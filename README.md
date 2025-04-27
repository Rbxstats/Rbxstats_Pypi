**RBXStatsClient Usage Guide**

This document describes how to install and use the `rbxstats` Python client library to interact with the RbxStats API. It covers:

- Installation
- Import statements
- Configuration and initialization
- Synchronous usage examples
- Asynchronous usage examples
- Advanced configuration (timeouts, retries, logging, caching)
- Error handling
- API resource reference

---

## 1. Installation

Install the `rbxstats` library from PyPI:

```bash
pip install rbxstats
```

> **Note**: If you are installing in a project, consider using a virtual environment:
>
> ```bash
> python -m venv venv
> source venv/bin/activate   # Linux/macOS
> venv\Scripts\activate    # Windows
> pip install rbxstats
> ```

---

## 2. Importing the Library

You can import the library in two ways:

```python
import rbxstats
```

or import specific classes:

```python
from rbxstats import RbxStatsClient, ClientConfig, LogLevel
```

---

## 3. Initialization and Configuration

### 3.1 Basic initialization

Create a client by passing your API key:

```python
from rbxstats import RbxStatsClient

api_key = "YOUR_API_KEY_HERE"
client = RbxStatsClient(api_key)
```

### 3.2 Custom base URL or configuration

You can override the default API base URL or adjust timeouts, retries, logging, and cache TTL via `ClientConfig`:

```python
from rbxstats import RbxStatsClient, ClientConfig, LogLevel

config = ClientConfig(
    timeout=5,            # seconds
    max_retries=5,
    retry_delay=2,        # seconds between retries
    auto_retry=True,
    log_level=LogLevel.DEBUG,
    cache_ttl=120         # cache responses for 120 seconds
)

client = RbxStatsClient(
    api_key="YOUR_API_KEY_HERE",
    base_url="https://api.rbxstats.xyz/api",
    config=config
)
```

---

## 4. Synchronous Usage Examples

### 4.1 Fetching the latest Roblox version

```python
response = client.versions.latest()
print("Status code:", response.status_code)
print("Data:", response.data)
print("Request took:", response.request_time, "seconds")
```

### 4.2 Getting user information by username

```python
resp = client.user.by_username("builderman")
user_data = resp.data
print(f"User ID: {user_data['id']}")
print(f"Username: {user_data['username']}")
```

### 4.3 Listing popular games

```python
games_resp = client.game.popular(limit=5)
for game in games_resp.data.get('games', []):
    print(f"{game['id']}: {game['name']}")
```  

### 4.4 Handling rate limits and retries

By default, the client will automatically retry on rate limits (HTTP 429) and transient errors, up to `max_retries` times. You can disable this:

```python
client.config.auto_retry = False
```  

---

## 5. Asynchronous Usage Examples

```python
import asyncio
from rbxstats import RbxStatsClient

async def main():
    client = RbxStatsClient("YOUR_API_KEY")
    # Fetch player count asynchronously
    resp = await client.stats.player_count_async()
    print("Players online:", resp.data.get('count'))
    await client.close()

asyncio.run(main())
```

---

## 6. Advanced Configuration

### 6.1 Custom headers

```python
client.set_headers({
    "X-Custom-Header": "value"
})
```

### 6.2 Adjusting timeout

```python
client.set_timeout(15)  # 15-second timeout
```

### 6.3 Changing log level at runtime

```python
from rbxstats import LogLevel
client.set_log_level(LogLevel.ERROR)
```

### 6.4 Cache management

- **Clear cache**:
  ```python
  client.clear_cache()
  ```
- **Set cache TTL**:
  ```python
  client.set_cache_ttl(300)  # 5 minutes
  ```

---

## 7. Error Handling

When an error occurs, the client raises one of:

| Exception            | Condition                                          |
| -------------------- | -------------------------------------------------- |
| `AuthenticationError`| HTTP 401                                           |
| `NotFoundError`      | HTTP 404                                           |
| `RateLimitError`     | HTTP 429 (has `retry_after` attribute)             |
| `ServerError`        | HTTP 5xx                                           |
| `RbxStatsError`      | Other errors (JSON parse, network failure, etc.)   |

```python
from rbxstats.exceptions import RateLimitError, RbxStatsError

try:
    resp = client.game.by_id(12345678)
except RateLimitError as e:
    print("Rate limited. Retry after", e.retry_after)
except RbxStatsError as e:
    print("API error:", str(e))
```

---

## 8. API Resource Reference

The `client` exposes the following resources:

| Resource        | Methods                                                                                      |
| --------------- | -------------------------------------------------------------------------------------------- |
| **versions**    | `latest()`, `future()`, `history(limit)`, `by_version(version)`                              |
| **game**        | `by_id(id)`, `popular(limit)`, `search(q, limit)`, `stats(game_id)`                          |
| **user**        | `by_id(id)`, `by_username(username)`, `friends(id, limit)`, `badges(id, limit)`, `search()`|
| **offsets**     | `all()`, `by_name()`, `by_prefix()`, `camera()`, `search()`                                  |
| **exploits**    | `all()`, `windows()`, `mac()`, `undetected()`, `detected()`, `free()`, `by_name()`, `compare()`|
| **stats**       | `api_status()`, `roblox_status()`, `player_count()`                                         |

---

## 9. Full Example

```python
from rbxstats import RbxStatsClient, ClientConfig, LogLevel

# 1. Configure client
config = ClientConfig(timeout=8, max_retries=3, retry_delay=1, auto_retry=True, log_level=LogLevel.DEBUG)
client = RbxStatsClient(api_key="YOUR_API_KEY", config=config)

# 2. Fetch and print latest Roblox version
ver_resp = client.versions.latest()
print("Latest Roblox version:", ver_resp.data.get('version'))

# 3. Search for a user and get their friends
user_resp = client.user.by_username("builderman")
uid = user_resp.data['id']
friends_resp = client.user.friends(uid, limit=10)
print("Builderman's friends:")
for friend in friends_resp.data.get('friends', []):
    print(f"- {friend['username']} (ID: {friend['id']})")

# 4. Get current player count
players_resp = client.stats.player_count()
print("Current players online:", players_resp.data.get('count'))

# 5. Clean up
client.clear_cache()
client.session.close()
```

---

Happy coding with the RbxStatsClient!

