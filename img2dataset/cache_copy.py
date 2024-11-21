from typing import Dict, Optional, Tuple

import dns.name
import dns.rdataclass
import dns.rdatatype
import dns.resolver

# Define TypeAlias
CacheKey = Tuple[dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass]


class SimpleCache:
    """A simple cache for local processes, no eviction policy, no lock."""

    def __init__(self, dump=None) -> None:
        self.data: Dict[CacheKey, Answer] = {} if dump is None else dump

    def put(self, key: CacheKey, value: Answer) -> None:
        self.data[key] = value

    def dump(self) -> Dict[CacheKey, Answer]:
        dumped_data = self.data.copy()
        self.data.clear()
        return dumped_data


class GlobalCache:
    """Thread-safe global cache with optimized merging."""

    def __init__(self) -> None:
        self.data: Dict[CacheKey, Answer] = {}
        self.lock = threading.Lock()

    def merge(self, new_data: Dict[CacheKey, Answer]) -> None:
        """Efficiently merge new data into global cache without duplicates."""
        with self.lock:
            keys_to_add = new_data.keys() - self.data.keys()
            keys_to_add_data = {k: new_data[k] for k in keys_to_add}
            self.data.update(keys_to_add_data)

    def get(self, key: CacheKey) -> Optional[Answer]:
        with self.lock:
            return self.data.get(key)

    def dump(self) -> Dict[CacheKey, Answer]:
        # We should us a lock here
        # but since we can afford to lose some data in this case
        # we are not using it
        with self.lock:
            dumped_data = self.data.copy()
            return dumped_data
