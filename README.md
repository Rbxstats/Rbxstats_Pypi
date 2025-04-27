**RBXStatsClient Usage Guide**

A detailed walkthrough of the `rbxstats` Python client library for interacting with the RbxStats API.

---

## Table of Contents

1. [Installation](#installation)
2. [Imports](#imports)
3. [Client Initialization & Configuration](#initialization--configuration)
4. [Resource Reference & Examples](#resource-reference--examples)
   1. [Offsets](#offsets)
   2. [Versions](#versions)
   3. [Exploits](#exploits)
   4. [Games](#games)
   5. [Users](#users)
   6. [Stats](#stats)
5. [Advanced Configuration](#advanced-configuration)
6. [Error Handling](#error-handling)
7. [Full End-to-End Example](#full-end-to-end-example)

---

## 1. Installation

Install via pip:

```bash
pip install rbxstats
```

Use a virtual environment to isolate dependencies:

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\\Scripts\\activate  # Windows
pip install rbxstats
```

---

## 2. Imports

Two main styles:

```python
# import full module
ingest = __import__('rbxstats')
import rbxstats

# or import specific classesrom rbxstats import RbxStatsClient, ClientConfig, LogLevel
```

---

## 3. Client Initialization & Configuration

```python
from rbxstats import RbxStatsClient, ClientConfig, LogLevel

config = ClientConfig(
    timeout=10,            # seconds per request
    max_retries=3,         # retry attempts on failure
    retry_delay=1,         # seconds between retries
    auto_retry=True,       # automatically retry on 429/5xx
    log_level=LogLevel.INFO,
    cache_ttl=60           # seconds to cache GET responses
)
client = RbxStatsClient(api_key="YOUR_API_KEY", config=config)
```

- **base_url**: override default (`https://api.rbxstats.xyz/api`)
- **Logging**: set via `config.log_level` or `client.set_log_level(...)`
- **Cache**: in-memory; clear with `client.clear_cache()`, TTL via `client.set_cache_ttl(...)`

---

## 4. Resource Reference & Examples

The client exposes these resource groups in order below. Each method returns an `ApiResponse` with `.data`, `.status_code`, `.headers`, and `.request_time`.

### 4.1 Offsets

Offsets are memory addresses for Roblox client functions.

| Method                          | Description                                 | Example call                         |
| ------------------------------- | ------------------------------------------- | ------------------------------------ |
| `offsets.all()`                 | List all offsets                            | `client.offsets.all()`               |
| `offsets.by_name(name)`         | Fetch offset by exact name                  | `client.offsets.by_name("WalkSpeed")` |
| `offsets.by_prefix(prefix)`     | List offsets starting with prefix           | `client.offsets.by_prefix("Cam")`  |
| `offsets.camera()`              | Pre-filtered camera-related offsets         | `client.offsets.camera()`            |
| `offsets.search(query)`         | Full-text search on offset descriptions     | `client.offsets.search("jump")`    |

#### Example: retrieve and inspect camera offsets

```python
resp = client.offsets.camera()
camera_offsets = resp.data.get('offsets', [])
for off in camera_offsets:
    print(off['name'], hex(off['address']))
```  

---

### 4.2 Versions

Roblox client and beta version metadata.

| Method                                 | Description                       | Example                                |
| -------------------------------------- | --------------------------------- | -------------------------------------- |
| `versions.latest()`                    | Current public Roblox version     | `client.versions.latest()`             |
| `versions.future()`                    | Upcoming/beta Roblox version      | `client.versions.future()`             |
| `versions.history(limit)`              | Historical version list           | `client.versions.history(limit=5)`     |
| `versions.by_version(version_str)`     | Info for a specific version       | `client.versions.by_version("0.543.1")` |

#### Example: compare latest vs future

```python
latest = client.versions.latest().datafuture = client.versions.future().data
print("Latest:", latest['version'], "released", latest['released'])
print("Future:", future['version'], "ETA", future['eta'])
```  

---

### 4.3 Exploits

Information on available exploit tools.

| Method                           | Description                              | Example                                           |
| -------------------------------- | ---------------------------------------- | ------------------------------------------------- |
| `exploits.all()`                 | All exploits                             | `client.exploits.all()`                          |
| `exploits.windows()`, `.mac()`   | Platform-specific                        | `client.exploits.windows()`                      |
| `exploits.free()`, `.undetected()` | Filter by cost or detection status     | `client.exploits.free()`                         |
| `exploits.by_name(name)`         | Details on a named exploit               | `client.exploits.by_name("Krnl")`               |
| `exploits.compare(a, b)`         | Compare two exploits feature-by-feature   | `client.exploits.compare("Krnl", "Synapse")` |

#### Example: list free, undetected exploits

```python
resp = client.exploits.free().data
for e in resp['exploits']:
    if e['undetected']:
        print(e['name'], "- version", e['version'])
```  

---

### 4.4 Games

Roblox game metadata.

| Method                                | Description                         | Example                                     |
| ------------------------------------- | ----------------------------------- | ------------------------------------------- |
| `game.by_id(game_id)`                 | Single game info                    | `client.game.by_id(123456789)`              |
| `game.popular(limit)`                 | Top played games                    | `client.game.popular(limit=10)`             |
| `game.search(q, limit)`               | Search by keyword                   | `client.game.search("tycoon", limit=5)`   |
| `game.stats(game_id)`                 | Server & player stats for game      | `client.game.stats(123456789)`              |

---

### 4.5 Users

Roblox user data and relations.

| Method                                   | Description                          | Example                                         |
| ---------------------------------------- | ------------------------------------ | ----------------------------------------------- |
| `user.by_id(user_id)`                    | Profile by ID                        | `client.user.by_id(1)`                          |
| `user.by_username(username)`             | Profile by username                  | `client.user.by_username("builderman")`       |
| `user.friends(user_id, limit)`           | Friends list                         | `client.user.friends(1, limit=20)`              |
| `user.badges(user_id, limit)`            | Owned badges                         | `client.user.badges(1, limit=10)`               |
| `user.search(q, limit)`                  | Search users by keyword              | `client.user.search("gamer", limit=5)`        |

---

### 4.6 Stats

API & Roblox service health and usage.

| Method                           | Description                             | Example                         |
| -------------------------------- | --------------------------------------- | ------------------------------- |
| `stats.api_status()`             | RbxStats API health                     | `client.stats.api_status()`     |
| `stats.roblox_status()`          | Roblox platform service status          | `client.stats.roblox_status()`  |
| `stats.player_count()`           | Current total players online on Roblox  | `client.stats.player_count()`   |

---

## 5. Advanced Configuration

```python
# Add custom HTTP headers\client.set_headers({"X-My-Header":"value"})

# Change timeout mid-session
client.set_timeout(20)

# Adjust logging level
from rbxstats import LogLevel
client.set_log_level(LogLevel.DEBUG)

# Manage cache
client.clear_cache()
client.set_cache_ttl(300)
```

---

## 6. Error Handling

Exceptions raised by the client:

| Exception            | Condition                   | Attributes                  |
| -------------------- | --------------------------- | --------------------------- |
| AuthenticationError  | HTTP 401                    | None                        |
| NotFoundError        | HTTP 404                    | None                        |
| RateLimitError       | HTTP 429                    | `retry_after` (seconds)     |
| ServerError          | HTTP 5xx                    | None                        |
| RbxStatsError        | JSON/network/other failures | None                        |

```python
from rbxstats.exceptions import RateLimitError, RbxStatsError
try:
    resp = client.game.by_id(0)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except RbxStatsError as e:
    print("General API error:", e)
```  

---

## 7. Full End-to-End Example

```python
import asyncio
from rbxstats import RbxStatsClient, ClientConfig, LogLevel

# Setup
config = ClientConfig(log_level=LogLevel.DEBUG)
client = RbxStatsClient(api_key="YOUR_API_KEY", config=config)

# 1. Offsets: find jump-related offsets
offs = client.offsets.search("jump").data['offsets']
print("Jump Offsets:", [o['name'] for o in offs])

# 2. Versions: show latest and next beta
print(client.versions.latest().data)
print(client.versions.future().data)

# 3. Exploits: compare two
comp = client.exploits.compare("Krnl", "Synapse").data
print("Comparison:", comp)

# 4. Game info: top 3 popular
for g in client.game.popular(limit=3).data['games']:
    print(g['id'], g['name'], g['playing'])

# 5. User: builderman friends
u = client.user.by_username("builderman").data
friends = client.user.friends(u['id']).data['friends']
print("Builderman's Friends:",[f['username'] for f in friends])

# 6. Stats: current players
print("Players online:", client.stats.player_count().data['count'])

# Cleanup
client.clear_cache()
client.session.close()
```

Happy scripting with RbxStatsClient!

