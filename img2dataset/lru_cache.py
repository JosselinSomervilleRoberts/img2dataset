import pickle  # For serialization of complex objects
from typing import Optional, Tuple

import dns.name
import dns.rdataclass
import dns.rdatatype
import dns.resolver
import redis

# Define TypeAlias
CacheKey = Tuple[dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass]


class LRUCacheRedis(dns.resolver.CacheBase):
    """
    Redis-based LRU DNS Cache with max size constraints.
    Uses Pickle to serialize and store the Answer object in Redis.
    """

    def __init__(self, pool: redis.ConnectionPool) -> None:
        """
        Initialize Redis-backed LRU cache for DNS answers.

        :param redis_host: Redis server hostname.
        :param redis_port: Redis server port.
        """
        super().__init__()
        self.conn = redis.Redis(
            connection_pool=pool, decode_responses=False
        )  # Set decode_responses=False for binary usage

    def get_size(self) -> int:
        return self.conn.dbsize()

    def _generate_cache_key(self, key: CacheKey) -> str:
        """
        Generate a cache key string for Redis based on a CacheKey Tuple.

        :param key: A tuple `(dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass)`
        :return: A string key to store in Redis.
        """
        name, rdtype, rdclass = key
        return f"{name!s}:{int(rdtype)}:{int(rdclass)}"

    def get(self, key: CacheKey) -> Optional[dns.resolver.Answer]:
        """
        Get the DNS answer associated with the key from Redis.

        :param key: A tuple of `(dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass)`
        :return: `dns.resolver.Answer` or `None` if not found.
        """
        cache_key = self._generate_cache_key(key)
        cache_data = self.conn.get(cache_key)  # Get serialized data from Redis

        if cache_data is None:
            # Cache miss
            self.statistics.misses += 1
            return None

        # Deserialize the binary data back into an Answer object
        answer = pickle.loads(cache_data)

        # Move the key to "recently used" by updating the LRU list
        self.conn.lrem(
            "lru_list", 0, cache_key
        )  # Remove existing references in the LRU list
        self.conn.lpush(
            "lru_list", cache_key
        )  # Add cache_key to the front (most recent)

        self.statistics.hits += 1

        return answer

    def put(self, key: CacheKey, value: dns.resolver.Answer) -> None:
        """
        Add a DNS answer to Redis cache with LRU behavior.

        :param key: A tuple `(dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass)`
        :param value: A `dns.resolver.Answer` to cache
        """
        cache_key = self._generate_cache_key(key)

        # Serialize the Answer object to binary using pickle
        serialized_value = pickle.dumps(value)

        # Insert into Redis
        self.conn.set(cache_key, serialized_value)

        # Insert into LRU tracking list
        self.conn.lrem("lru_list", 0, cache_key)  # Remove existing reference if any
        self.conn.lpush("lru_list", cache_key)  # Add the key to front of the LRU list

    def flush(self, key: Optional[CacheKey] = None) -> None:
        """
        Flush an individual cache key from Redis or flush all if key is not specified.

        :param key: Specific DNS cache key to flush or `None` to flush all.
        """
        if key is not None:
            cache_key = self._generate_cache_key(key)
            self.conn.delete(cache_key)  # Remove the specific key from Redis
            self.conn.lrem("lru_list", 0, cache_key)  # Remove from LRU tracking list
        else:
            # Flush everything (both cache and LRU list)
            self.conn.flushdb()
