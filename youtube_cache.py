import logging
import os
from typing import Optional

import yaml

log = logging.getLogger(__name__)


class YoutubeCacheBase():
    def get(self, section: str, key: str) -> Optional[object]:
        raise NotImplementedError()

    def update(self, section: str, key: str, data: Optional[object]) -> None:
        raise NotImplementedError()


class YamlYoutubeCache(YoutubeCacheBase):
    def __init__(self, path):
        self.path = path
        self._data = None

    def __enter__(self):
        self.read_from_disk()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug('flushing the cache to the disk...')
        self.flush()

    def read_from_disk(self):
        log.info('reading the cache from the disk...')

        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as file:
                    self._data = yaml.load(file, Loader=yaml.Loader) or {}
                    log.info('  ok')
            except yaml.scanner.ScannerError as scannerError:
                raise Exception(f'Cache YAML file looks broken -- consider removing it and retrying: {scannerError}')
        else:
            log.warning('cache does not exist')
            self._data = {}  # init as empty cache

    def flush(self):
        log.info('flushing the cache to the disk...')

        # use portalocked to handle cases of multiple processes using the same cache file
        with open(self.path, 'w') as file:
            yaml.dump(self._data, file)
        log.info('  ok')

    def update(self, section: str, key: str, value: Optional[object]) -> None:
        if self._data is None:
            self.read_from_disk()

        if section not in self._data:
            self._data[section] = {}

        self._data[section][key] = value

    def get(self, section: str, key: str) -> Optional[object]:
        if self._data is None:
            self.read_from_disk()

        if not self._data or section not in self._data or key not in self._data[section]:
            return None

        return self._data[section][key]

