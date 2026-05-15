import unittest
from unittest.mock import patch

from youtube_client import YouTubeClientImpl, SUPPORTED_VIDEO_EXTENSIONS


def make_client() -> YouTubeClientImpl:
    """Construct a YouTubeClientImpl without touching the filesystem."""
    with patch('youtube_client.YamlYoutubeCache'), \
         patch('youtube_client.YouTubeHasher'):
        return YouTubeClientImpl()


class IsVideoTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client()

    # --- all supported extensions, lower- and upper-case ---

    def test_supported_extensions_lowercase(self):
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            with self.subTest(ext=ext):
                self.assertTrue(self.client.is_video(f'clip{ext}'))

    def test_supported_extensions_uppercase(self):
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            with self.subTest(ext=ext):
                self.assertTrue(self.client.is_video(f'clip{ext.upper()}'))

    # --- full paths are handled ---

    def test_full_path_is_video(self):
        self.assertTrue(self.client.is_video('/home/user/videos/holiday.mp4'))

    def test_full_path_uppercase_is_video(self):
        self.assertTrue(self.client.is_video('/home/user/videos/FOO.AVI'))

    # --- unsupported extensions return False ---

    def test_unsupported_extensions(self):
        for name in ['document.txt', 'document.pdf', 'photo.jpg', 'audio.mp3', 'somefile']:
            with self.subTest(name=name):
                self.assertFalse(self.client.is_video(name))


if __name__ == '__main__':
    unittest.main()

