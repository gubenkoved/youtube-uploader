import logging
import os
import tempfile
import unittest

from youtube_uploader.cache import YamlYoutubeCache
from youtube_uploader.model import PlaylistVideosResponse, Video

log = logging.getLogger(__name__)


class YamlYoutubeCacheTest(unittest.TestCase):
    """Basic read/write/flush behaviour of YamlYoutubeCache."""

    file_name = 'test-cache.yaml'

    def setUp(self) -> None:
        if os.path.exists(self.file_name):
            os.remove(self.file_name)

    def test_cache_does_not_get_corrupted_when_shrinking(self):
        cache = YamlYoutubeCache(self.file_name)
        cache.read_from_disk()
        cache.update('test', 'text1', 'Text 1 ' * 50)
        cache.update('test', 'text2', 'Text 2 ' * 50)
        cache.flush()

        # now shrink the cache data and re-read
        cache = YamlYoutubeCache(self.file_name)
        cache.read_from_disk()
        cache.update('test', 'text1', 'Text 1 ' * 10)
        cache.update('test', 'text2', 'Text 2 ' * 10)
        cache.flush()

        # make sure it's still readable
        cache = YamlYoutubeCache(self.file_name)
        cache.read_from_disk()
        self.assertEqual('Text 1 ' * 10, cache.get('test', 'text1'))
        self.assertEqual('Text 2 ' * 10, cache.get('test', 'text2'))


class YamlYoutubeCacheSerializationTest(unittest.TestCase):
    """Verify that model objects survive a cache round-trip."""

    def _temp_path(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()
        log.info('temp path: %s', f.name)
        return f.name

    def test_playlist_videos_response_round_trip(self):
        path = self._temp_path()
        cache = YamlYoutubeCache(path)

        cache.update(
            'section',
            'key',
            PlaylistVideosResponse([
                Video('id1', 'title1', 'description1'),
                Video('id2', 'title2', 'description2'),
            ])
        )
        cache.flush()

        cache2 = YamlYoutubeCache(path)
        cache2.read_from_disk()

        restored = cache2.get('section', 'key')

        self.assertIsInstance(restored, PlaylistVideosResponse)
        self.assertEqual(2, len(restored.videos))

