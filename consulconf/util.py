from functools import wraps

try:  # py3k only
    from functools import lru_cache as _lru_cache

    def cached(func):
        """Wraps functools.lru_cache with maxsize=None"""
        return _lru_cache(None)(func)

except:  # otherwise, hack this in.

    def cached(func):
        """Python 2 fake lru_cache.  Ignore `maxsize` and `typed`.
        This won't work in many scenarios, so don't port this to other projects

        Assume kwargs are never used
        """
        cache_dct = {}

        @wraps(func)
        def _lru_cache_decorator(*args):
            key = args
            if key in cache_dct:
                return cache_dct[key]
            else:
                cache_dct[key] = func(*args)
                return cache_dct[key]
        return _lru_cache_decorator
