import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, TypeVar, Generic, cast
from enum import Enum
from dataclasses import dataclass
import time
from urllib.parse import urljoin

import requests
import aiohttp
from requests.exceptions import HTTPError, Timeout, RequestException

T = TypeVar('T')

class RbxStatsError(Exception):
    """Base exception for all RbxStats client errors."""
    pass

class RateLimitError(RbxStatsError):
    """Raised when API rate limit is exceeded."""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        message = f"API rate limit exceeded. Retry after {retry_after} seconds." if retry_after else "API rate limit exceeded."
        super().__init__(message)

class AuthenticationError(RbxStatsError):
    """Raised when API authentication fails."""
    pass

class NotFoundError(RbxStatsError):
    """Raised when a requested resource is not found."""
    pass

class ServerError(RbxStatsError):
    """Raised when the API server encounters an error."""
    pass

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
