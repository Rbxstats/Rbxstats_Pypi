import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, TypeVar, Generic, cast
from enum import Enum
from dataclasses import dataclass
import time
from urllib.parse import urljoin
from .exceptions import import RbxStatsError, AuthenticationError, RateLimitError, NotFoundError, ServerError

import requests
import aiohttp
from requests.exceptions import HTTPError, Timeout, RequestException

T = TypeVar('T')

class LogLevel(Enum):
    """Log levels for the RbxStats client."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

@dataclass
class ClientConfig:
    """Configuration for the RbxStats client."""
    timeout: int = 10
    max_retries: int = 3
    retry_delay: int = 1
    auto_retry: bool = True
    log_level: LogLevel = LogLevel.INFO
    cache_ttl: int = 60  # Cache time-to-live in seconds

class Cache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, ttl: int = 60):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if it exists and is not expired."""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        """Cache a value with expiration based on TTL."""
        self.cache[key] = (value, time.time() + self.ttl)
        
    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        
    def set_ttl(self, ttl: int) -> None:
        """Update the cache TTL."""
        self.ttl = ttl

class ApiResponse(Generic[T]):
    """Wrapper for API responses with metadata."""
    
    def __init__(self, 
                 data: T, 
                 status_code: int, 
                 headers: Dict[str, str],
                 request_time: float):
        self.data = data
        self.status_code = status_code
        self.headers = headers
        self.request_time = request_time
        
    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """Return remaining rate limit if available in headers."""
        return int(self.headers.get('X-RateLimit-Remaining', -1)) if 'X-RateLimit-Remaining' in self.headers else None
    
    @property
    def rate_limit_reset(self) -> Optional[int]:
        """Return rate limit reset time if available in headers."""
        return int(self.headers.get('X-RateLimit-Reset', 0)) if 'X-RateLimit-Reset' in self.headers else None

