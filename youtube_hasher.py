import hashlib
import portalocker
import yaml
import logging
import os
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

class YouTubeHasher(object):
    def __init__(self, cache_file_path: str):
        self.cache_file_path = cache_file_path

    def _save_to_cache(self, path: str, md5: str) -> None:
        mode = 'r+' if os.path.exists(self.cache_file_path) else 'w+'
        # use portalocked to handle cases of multiple processes using the same cache file
        with portalocker.Lock(self.cache_file_path, mode, timeout=60) as file:
            data = yaml.load(file, Loader=yaml.FullLoader) or {}
            if path not in data:
                data[path] = {}
            data[path]['md5'] = md5
            data[path]['calculated_at'] = str(datetime.now())
            file.seek(0)
            yaml.dump(data, file)
            # closing routine as per https://readthedocs.org/projects/portalocker/downloads/pdf/latest/
            file.flush()
            os.fsync(file.fileno())

    def _get_from_cache(self, path: str) -> Optional[str]:
        if not os.path.exists(self.cache_file_path):
            log.warning('cache does not exist')
            return None

        with portalocker.Lock(self.cache_file_path, 'r', timeout=60) as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
            if not data or path not in data or 'md5' not in data[path]:
                return None
            return data[path]['md5']

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
