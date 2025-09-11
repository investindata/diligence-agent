"""
Cached wrappers for Serper tools to reduce API calls during development.
"""

import hashlib
import json
import os
import shutil
from typing import Any, Dict, Optional
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from crewai.tools.base_tool import BaseTool


class CachedSerperDevTool(BaseTool):
    """Cached wrapper for SerperDevTool with memory and file caching."""
    
    def __init__(self, cache_dir: str = "cache/serper_search"):
        super().__init__(
            name="cached_serper_search",
            description="Search the web with caching to reduce API calls"
        )
        # Use object.__setattr__ to bypass Pydantic's validation
        object.__setattr__(self, 'cache_dir', cache_dir)
        object.__setattr__(self, 'memory_cache', {})
        object.__setattr__(self, 'serper_tool', SerperDevTool())
        object.__setattr__(self, 'stats', {'hits': 0, 'misses': 0, 'memory_hits': 0, 'file_hits': 0})
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    def _generate_cache_key(self, query: str) -> str:
        """Generate a unique cache key for the search query."""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _load_from_file_cache(self, cache_key: str) -> Optional[Any]:
        """Load cached result from file."""
        cache_file = self._get_cache_file_path(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    return cached_data['result']
            except (json.JSONDecodeError, KeyError, IOError):
                pass
        return None
    
    def _save_to_file_cache(self, cache_key: str, result: Any) -> None:
        """Save result to file cache."""
        cache_file = self._get_cache_file_path(cache_key)
        try:
            cached_data = {
                'cache_key': cache_key,
                'result': result
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, indent=2, ensure_ascii=False)
        except (IOError, TypeError):
            pass
    
    def clear_cache(self) -> None:
        """Clear both memory and file cache."""
        self.memory_cache.clear()
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        # Reset stats
        self.stats = {'hits': 0, 'misses': 0, 'memory_hits': 0, 'file_hits': 0}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_ratio = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'tool_name': 'Search',
            'total_requests': total_requests,
            'cache_hits': self.stats['hits'],
            'api_calls': self.stats['misses'],
            'hit_ratio': f"{hit_ratio:.1f}%",
            'memory_hits': self.stats['memory_hits'],
            'file_hits': self.stats['file_hits'],
            'cached_items': len(self.memory_cache)
        }
    
    def _run(self, query: str, **kwargs) -> Any:
        """Execute search with caching logic."""
        cache_key = self._generate_cache_key(query)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.stats['hits'] += 1
            self.stats['memory_hits'] += 1
            print(f"🧠 Cache HIT (memory): {query[:50]}...")
            return self.memory_cache[cache_key]
        
        # Check file cache
        cached_result = self._load_from_file_cache(cache_key)
        if cached_result is not None:
            self.stats['hits'] += 1
            self.stats['file_hits'] += 1
            self.memory_cache[cache_key] = cached_result
            print(f"🗂️ Cache HIT (file): {query[:50]}...")
            return cached_result
        
        # No cache hit, call the actual Serper API
        self.stats['misses'] += 1
        print(f"🔍 Cache MISS - API call: {query[:50]}...")
        
        try:
            result = self.serper_tool._run(query=query, **kwargs)
            # Cache the result in both memory and file
            self.memory_cache[cache_key] = result
            self._save_to_file_cache(cache_key, result)
            return result
        except Exception as e:
            # Don't cache errors, just re-raise
            raise e