class RbxStatsClient:
    """
    A comprehensive client for the RbxStats API with advanced features.
    
    Features:
    - Synchronous and asynchronous request support
    - Automatic rate limit handling and retries
    - Comprehensive error handling and logging
    - Response caching
    - Detailed response metadata
    """
    
    BASE_URL = "https://api.rbxstats.xyz/api"
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, config: Optional[ClientConfig] = None):
        """
        Initialize the RbxStats API client.
        
        Args:
            api_key: Your RbxStats API key
            base_url: Optional custom API base URL
            config: Optional client configuration
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.config = config or ClientConfig()
        
        # Set up logging
        self.logger = logging.getLogger("rbxstats")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(self.config.log_level.value)
        
        # Initialize headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "RbxStatsClient/2.0",
            "Accept": "application/json"
        }
        
        # Create cache
        self.cache = Cache(ttl=self.config.cache_ttl)
        
        # Initialize session for reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Initialize async session lazily
        self._async_session = None
        
        # Initialize API resources
        self._offsets = self.Offsets(self)
        self._exploits = self.Exploits(self)
        self._versions = self.Versions(self)
        self._game = self.Game(self)
        self._user = self.User(self)
        self._stats = self.Stats(self)
    
    @property
    def async_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of async session."""
        if self._async_session is None or self._async_session.closed:
            self._async_session = aiohttp.ClientSession(headers=self.headers)
        return self._async_session
    
    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for an API endpoint."""
        return urljoin(f"{self.base_url}/", endpoint)
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process response and handle errors."""
        status_code = response.status_code
        
        if status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                raise RbxStatsError(f"Invalid JSON response: {e}")
        
        if status_code == 401:
            raise AuthenticationError("Invalid API key or unauthorized access")
        
        if status_code == 404:
            raise NotFoundError("Requested resource not found")
        
        if status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(retry_after)
        
        if 500 <= status_code < 600:
            raise ServerError(f"Server error: {status_code}")
        
        # Handle other error cases
        error_msg = f"API request failed with status code {status_code}"
        try:
            error_data = response.json()
            if "error" in error_data:
                error_msg = f"{error_msg}: {error_data['error']}"
        except (ValueError, KeyError):
            pass
        
        raise RbxStatsError(error_msg)
    
    async def _handle_async_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Process async response and handle errors."""
        status_code = response.status
        
        if status_code == 200:
            try:
                return await response.json()
            except ValueError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                raise RbxStatsError(f"Invalid JSON response: {e}")
        
        if status_code == 401:
            raise AuthenticationError("Invalid API key or unauthorized access")
        
        if status_code == 404:
            raise NotFoundError("Requested resource not found")
        
        if status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(retry_after)
        
        if 500 <= status_code < 600:
            raise ServerError(f"Server error: {status_code}")
        
        # Handle other error cases
        error_msg = f"API request failed with status code {status_code}"
        try:
            error_data = await response.json()
            if "error" in error_data:
                error_msg = f"{error_msg}: {error_data['error']}"
        except (ValueError, KeyError):
            pass
        
        raise RbxStatsError(error_msg)
    
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
        """
        Make a GET request to the API with error handling and retries.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            use_cache: Whether to use cached response if available
        
        Returns:
            ApiResponse object containing the response data and metadata
        """
        if params is None:
            params = {}
        
        # Add API key to params
        params["api"] = self.api_key
        
        # Generate cache key
        cache_key = f"{endpoint}:{str(sorted(params.items()))}"
        
        # Check cache first if enabled
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.debug(f"Cache hit for {endpoint}")
                return cached
        
        url = self._build_url(endpoint)
        self.logger.debug(f"Making GET request to {url}")
        
        retries = 0
        last_exception = None
        
        while retries <= self.config.max_retries:
            try:
                start_time = time.time()
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                )
                request_time = time.time() - start_time
                
                data = self._handle_response(response)
                api_response = ApiResponse(
                    data=data,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    request_time=request_time
                )
                
                # Cache successful response
                if use_cache:
                    self.cache.set(cache_key, api_response)
                
                return api_response
                
            except RateLimitError as e:
                last_exception = e
                if not self.config.auto_retry or retries >= self.config.max_retries:
                    raise
                
                retry_after = e.retry_after or self.config.retry_delay
                self.logger.warning(f"Rate limit exceeded. Retrying in {retry_after} seconds.")
                time.sleep(retry_after)
                
            except (HTTPError, Timeout, RequestException, RbxStatsError) as e:
                last_exception = e
                if not self.config.auto_retry or retries >= self.config.max_retries:
                    if isinstance(e, RbxStatsError):
                        raise
                    raise RbxStatsError(f"Request failed: {str(e)}")
                
                retry_delay = self.config.retry_delay * (2 ** retries)  # Exponential backoff
                self.logger.warning(f"Request failed: {str(e)}. Retrying in {retry_delay} seconds.")
                time.sleep(retry_delay)
            
            retries += 1
        
        # If we got here, all retries failed
        if last_exception:
            if isinstance(last_exception, RbxStatsError):
                raise last_exception
            raise RbxStatsError(f"All retries failed: {str(last_exception)}")
        
        # This should never happen, but just in case
        raise RbxStatsError("Request failed for unknown reason")
    
    async def _async_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
        """
        Make an asynchronous GET request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            use_cache: Whether to use cached response if available
        
        Returns:
            ApiResponse object containing the response data and metadata
        """
        if params is None:
            params = {}
        
        # Add API key to params
        params["api"] = self.api_key
        
        # Generate cache key
        cache_key = f"async:{endpoint}:{str(sorted(params.items()))}"
        
        # Check cache first if enabled
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.debug(f"Cache hit for {endpoint}")
                return cached
        
        url = self._build_url(endpoint)
        self.logger.debug(f"Making async GET request to {url}")
        
        retries = 0
        last_exception = None
        
        while retries <= self.config.max_retries:
            try:
                start_time = time.time()
                
                async with self.async_session.get(url, params=params, timeout=self.config.timeout) as response:
                    request_time = time.time() - start_time
                    data = await self._handle_async_response(response)
                    
                    api_response = ApiResponse(
                        data=data,
                        status_code=response.status,
                        headers=dict(response.headers),
                        request_time=request_time
                    )
                    
                    # Cache successful response
                    if use_cache:
                        self.cache.set(cache_key, api_response)
                    
                    return api_response
                    
            except RateLimitError as e:
                last_exception = e
                if not self.config.auto_retry or retries >= self.config.max_retries:
                    raise
                
                retry_after = e.retry_after or self.config.retry_delay
                self.logger.warning(f"Rate limit exceeded. Retrying in {retry_after} seconds.")
                await asyncio.sleep(retry_after)
                
            except (aiohttp.ClientError, asyncio.TimeoutError, RbxStatsError) as e:
                last_exception = e
                if not self.config.auto_retry or retries >= self.config.max_retries:
                    if isinstance(e, RbxStatsError):
                        raise
                    raise RbxStatsError(f"Async request failed: {str(e)}")
                
                retry_delay = self.config.retry_delay * (2 ** retries)  # Exponential backoff
                self.logger.warning(f"Async request failed: {str(e)}. Retrying in {retry_delay} seconds.")
                await asyncio.sleep(retry_delay)
            
            retries += 1
        
        # If we got here, all retries failed
        if last_exception:
            if isinstance(last_exception, RbxStatsError):
                raise last_exception
            raise RbxStatsError(f"All async retries failed: {str(last_exception)}")
        
        # This should never happen, but just in case
        raise RbxStatsError("Async request failed for unknown reason")
    
    def set_headers(self, additional_headers: Dict[str, str]) -> None:
        """
        Set additional headers for API requests.
        
        Args:
            additional_headers: Dict of header names and values
        """
        self.headers.update(additional_headers)
        self.session.headers.update(additional_headers)
        
        # Update async session headers if it exists
        if self._async_session is not None and not self._async_session.closed:
            self._async_session._default_headers.update(additional_headers)
    
    def set_timeout(self, timeout: int) -> None:
        """
        Set custom timeout for requests in seconds.
        
        Args:
            timeout: Timeout in seconds
        """
        self.config.timeout = timeout
    
    def set_log_level(self, level: LogLevel) -> None:
        """
        Set the client's logging level.
        
        Args:
            level: LogLevel enum value
        """
        self.logger.setLevel(level.value)
    
    def set_cache_ttl(self, ttl: int) -> None:
        """
        Set the cache time-to-live in seconds.
        
        Args:
            ttl: Time-to-live in seconds
        """
        self.config.cache_ttl = ttl
        self.cache.set_ttl(ttl)
    
    def clear_cache(self) -> None:
        """Clear the client's response cache."""
        self.cache.clear()
        self.logger.info("Cache cleared")
    
    async def close(self) -> None:
        """Close any open connections and sessions."""
        if self._async_session is not None and not self._async_session.closed:
            await self._async_session.close()
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # API Resource Classes
    class Offsets:
        """API operations related to offsets."""
        
        def __init__(self, client):
            self.client = client
        
        def all(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get all available offsets."""
            return self.client._get("offsets", use_cache=use_cache)
        
        async def all_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get all available offsets asynchronously."""
            return await self.client._async_get("offsets", use_cache=use_cache)
        
        def by_name(self, name: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get offset by its exact name."""
            return self.client._get(f"offsets/{name}", use_cache=use_cache)
        
        async def by_name_async(self, name: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get offset by its exact name asynchronously."""
            return await self.client._async_get(f"offsets/{name}", use_cache=use_cache)
        
        def by_prefix(self, prefix: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get offsets by prefix matching."""
            return self.client._get(f"offsets/prefix/{prefix}", use_cache=use_cache)
        
        async def by_prefix_async(self, prefix: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get offsets by prefix matching asynchronously."""
            return await self.client._async_get(f"offsets/prefix/{prefix}", use_cache=use_cache)
        
        def camera(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get camera-related offsets."""
            return self.client._get("offsets/camera", use_cache=use_cache)
        
        async def camera_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get camera-related offsets asynchronously."""
            return await self.client._async_get("offsets/camera", use_cache=use_cache)
        
        def search(self, query: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for offsets by keyword."""
            return self.client._get("offsets/search", params={"q": query}, use_cache=use_cache)
        
        async def search_async(self, query: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for offsets by keyword asynchronously."""
            return await self.client._async_get("offsets/search", params={"q": query}, use_cache=use_cache)
    
    class Exploits:
        """API operations related to exploits."""
        
        def __init__(self, client):
            self.client = client
        
        def all(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get all exploits information."""
            return self.client._get("exploits", use_cache=use_cache)
        
        async def all_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get all exploits information asynchronously."""
            return await self.client._async_get("exploits", use_cache=use_cache)
        
        def windows(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Windows-compatible exploits."""
            return self.client._get("exploits/windows", use_cache=use_cache)
        
        async def windows_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Windows-compatible exploits asynchronously."""
            return await self.client._async_get("exploits/windows", use_cache=use_cache)
        
        def mac(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Mac-compatible exploits."""
            return self.client._get("exploits/mac", use_cache=use_cache)
        
        async def mac_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Mac-compatible exploits asynchronously."""
            return await self.client._async_get("exploits/mac", use_cache=use_cache)
        
        def undetected(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploits that are currently undetected."""
            return self.client._get("exploits/undetected", use_cache=use_cache)
        
        async def undetected_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploits that are currently undetected asynchronously."""
            return await self.client._async_get("exploits/undetected", use_cache=use_cache)
        
        def detected(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploits that are currently detected."""
            return self.client._get("exploits/detected", use_cache=use_cache)
        
        async def detected_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploits that are currently detected asynchronously."""
            return await self.client._async_get("exploits/detected", use_cache=use_cache)
        
        def free(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get free exploits."""
            return self.client._get("exploits/free", use_cache=use_cache)
        
        async def free_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get free exploits asynchronously."""
            return await self.client._async_get("exploits/free", use_cache=use_cache)
        
        def by_name(self, name: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploit by its exact name."""
            return self.client._get(f"exploits/{name}", use_cache=use_cache)
        
        async def by_name_async(self, name: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get exploit by its exact name asynchronously."""
            return await self.client._async_get(f"exploits/{name}", use_cache=use_cache)
        
        def compare(self, first: str, second: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Compare two exploits by name."""
            return self.client._get("exploits/compare", params={"first": first, "second": second}, use_cache=use_cache)
        
        async def compare_async(self, first: str, second: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Compare two exploits by name asynchronously."""
            return await self.client._async_get("exploits/compare", params={"first": first, "second": second}, use_cache=use_cache)
    
    class Versions:
        """API operations related to Roblox versions."""
        
        def __init__(self, client):
            self.client = client
        
        def latest(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get latest Roblox version information."""
            return self.client._get("versions/latest", use_cache=use_cache)
        
        async def latest_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get latest Roblox version information asynchronously."""
            return await self.client._async_get("versions/latest", use_cache=use_cache)
        
        def future(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get future/beta Roblox version information."""
            return self.client._get("versions/future", use_cache=use_cache)
        
        async def future_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get future/beta Roblox version information asynchronously."""
            return await self.client._async_get("versions/future", use_cache=use_cache)
        
        def history(self, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get historical Roblox versions."""
            return self.client._get("versions/history", params={"limit": limit}, use_cache=use_cache)
        
        async def history_async(self, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get historical Roblox versions asynchronously."""
            return await self.client._async_get("versions/history", params={"limit": limit}, use_cache=use_cache)
        
        def by_version(self, version: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get information about a specific version."""
            return self.client._get(f"versions/{version}", use_cache=use_cache)
        
        async def by_version_async(self, version: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get information about a specific version asynchronously."""
            return await self.client._async_get(f"versions/{version}", use_cache=use_cache)
    
    class Game:
        """API operations related to Roblox games."""
        
        def __init__(self, client):
            self.client = client
        
        def by_id(self, game_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get game information by game ID."""
            return self.client._get(f"game/{game_id}", use_cache=use_cache)
        
        async def by_id_async(self, game_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get game information by game ID asynchronously."""
            return await self.client._async_get(f"game/{game_id}", use_cache=use_cache)
        
        def popular(self, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get popular games on Roblox."""
            return self.client._get("games/popular", params={"limit": limit}, use_cache=use_cache)
        
        async def popular_async(self, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get popular games on Roblox asynchronously."""
            return await self.client._async_get("games/popular", params={"limit": limit}, use_cache=use_cache)
        
        def search(self, query: str, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for games by keyword."""
            return self.client._get("games/search", params={"q": query, "limit": limit}, use_cache=use_cache)
        
        async def search_async(self, query: str, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for games by keyword asynchronously."""
            return await self.client._async_get("games/search", params={"q": query, "limit": limit}, use_cache=use_cache)
        
        def stats(self, game_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get detailed stats for a game."""
            return self.client._get(f"game/{game_id}/stats", use_cache=use_cache)
        
        async def stats_async(self, game_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get detailed stats for a game asynchronously."""
            return await self.client._async_get(f"game/{game_id}/stats", use_cache=use_cache)
    
    class User:
        """API operations related to Roblox users."""
        
        def __init__(self, client):
            self.client = client
        
        def by_id(self, user_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get user information by user ID."""
            return self.client._get(f"user/{user_id}", use_cache=use_cache)
        
        async def by_id_async(self, user_id: int, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get user information by user ID asynchronously."""
            return await self.client._async_get(f"user/{user_id}", use_cache=use_cache)
        
        def by_username(self, username: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get user information by username."""
            return self.client._get("user", params={"username": username}, use_cache=use_cache)
        
        async def by_username_async(self, username: str, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get user information by username asynchronously."""
            return await self.client._async_get("user", params={"username": username}, use_cache=use_cache)
                
        def friends(self, user_id: int, limit: int = 20, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get a user's friends list."""
            return self.client._get(f"user/{user_id}/friends", params={"limit": limit}, use_cache=use_cache)
        
        async def friends_async(self, user_id: int, limit: int = 20, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get a user's friends list asynchronously."""
            return await self.client._async_get(f"user/{user_id}/friends", params={"limit": limit}, use_cache=use_cache)
        
        def badges(self, user_id: int, limit: int = 20, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get badges owned by a user."""
            return self.client._get(f"user/{user_id}/badges", params={"limit": limit}, use_cache=use_cache)
        
        async def badges_async(self, user_id: int, limit: int = 20, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get badges owned by a user asynchronously."""
            return await self.client._async_get(f"user/{user_id}/badges", params={"limit": limit}, use_cache=use_cache)
        
        def search(self, query: str, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for users by keyword."""
            return self.client._get("users/search", params={"q": query, "limit": limit}, use_cache=use_cache)
        
        async def search_async(self, query: str, limit: int = 10, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Search for users by keyword asynchronously."""
            return await self.client._async_get("users/search", params={"q": query, "limit": limit}, use_cache=use_cache)
    
    class Stats:
        """API operations related to general statistics."""
        
        def __init__(self, client):
            self.client = client
        
        def api_status(self, use_cache: bool = False) -> ApiResponse[Dict[str, Any]]:
            """Get API status and health information."""
            return self.client._get("stats/status", use_cache=use_cache)
        
        async def api_status_async(self, use_cache: bool = False) -> ApiResponse[Dict[str, Any]]:
            """Get API status and health information asynchronously."""
            return await self.client._async_get("stats/status", use_cache=use_cache)
        
        def roblox_status(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Roblox services status."""
            return self.client._get("stats/roblox", use_cache=use_cache)
        
        async def roblox_status_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get Roblox services status asynchronously."""
            return await self.client._async_get("stats/roblox", use_cache=use_cache)
        
        def player_count(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get current player count on Roblox."""
            return self.client._get("stats/players", use_cache=use_cache)
        
        async def player_count_async(self, use_cache: bool = True) -> ApiResponse[Dict[str, Any]]:
            """Get current player count on Roblox asynchronously."""
            return await self.client._async_get("stats/players", use_cache=use_cache)
    
    # Convenience properties to access API resources
    @property
    def offsets(self) -> Offsets:
        """Get the Offsets API resource."""
        return self._offsets
    
    @property
    def exploits(self) -> Exploits:
        """Get the Exploits API resource."""
        return self._exploits
    
    @property
    def versions(self) -> Versions:
        """Get the Versions API resource."""
        return self._versions
    
    @property
    def game(self) -> Game:
        """Get the Game API resource."""
        return self._game
    
    @property
    def user(self) -> User:
        """Get the User API resource."""
        return self._user
    
    @property
    def stats(self) -> Stats:
        """Get the Stats API resource."""
        return self._stats
