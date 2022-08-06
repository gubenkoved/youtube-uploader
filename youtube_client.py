import http.client
import logging
import os
import random
from datetime import datetime, time
from typing import Optional

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

from youtube_cache import YamlYoutubeCache
from youtube_hasher import YouTubeHasher
from youtube_uploader_model import YouTubeClient, GetMyPlaylistsResponse, Playlist, PlaylistVideosResponse, Video, \
    UploadVideoResponse

log = logging.getLogger(__name__)


class YouTubeClientImpl(YouTubeClient):
    def __init__(
            self,
            client_secrets_file_path: str = 'client_secrets.json',
            credentials_file_path: str = 'credentials.json',
            disable_ssl_validation: bool = False):
        log.debug('Creating YouTube client...')
        self.scopes = ['https://www.googleapis.com/auth/youtube.readonly',
                       'https://www.googleapis.com/auth/youtube.upload',
                       'https://www.googleapis.com/auth/youtube']  # to add files to playlists
        self.api_service = 'youtube'
        self.api_version = 'v3'
        self.client_secrets_file_path = client_secrets_file_path
        self.credentials_file_path = credentials_file_path
        self._cache = YamlYoutubeCache('cache.yaml')
        self._hasher = YouTubeHasher(self._cache)
        self._disable_ssl_validation = disable_ssl_validation

    def __enter__(self):
        self._cache.read_from_disk()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cache.flush()

    def _get_authenticated_service(self):
        flow = flow_from_clientsecrets(
            self.client_secrets_file_path,
            scope=self.scopes,
            message="missing secrets message here!"
        )

        storage = Storage(self.credentials_file_path)
        credentials = storage.get()

        class Args(object):
            pass

        args = Args()

        args.auth_host_name = 'localhost'
        args.auth_host_port = [8080, 8090]
        args.logging_level = 'ERROR'
        args.noauth_local_webserver = False

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, args)

        return build(
            self.api_service,
            self.api_version,
            http=credentials.authorize(
                httplib2.Http(disable_ssl_certificate_validation=self._disable_ssl_validation))
        )

    def authorize(self) -> None:
        _ = self._get_authenticated_service()

    def get_my_playlists(self) -> GetMyPlaylistsResponse:
        youtube = self._get_authenticated_service()

        playlists = []
        nextPageToken = None

        while True:

            request = youtube.playlists().list(
                part="snippet,contentDetails",
                maxResults=25,
                mine=True,
                pageToken=nextPageToken
            )

            response = request.execute()

            for item in response['items']:
                playlistId = item['id']
                title = item['snippet']['title']
                description = item['snippet']['description']
                # publishedAt = item['snippet']['publishedAt']
                # itemCount = item['contentDetails']['itemCount']
                etag = item['etag']

                playlist = Playlist(playlistId, title, description=description, etag=etag)
                playlists.append(playlist)

            if 'nextPageToken' in response:
                nextPageToken = response['nextPageToken']
            else:
                break

        return GetMyPlaylistsResponse(playlists)

    def _get_playlist_current_etag(self, playlistId: str) -> str:
        youtube = self._get_authenticated_service()

        playlist_request = youtube.playlists().list(
            part="snippet",
            maxResults=25,
            id=playlistId,
        )

        playlist_response = playlist_request.execute()
        playlist_etag = playlist_response['etag']
        return playlist_etag

    def get_playlist_videos(self, playlistId: str, etag: Optional[str] = None) -> PlaylistVideosResponse:
        playlist_etag = etag or self._get_playlist_current_etag(playlistId)

        # check in the cache!
        cache_section = "playlists"
        data_ver = 'v1'
        from_cache = self._cache.get(cache_section, playlistId)

        if (from_cache is not None
                and 'etag' in from_cache and from_cache['etag'] == playlist_etag  # check etag
                and 'version' in from_cache and from_cache['version'] == data_ver  # check data contract
                and 'data' in from_cache):  # check data is there
            return from_cache['data']

        log.debug(f'cache miss for playlist content for {playlistId}, populating...')

        youtube = self._get_authenticated_service()

        videos = []
        pageToken = None

        while True:

            request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                maxResults=50,
                pageToken=pageToken,
                playlistId=playlistId
            )

            response = request.execute()

            for item in response['items']:
                videoId = item['id']
                title = item['snippet']['title']
                description = item['snippet']['description']

                videos.append(Video(videoId, title, description))

            if 'nextPageToken' not in response:
                break  # all pages digested

            pageToken = response['nextPageToken']

        result = PlaylistVideosResponse(videos)

        # cache in the cache
        try:
            cache_val = {'data': result,
                         'version': data_ver,
                         'etag': playlist_etag}

            self._cache.update(cache_section, playlistId, cache_val)
        except Exception as e:
            log.warning(f'An error occurred caching playlist listing results: {e}')

        return result

    def is_video(self, path) -> bool:
        extensions = ['.mp4', '.mov']

        for ext in extensions:
            if path.lower().endswith(ext):
                return True

        return False

    def is_matching_video(self, local_hash: str, video: Video) -> bool:
        return local_hash in video.description

    def file_hash(self, path) -> str:
        return self._hasher.md5(path)

    def _generate_metadata(self, path: str) -> str:
        dir, fileName = os.path.split(path)
        hash = self.file_hash(path)
        createdAt = datetime.fromtimestamp(os.path.getctime(path))
        modifiedAt = datetime.fromtimestamp(os.path.getmtime(path))
        size = os.path.getsize(path)

        description = f'File name: {fileName}\n'
        description += f'Dir: {dir}\n'
        description += f'Created at: {createdAt:%Y-%m-%dT%H:%M:%S}\n'
        description += f'Modified at: {modifiedAt:%Y-%m-%dT%H:%M:%S}\n'
        description += f'Size: {(size/(1024*1024)):.2f} MiB\n'
        description += f'MD5: {hash}\n'
        description += f'[auto uploaded]'

        return description

    def _resumable_upload(self, insert_request) -> str:
        response = None
        error = None
        retry = 0
        max_retries = 10

        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' not in response:
                        raise Exception("The upload failed with an unexpected response: %s" % response)

                    return response['id']
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
                else:
                    raise
            except (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                    http.client.IncompleteRead, http.client.ImproperConnectionState,
                    http.client.CannotSendRequest, http.client.CannotSendHeader,
                    http.client.ResponseNotReady, http.client.BadStatusLine) as e:
                error = "A retriable error occurred: %s" % e

            if error is not None:
                log.warning(error)
                retry += 1
                if retry > max_retries:
                    raise Exception("No longer attempting to retry.")

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                log.warning("Sleeping %f seconds and then retrying..." % sleep_seconds)
                time.sleep(sleep_seconds)

    def upload_video(self, path: str, title: str, description: str = '', privacyLevel: str = 'unlisted') -> UploadVideoResponse:

        description += self._generate_metadata(path)

        body = dict(
            snippet=dict(
                title=title,
                description=description,
                tags=[],
                categoryId=22
            ),
            status=dict(
                privacyStatus=privacyLevel
            )
        )

        youtube = self._get_authenticated_service()

        insert_request = youtube.videos().insert(
            part=",".join(list(body.keys())),
            body=body,
            media_body=MediaFileUpload(path, chunksize=-1, resumable=True)
        )

        videoId = self._resumable_upload(insert_request)

        return UploadVideoResponse(videoId)

    def add_video_to_playlist(self, playlistId: str, videoId: str):
        body = {
            "snippet": {
                "playlistId": playlistId,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": videoId
                }
            }
        }

        youtube = self._get_authenticated_service()

        request = youtube.playlistItems().insert(
            part=",".join(list(body.keys())),
            body=body
        )

        request.execute()
