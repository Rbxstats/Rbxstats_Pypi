# RbxStats API Client

A comprehensive Python client for the RbxStats API, providing both synchronous and asynchronous access to Roblox data.

## Features

- 🔄 Synchronous and asynchronous request support
- 🔒 Automatic rate limit handling and retries
- 🛡️ Detailed error handling and logging
- 📦 Response caching for improved performance
- 📊 Comprehensive API coverage for Roblox data

## Installation

```bash
pip install rbxstats
```

## Quick Start

```python
from rbxstats import RbxStatsClient

# Initialize the client with your API key
client = RbxStatsClient("your_api_key_here")

# Make a request
response = client.versions.latest()

# Access the data
latest_version = response.data
print(f"Latest Roblox Version: {latest_version['Windows']}")
```

## Configuration

You can customize the client's behavior with the `ClientConfig` class:

```python
from rbxstats import RbxStatsClient, ClientConfig, LogLevel

config = ClientConfig(
    timeout=15,              # Request timeout in seconds
    max_retries=5,           # Maximum retry attempts
    retry_delay=2,           # Initial delay between retries (exponential backoff applied)
    auto_retry=True,         # Automatically retry failed requests
    log_level=LogLevel.INFO, # Logging level
    cache_ttl=300            # Cache time-to-live in seconds
)

client = RbxStatsClient("your_api_key_here", config=config)
```

## Working with Responses

All API methods return an `ApiResponse` object containing:

- `data`: The actual API response data
- `status_code`: HTTP status code
- `headers`: Response headers
- `request_time`: Time taken for the request in seconds
- `rate_limit_remaining`: Remaining API requests (if provided by the API)
- `rate_limit_reset`: Time until rate limit reset (if provided by the API)

```python
response = client.offsets.all()

# Access response data
offsets_data = response.data

# Access metadata
print(f"Status code: {response.status_code}")
print(f"Request time: {response.request_time:.2f} seconds")
print(f"Rate limit remaining: {response.rate_limit_remaining}")
```

## API Reference

### Offsets

Methods for retrieving Roblox offset data.

```python
# Get all offsets
all_offsets = client.offsets.all().data

# Get a specific offset by name
camera_pos = client.offsets.by_name("CameraPosition").data['CameraPosition']

# Search offsets by prefix
input_offsets = client.offsets.by_prefix("Input").data['Input']

# Get camera-related offsets
camera_offsets = client.offsets.camera().data

# Search offsets by keyword
search_results = client.offsets.search("player").data['player']
```

### Exploits

Methods for retrieving information about Roblox exploits.

```python
# Get all exploits
all_exploits = client.exploits.all().data

# Get Windows-compatible exploits
windows_exploits = client.exploits.windows().data

# Get Mac-compatible exploits
mac_exploits = client.exploits.mac().data

# Get undetected exploits
undetected = client.exploits.undetected().data

# Get detected exploits
detected = client.exploits.detected().data

# Get free exploits
free_exploits = client.exploits.free().data

# Get exploit by name
synapse = client.exploits.by_name("Synapse")

# Compare two exploits
comparison = client.exploits.compare("Synapse", "KRNL").data
```

### Versions

Methods for retrieving Roblox version information.

```python
# Get latest Roblox version
latest = client.versions.latest().data['Windows']

# Get future/beta Roblox version
future = client.versions.future().data['Windows']

# Get version history (last 10 versions by default)
history = client.versions.history().data
history_20 = client.versions.history(limit=20).data

# Get specific version
specific = client.versions.by_version("0.547.0.4242435").data
```

### Game

Methods for retrieving information about Roblox games.

```python
# Get game information by ID
adopt_me = client.game.by_id(920587237).data['gameName']
```
### Stats

Methods for retrieving general statistics.

```python
# Get API status
api_status = client.stats.api_status().data

# Get Roblox services status
roblox_status = client.stats.roblox_status().data

# Get current player count
player_count = client.stats.player_count().data
```

## Asynchronous Usage

All methods have asynchronous counterparts with `_async` suffix:

```python
import asyncio
from rbxstats import RbxStatsClient

async def main():
    client = RbxStatsClient("your_api_key_here")
    
    # Make async requests
    latest_version = await client.versions.latest_async()
    game_info = await client.game.by_id_async(920587237)
    
    print(f"Latest version: {latest_version.data['version']}")
    print(f"Game name: {game_info.data['name']}")
    
    # Don't forget to close the client
    await client.close()

asyncio.run(main())
```

## Handling Errors

The library provides specific exception classes for different error types:

```python
from rbxstats import RbxStatsClient
from rbxstats.exceptions import (
    RbxStatsError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ServerError
)

client = RbxStatsClient("your_api_key_here")

try:
    response = client.game.by_id(123456789)
    game_data = response.data['gameName']
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Try again in {e.retry_after} seconds")
except NotFoundError:
    print("Game not found")
except ServerError:
    print("API server error")
except RbxStatsError as e:
    print(f"General error: {str(e)}")
```

## Advanced Usage

### Configuring Cache

Control caching behavior to improve performance:

```python
# Set cache TTL to 5 minutes
client.set_cache_ttl(300)

# Clear the cache
client.clear_cache()

# Disable cache for a specific request
no_cache_response = client.versions.latest(use_cache=False)
```

### Customizing Headers

Add custom headers to all requests:

```python
client.set_headers({
    "X-Custom-Header": "value",
    "User-Agent": "MyApp/1.0"
})
```

### Adjusting Timeout

Update the request timeout:

```python
# Set timeout to 30 seconds
client.set_timeout(30)
```

### Context Managers

Use the client as a context manager:

```python
# Synchronous context manager
with RbxStatsClient("your_api_key_here") as client:
    response = client.versions.latest()
    print(response.data)
    
# Asynchronous context manager
async with RbxStatsClient("your_api_key_here") as client:
    response = await client.versions.latest_async()
    print(response.data)
```

## Logging

Adjust the logging level to see more or less information:

```python
from rbxstats import RbxStatsClient, LogLevel

client = RbxStatsClient("your_api_key_here")

# Set log level
client.set_log_level(LogLevel.DEBUG)  # Verbose logging
client.set_log_level(LogLevel.ERROR)  # Only log errors
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