class CachedSerperScrapeWebsiteTool(BaseTool):
    """Cached wrapper for SerperScrapeWebsiteTool with memory and file caching."""
    
    def __init__(self, cache_dir: str = "cache/serper_scraper"):
        super().__init__(
            name="cached_serper_scraper", 
            description="Scrape website content with caching to reduce API calls"
        )
        # Use object.__setattr__ to bypass Pydantic's validation
        object.__setattr__(self, 'cache_dir', cache_dir)
        object.__setattr__(self, 'memory_cache', {})
        object.__setattr__(self, 'serper_tool', SerperScrapeWebsiteTool())
        object.__setattr__(self, 'stats', {'hits': 0, 'misses': 0, 'memory_hits': 0, 'file_hits': 0})
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
    
    def _generate_cache_key(self, url: str) -> str:
        """Generate a unique cache key for the URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _load_from_file_cache(self, cache_key: str) -> Optional[Any]:
        """Load cached result from file."""
        cache_file = self._get_cache_file_path(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    return cached_data['result']
            except (json.JSONDecodeError, KeyError, IOError):
                pass
        return None
    
    def _save_to_file_cache(self, cache_key: str, result: Any) -> None:
        """Save result to file cache."""
        cache_file = self._get_cache_file_path(cache_key)
        try:
            cached_data = {
                'cache_key': cache_key,
                'result': result
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, indent=2, ensure_ascii=False)
        except (IOError, TypeError):
            pass
    
    def clear_cache(self) -> None:
        """Clear both memory and file cache."""
        self.memory_cache.clear()
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        # Reset stats
        self.stats = {'hits': 0, 'misses': 0, 'memory_hits': 0, 'file_hits': 0}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_ratio = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'tool_name': 'Scraper',
            'total_requests': total_requests,
            'cache_hits': self.stats['hits'],
            'api_calls': self.stats['misses'],
            'hit_ratio': f"{hit_ratio:.1f}%",
            'memory_hits': self.stats['memory_hits'],
            'file_hits': self.stats['file_hits'],
            'cached_items': len(self.memory_cache)
        }
    
    def _run(self, url: str, **kwargs) -> Any:
        """Execute scraping with caching logic."""
        cache_key = self._generate_cache_key(url)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.stats['hits'] += 1
            self.stats['memory_hits'] += 1
            print(f"🧠 Cache HIT (memory): {url[:50]}...")
            return self.memory_cache[cache_key]
        
        # Check file cache
        cached_result = self._load_from_file_cache(cache_key)
        if cached_result is not None:
            self.stats['hits'] += 1
            self.stats['file_hits'] += 1
            self.memory_cache[cache_key] = cached_result
            print(f"🗂️ Cache HIT (file): {url[:50]}...")
            return cached_result
        
        # No cache hit, call the actual Serper API
        self.stats['misses'] += 1
        print(f"🕷️ Cache MISS - API call: {url[:50]}...")
        
        try:
            result = self.serper_tool._run(url=url, **kwargs)
            # Cache the result in both memory and file
            self.memory_cache[cache_key] = result
            self._save_to_file_cache(cache_key, result)
            return result
        except Exception as e:
            # Don't cache errors, just re-raise
            raise e


# Global instances for cache clearing
cached_serper_search = CachedSerperDevTool()
cached_serper_scraper = CachedSerperScrapeWebsiteTool()


def print_cache_stats():
    """Print cache statistics for both tools."""
    search_stats = cached_serper_search.get_cache_stats()
    scraper_stats = cached_serper_scraper.get_cache_stats()
    
    print("\n📊 CACHE PERFORMANCE STATS")
    print("=" * 50)
    
    for stats in [search_stats, scraper_stats]:
        if stats['total_requests'] > 0:
            print(f"\n🔧 {stats['tool_name']} Tool:")
            print(f"   Total Requests: {stats['total_requests']}")
            print(f"   Cache Hits: {stats['cache_hits']} ({stats['hit_ratio']})")
            print(f"   API Calls: {stats['api_calls']}")
            print(f"   Memory Hits: {stats['memory_hits']}")
            print(f"   File Hits: {stats['file_hits']}")
            print(f"   Items in Memory: {stats['cached_items']}")
    
    # Calculate totals
    total_requests = search_stats['total_requests'] + scraper_stats['total_requests']
    total_hits = search_stats['cache_hits'] + scraper_stats['cache_hits']
    total_api_calls = search_stats['api_calls'] + scraper_stats['api_calls']
    
    if total_requests > 0:
        overall_hit_ratio = (total_hits / total_requests * 100)
        print(f"\n🎯 OVERALL PERFORMANCE:")
        print(f"   Total Requests: {total_requests}")
        print(f"   Cache Hit Ratio: {overall_hit_ratio:.1f}%")
        print(f"   API Calls Saved: {total_hits}")
        print(f"   API Calls Made: {total_api_calls}")
    else:
        print("\n   No cache activity yet")
    
    print("=" * 50)