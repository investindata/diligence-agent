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
    
    def _run(self, query: str, **kwargs) -> Any:
        """Execute search with caching logic."""
        cache_key = self._generate_cache_key(query)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check file cache
        cached_result = self._load_from_file_cache(cache_key)
        if cached_result is not None:
            self.memory_cache[cache_key] = cached_result
            return cached_result
        
        # No cache hit, call the actual Serper API
        result = self.serper_tool._run(query=query, **kwargs)
        
        # Cache the result in both memory and file
        self.memory_cache[cache_key] = result
        self._save_to_file_cache(cache_key, result)
        
        return result


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
    
    def _run(self, url: str, **kwargs) -> Any:
        """Execute scraping with caching logic."""
        cache_key = self._generate_cache_key(url)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check file cache
        cached_result = self._load_from_file_cache(cache_key)
        if cached_result is not None:
            self.memory_cache[cache_key] = cached_result
            return cached_result
        
        # No cache hit, call the actual Serper API
        result = self.serper_tool._run(url=url, **kwargs)
        
        # Cache the result in both memory and file
        self.memory_cache[cache_key] = result
        self._save_to_file_cache(cache_key, result)
        
        return result


# Global instances for cache clearing
cached_serper_search = CachedSerperDevTool()
cached_serper_scraper = CachedSerperScrapeWebsiteTool()