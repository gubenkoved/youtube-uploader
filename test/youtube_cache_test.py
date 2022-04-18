import logging
import tempfile
import unittest

from youtube_cache import YamlYoutubeCache
from youtube_uploader_model import PlaylistVideosResponse, Video

log = logging.getLogger(__name__)


class CacheSerializabilityTest(unittest.TestCase):
    def get_temp_path(self):
        file = tempfile.NamedTemporaryFile()
        log.info('temp path: %s', file.name)
        return file.name

    def create_cache(self, path):
        return YamlYoutubeCache(path)

    def test_PlaylistVideosResponse(self):
        path = self.get_temp_path()
        cache = self.create_cache(path)

        cache.update(
            'section',
            'key',
            PlaylistVideosResponse([
                Video('id', 'title', 'description'),
                Video('id', 'title', 'description'),
            ])
        )

        cache.flush()

        cache2 = self.create_cache(path)
        cache2.read_from_disk()

        restored = cache2.get('section', 'key')

        self.assertTrue(isinstance(restored, PlaylistVideosResponse))
        self.assertEquals(2, len(restored.videos))


if __name__ == '__main__':
    unittest.main()
