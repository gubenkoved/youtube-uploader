import argparse
import os
import re
import hashlib

from typing import Iterable, Optional
from youtube_uploader_model import YouTubeClient, Playlist, Video, UploadVideoResponse
from youtube_client import YouTubeClientImpl


def find_already_uploaded(client: YouTubeClient, videos: Iterable[Video], local_file_path: str) -> Optional[Video]:

    local_hash = client.file_hash(local_file_path)
    # work using videos description MD5 inside!
    for video in videos:
        if 'auto uploaded' not in video.description:
            continue

        match = re.search('MD5: (?P<md5>[a-z0-9]+)', video.description)
        if match:
            md5 = match.group('md5').lower()

            if local_hash.lower() == md5:
                return video
    return None


def is_video(fileName: str) -> bool:
    extensions = ['.mp4', '.mov']

    for ext in extensions:
        if fileName.lower().endswith(ext):
            return True

    return False


def get_files_for_upload(dir: str) -> Iterable[str]:
    upload_queue = []

    print(f'Discovering videos in {dir}...')

    for root, subdirs, files in os.walk(args.dir):
        print(f'  walking in {root}...')

        for file in files:
            if not is_video(file):
                continue

            print(f'    looking at {file}')
            upload_queue.append(os.path.join(root, file))

    upload_queue.sort(key=lambda path: os.path.getmtime(path))

    return upload_queue


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()

    argparser.add_argument("--dir", required=True,
                           help="Directory to digest files inside")
    argparser.add_argument("--playlist", required=False,
                           help="Playlist to for video to be added to (will be found via contains)")
    argparser.add_argument("--client-secrets-file", required=False, default='client_secrets.json',
                           help="Path to client secrets file, when different from client_secrets.json")
    argparser.add_argument("--credentials-file", required=False, default='credentials.json',
                           help="Path to stored credentials file, when different from credentials.json")

    args = argparser.parse_args()

    # construct the client
    youtube: YouTubeClient = YouTubeClientImpl(
        client_secrets_file_path=args.client_secrets_file,
        credentials_file_path=args.credentials_file)

    # authorize the user!
    youtube.authorize()

    # get ALL playlists
    playlists_response = youtube.get_my_playlists()

    print(f'Populated {len(playlists_response.playlists)} playlists')

    # try to find the target playlist
    target_playlist: Playlist = next(filter(lambda p: args.playlist in p.title, playlists_response.playlists), None)

    if not target_playlist:
        raise Exception('Unable to find the playlist -- make sure specified string is withing the Playlist Name')

    print(f'Found the target playlist -- {target_playlist.title} ({target_playlist.playlistId})')

    all_videos = []

    print(f'Populating ALL videos to detect already uploaded')

    playlist: Playlist
    for playlist in playlists_response.playlists:
        playlist_videos_response = youtube.get_playlist_videos(playlist.playlistId)
        print(f'  {playlist.title:30} {playlist.playlistId:38} {len(playlist_videos_response.videos):5} items')
        all_videos.extend(playlist_videos_response.videos)

    print(f'Populated {len(all_videos)} videos in total in {len(playlists_response.playlists)} playlists')

    # find all files for upload
    upload_queue = get_files_for_upload(args.dir)

    print(f"Discovered {len(upload_queue)} items, start upload procedure")

    for path in upload_queue:
        print(f'handling {path}...')

        already_uploaded: Optional[Video] = find_already_uploaded(youtube, all_videos, path)

        if already_uploaded:
            print(f'  already uploaded as {already_uploaded.title} (ID: {already_uploaded.videoId})')
            continue

        dir, fileName = os.path.split(path)
        fileNameNoExt = os.path.splitext(fileName)[0]

        print(f'  uploading a video...')
        upload_response = youtube.upload_video(path, title=fileNameNoExt, privacyLevel='unlisted')
        print(f'  upload successfull! ID: {upload_response.videoId}')

        print(f'  adding a video to the playlist...')
        youtube.add_video_to_playlist(playlistId=target_playlist.playlistId, videoId=upload_response.videoId)

        print(f'  processed!')
