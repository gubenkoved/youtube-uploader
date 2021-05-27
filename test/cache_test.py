import unittest
import os

from youtube_cache import YamlYoutubeCache


class CacheTest(unittest.TestCase):
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
        self.assertEquals('Text 1 ' * 10, cache.get('test', 'text1'))
        self.assertEquals('Text 2 ' * 10, cache.get('test', 'text2'))
