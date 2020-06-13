import argparse
import os
import re
import hashlib
import logging
import coloredlogs
from time import sleep
from datetime import datetime

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


def get_files_for_upload(client: YouTubeClient, dir: str, creation_cut_off: Optional[datetime]) -> Iterable[str]:
    upload_queue = []

    log.info(f'Discovering videos in {dir}...')

    for root, subdirs, files in os.walk(dir):
        log.info(f'  walking in {root}...')

        for file in files:
            if not client.is_video(file):
                continue

            path = os.path.join(root, file)
            created_at = datetime.fromtimestamp(os.path.getctime(path))

            log.info(f'    looking at {file} (created at: {created_at})')
            upload_queue.append(path)

    if creation_cut_off:
        log.info(f'Creation cut-off date was specified, applying filter... Discovered: {len(upload_queue)}')
        upload_queue = list(filter(lambda path: datetime.fromtimestamp(
            os.path.getctime(path)) >= creation_cut_off, upload_queue))
        log.info(f'  after filter: {len(upload_queue)}')

    upload_queue.sort(key=lambda path: os.path.getmtime(path))

    return upload_queue


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = f"Not a valid date: '{s}'"
        raise argparse.ArgumentTypeError(msg)

def main():
    argparser = argparse.ArgumentParser()

    argparser.add_argument("--dir", required=True,
                           help="Directory to digest files inside")
    argparser.add_argument("--playlist", required=False,
                           help="Playlist to for video to be added to (will be found via contains)")
    argparser.add_argument("--client-secrets-file", required=False, default='client_secrets.json',
                           help="Path to client secrets file, when different from client_secrets.json")
    argparser.add_argument("--credentials-file", required=False, default='credentials.json',
                           help="Path to stored credentials file, when different from credentials.json")
    argparser.add_argument("--creation-date-cutoff", required=False, default=None, type=valid_date,
                           help="Allows to specify cutoff date (YYYY-MM-DD) for the file creation time in order to be picked up")

    args = argparser.parse_args()

    log.info(f'Arguments: {args.__dict__}')

    # construct the client
    youtube: YouTubeClient = YouTubeClientImpl(
        client_secrets_file_path=args.client_secrets_file,
        credentials_file_path=args.credentials_file)

    # authorize the user!
    youtube.authorize()

    # get ALL playlists
    playlists_response = youtube.get_my_playlists()

    log.info(f'Populated {len(playlists_response.playlists)} playlists')

    # try to find the target playlist
    target_playlist: Playlist = next(
        filter(lambda p: args.playlist in p.title, playlists_response.playlists), None)

    if not target_playlist:
        raise Exception(
            'Unable to find the playlist -- make sure specified string is withing the Playlist Name')

    log.info(
        f'Found the target playlist -- {target_playlist.title} ({target_playlist.playlistId})')

    all_videos = []

    log.info(f'Populating ALL videos to detect already uploaded')

    playlist: Playlist
    for playlist in playlists_response.playlists:
        playlist_videos_response = youtube.get_playlist_videos(
            playlist.playlistId)
        log.info(
            f'  {playlist.title:30} {playlist.playlistId:38} {len(playlist_videos_response.videos):5} items')
        all_videos.extend(playlist_videos_response.videos)

    log.info(
        f'Populated {len(all_videos)} videos in total in {len(playlists_response.playlists)} playlists')

    # find all files for upload
    upload_queue = get_files_for_upload(youtube, args.dir, args.creation_date_cutoff)

    log.info(f"Discovered {len(upload_queue)} items, start upload procedure")

    for path in upload_queue:
        log.info(f'handling {path}...')

        already_uploaded: Optional[Video] = find_already_uploaded(
            youtube, all_videos, path)

        if already_uploaded:
            log.info(
                f'  already uploaded as {already_uploaded.title} (ID: {already_uploaded.videoId})')
            continue

        dir, fileName = os.path.split(path)
        fileNameNoExt = os.path.splitext(fileName)[0]

        log.info(f'  uploading a video...')
        upload_response = youtube.upload_video(
            path, title=fileNameNoExt, privacyLevel='unlisted')
        log.info(f'  upload successfull! ID: {upload_response.videoId}')

        log.info(f'  adding a video to the playlist...')
        youtube.add_video_to_playlist(
            playlistId=target_playlist.playlistId, videoId=upload_response.videoId)

        log.info(f'  processed!')


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    log_file_handler = logging.FileHandler("youtube_uploader.log", encoding='utf8')
    formatter = logging.Formatter("%(asctime)s [%(process)d] - %(name)s - %(levelname)s - %(message)s")
    log_file_handler.setFormatter(formatter)
    coloredlogs.install(logger=logger)
    logger.addHandler(log_file_handler)
    return logger

log = get_logger("default")


if __name__ == '__main__':
    try:
        log.info(f'YouTube Uploader started!')
        main()
    except Exception as e:
        log.error(e)
        raise
    finally:
        log.info("finished")
