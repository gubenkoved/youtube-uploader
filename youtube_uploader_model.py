from typing import Iterable, Optional


class UploadVideoResponse(object):
    def __init__(self, videoId: str):
        self.videoId = videoId

class Playlist(object):
    def __init__(self, playlistId: str, title: str, description: str = None):
        self.playlistId = playlistId
        self.title = title
        self.description = description

class GetMyPlaylistsResponse(object):
    def __init__(self, playlists: Iterable[Playlist]):
        self.playlists = playlists

class Video(object):
    def __init__(self, videoId: str, title: str, description: str):
        self.videoId = videoId
        self.title = title
        self.description = description

class PlaylistVideosResponse(object):
    def __init__(self, videos: Iterable[Video]):
        self.videos = videos


class YouTubeClient(object):
    def authorize(self) -> None:
        raise NotImplementedError()

    def file_hash(self, path) -> str:
        raise NotImplementedError

    def is_video(self, path) -> bool:
        raise NotImplementedError

    def get_my_playlists(self) -> GetMyPlaylistsResponse:
        raise NotImplementedError()

    def get_playlist_videos(self, playlistId: str) -> PlaylistVideosResponse:
        raise NotImplementedError()

    def upload_video(self, path: str, title: str, description: str = '', privacyLevel: str = 'unlisted') -> UploadVideoResponse:
        raise NotImplementedError()

    def add_video_to_playlist(self, playlistId: str, videoId: str) -> None:
        raise NotImplementedError()

    def update_video(self, videoId, newTitle: Optional[str], newDescription: Optional[str]) -> None:
        raise NotImplementedError()
