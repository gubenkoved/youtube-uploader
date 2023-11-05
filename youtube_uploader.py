import argparse
import os
import logging
import coloredlogs
from datetime import datetime
from typing import Iterable, Optional, List
from youtube_uploader_model import YouTubeClient, Playlist, Video
from youtube_client import YouTubeClientImpl


def find_already_uploaded(client: YouTubeClient, videos: Iterable[Video], local_file_path: str) -> Optional[Video]:
    local_hash = client.file_hash(local_file_path)

    # work using videos description MD5 inside!
    for video in videos:
        if client.is_matching_video(local_hash, video):
            return video

    return None


def get_files_for_upload(client: YouTubeClient, dir: str, creation_cut_off: Optional[datetime]) -> List[str]:
    upload_queue = []

    log.debug(f'Discovering videos in {dir}...')

    for root, subdirs, files in os.walk(dir):
        log.debug(f'  walking in {root}...')

        for file in files:
            if not client.is_video(file):
                continue

            path = os.path.join(root, file)
            created_at = datetime.fromtimestamp(os.path.getctime(path))

            log.debug(f'    looking at {file} (created at: {created_at})')
            upload_queue.append(path)

    if creation_cut_off:
        log.debug(f'Creation cut-off date was specified, applying filter... '
                  f'Discovered: {len(upload_queue)}')
        upload_queue = list(filter(lambda path: datetime.fromtimestamp(
            os.path.getctime(path)) >= creation_cut_off, upload_queue))
        log.debug(f'  after filter: {len(upload_queue)}')

    upload_queue.sort(key=lambda path: os.path.getmtime(path))

    return upload_queue


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = f"Not a valid date: '{s}'"
        raise argparse.ArgumentTypeError(msg)


def init_logging(log_level: str = 'INFO') -> None:
    # file logger
    file_handler = logging.FileHandler("youtube_uploader.log", encoding='utf8')
    format_template = "%(asctime)s [%(process)d] %(levelname)8s %(name)s %(message)s"
    formatter = logging.Formatter(format_template)
    file_handler.setFormatter(formatter)

    level_name = logging.getLevelName(log_level)
    logging.basicConfig(handlers=[file_handler], level=level_name)

    # colored console logger
    coloredlogs.install(level=level_name, fmt=format_template)

    # disable wordy loggers, when something important happens
    # application will see it in form of error to log
    logging.getLogger('googleapiclient.discovery_cache').disabled = True
    logging.getLogger('googleapiclient.discovery').disabled = True


def main():
    global log

    argparser = argparse.ArgumentParser()

    argparser.add_argument("--dir", required=True,
                           help="Directory to digest files inside")
    argparser.add_argument("--playlist", required=True,
                           help="Playlist to for video to be added to (will be found via contains)")
    argparser.add_argument("--client-secrets-file", required=False, default='client_secrets.json',
                           help="Path to client secrets file, when different from client_secrets.json")
    argparser.add_argument("--credentials-file", required=False, default='credentials.json',
                           help="Path to stored credentials file, when different from credentials.json")
    argparser.add_argument("--creation-date-cutoff", required=False, default=None, type=valid_date,
                           help="Allows to specify cutoff date (YYYY-MM-DD) for the file creation time in order to be picked up")
    argparser.add_argument("--log-level", required=False, default='INFO',
                           help="Logging level (DEBUG, INFO, WARN, ERROR)")
    argparser.add_argument("--disable-ssl-validation", required=False, default=False,
                           action=argparse.BooleanOptionalAction,
                           help="Disables SSL validation")

    args = argparser.parse_args()

    init_logging(args.log_level)

    log = logging.getLogger("main")

    log.info(f'YouTube uploader started ({args.dir})!')
    log.debug(f'CWD: {os.getcwd()}')
    log.debug(f'Arguments: {args.__dict__}')

    # construct the client
    youtube: YouTubeClient
    with YouTubeClientImpl(
        client_secrets_file_path=args.client_secrets_file,
            credentials_file_path=args.credentials_file,
            disable_ssl_validation=args.disable_ssl_validation) as youtube:

        # authorize the user!
        youtube.authorize()

        # get ALL playlists
        playlists_response = youtube.get_my_playlists()

        log.debug(f'Populated {len(playlists_response.playlists)} playlists')

        # try to find the target playlist
        target_playlist: Playlist = next(
            filter(lambda p: args.playlist in p.title, playlists_response.playlists), None)

        if not target_playlist:
            raise Exception(
                'Unable to find the playlist -- make sure specified string is within the Playlist Name')

        log.debug(
            f'Found the target playlist -- {target_playlist.title} ({target_playlist.playlistId})')

        all_videos = []

        log.debug(f'Populating ALL videos to detect already uploaded')

        playlist: Playlist
        for playlist in playlists_response.playlists:
            playlist_videos_response = youtube.get_playlist_videos(playlist.playlistId, etag=playlist.etag)
            log.debug(
                f'  {playlist.title:30} {playlist.playlistId:38} {len(playlist_videos_response.videos):5} items')
            all_videos.extend(playlist_videos_response.videos)

        log.debug(
            f'Populated {len(all_videos)} videos in total in {len(playlists_response.playlists)} playlists')

        # find all files for upload
        upload_queue = get_files_for_upload(youtube, args.dir, args.creation_date_cutoff)

        if len(upload_queue) > 0:
            log.debug(f"Discovered {len(upload_queue)} items, start upload procedure")
        else:
            log.info('Nothing to upload!')

        upload_count = 0

        for path in upload_queue:
            log.debug(f'handling {path}...')

            already_uploaded: Optional[Video] = find_already_uploaded(
                youtube, all_videos, path)

            if already_uploaded:
                log.debug(
                    f'  already uploaded as {already_uploaded.title} (ID: {already_uploaded.videoId})')
                continue

            _, fileName = os.path.split(path)
            fileNameNoExt = os.path.splitext(fileName)[0]
            size = os.path.getsize(path)

            log.info(f'  uploading a video ({size / (1024 * 1024):.2f} MiB)...')

            upload_response = youtube.upload_video(
                path, title=fileNameNoExt, privacyLevel='unlisted')

            log.info(f'  upload successfull, ID: {upload_response.videoId}')

            log.info(f'  adding video to the playlist... ({upload_response.videoId} -> {target_playlist.playlistId})')
            youtube.add_video_to_playlist(
                playlistId=target_playlist.playlistId, videoId=upload_response.videoId)

            log.info(f'  processed!')

            upload_count += 1
            
        if upload_count > 0:
            log.info(f'Uploaded {upload_count} new videos!')
        else:
            log.info(f'No new videos uploaded')


if __name__ == '__main__':
    global log
    log: Optional[logging.Logger] = None

    try:
        main()
    except Exception as e:
        if log:  # if logging managed to start, use it
            log.fatal(str(e))
        raise
