import hashlib
import logging
from datetime import datetime
from typing import Optional
from youtube_cache import YoutubeCacheBase

log = logging.getLogger(__name__)

class YouTubeHasher(object):
    def __init__(self, cache: YoutubeCacheBase):
        self.cache = cache
        self.section = 'file-hashes-v1'

    def _save_to_cache(self, path: str, md5: str) -> None:

        val = {
            'md5': md5,
            'calculated_at': datetime.now()
        }

        self.cache.update(self.section, path, val)

    def _get_from_cache(self, path: str) -> Optional[str]:
        val = self.cache.get(self.section, path)

        if val is None or 'md5' not in val:
            return None

        return val['md5']

    def _caclculate_md5(self, path: str) -> str:
        BLOCKSIZE = 65536
        hasher = hashlib.md5()
        with open(path, 'rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(BLOCKSIZE)
        return hasher.hexdigest()

    def md5(self, path) -> str:
        from_cache = self._get_from_cache(path)

        if from_cache:
            log.debug(f'Found {path} hash in the cache')
            return from_cache

        log.info(f'Calculating {path} hash...')
        md5 = self._caclculate_md5(path)

        try:
            self._save_to_cache(path, md5)
        except Exception as e:
            log.warning(f'unable to save hashing result into the cache: {e}')

        return md5
