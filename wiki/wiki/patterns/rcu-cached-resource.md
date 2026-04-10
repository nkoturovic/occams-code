---
summary: "RCU-style CachedResource<T,Token> pattern for hot-reloadable read-heavy data"
type: pattern
tags: [cpp, concurrency, rcu, cache, hot-reload, shared_mutex, design-pattern]
sources: []
related: cpp
created: 2026-04-09
updated: 2026-04-09
confidence: high
---

# RCU Cached Resource Pattern

## Problem

Data that is read millions of times per second but changes rarely (config files, geodata, feature flags).
Reads must be lock-free (or nearly so). Writes are rare and can be expensive.

## Solution: Read-Copy-Update via `CachedResource<T, Token>`

```
┌────────────┐   probe()    ┌──────────────┐
│  Watchdog  │ ──────────▶  │   Probe fn   │  → returns Token (e.g. mtime)
│  thread    │              └──────────────┘
│            │   loader()   ┌──────────────┐
│            │ ──────────▶  │   Loader fn  │  → returns T (the data)
└────────────┘              └──────────────┘
                                   │
                            shared_ptr<const T>
                                   │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                       ▼
      Reader 1              Reader 2               Reader N
   (shared_lock)          (shared_lock)           (shared_lock)
```

## Implementation Sketch

```cpp
template <typename T, typename Token>
class CachedResource {
 public:
  using Handle = std::shared_ptr<const T>;
  using Probe  = std::move_only_function<std::expected<Token, Error>() const>;
  using Loader = std::move_only_function<std::expected<T, Error>() const>;

  CachedResource(Probe probe, Loader loader);

  [[nodiscard]] Handle Get() const {   // zero-copy, readers run concurrently
    std::shared_lock lock(m_mutex);
    return m_data;
  }

  bool Update() {                      // called by watchdog thread
    auto token = m_probe();
    if (!token || *token == m_token) return false;  // no change
    if (Reload()) { m_token = *token; return true; }
    return false;
  }

 private:
  bool Reload() {                      // expensive load, then fast swap
    auto newData = m_loader();
    if (!newData) return false;
    auto ptr = std::make_shared<T>(*std::move(newData));
    std::unique_lock lock(m_mutex);    // only locked for pointer swap
    m_data = std::move(ptr);
    return true;
  }

  Probe  m_probe;
  Loader m_loader;
  Token  m_token;
  Handle m_data;
  mutable std::shared_mutex m_mutex;
};
```

## Key Properties

| Property | How |
|---|---|
| **Zero-copy reads** | `shared_ptr<const T>` snapshot — reader holds ref, writer swaps pointer |
| **No reader stall during load** | Expensive `Loader` runs before acquiring unique_lock |
| **Hot reload** | Watchdog thread polls `Probe`; on token change runs `Loader` then swaps |
| **Token-based invalidation** | Any comparable type: file mtime, etag, version counter, checksum |
| **Startup safety** | Constructor calls probe + load; throws on failure — fail-fast at init |

## Watchdog Pattern

```cpp
std::jthread watchdog([&] {
  while (!context.stopped()) {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    if (resource.Update()) {
      Log<Info>("Hot-reloaded {}", name);
    }
  }
});
```

- `std::jthread` joins automatically on scope exit
- Poll interval tunable (5s is a reasonable default for config/geodata)
- Watchdog itself needs no synchronization with readers

## Concrete Instantiation for Files

```cpp
using CachedFile = CachedResource<std::string, std::filesystem::file_time_type>;

auto FileProbe(std::filesystem::path p) {
  return [p = std::move(p)]() -> std::expected<file_time_type, Error> {
    std::error_code ec;
    auto t = std::filesystem::last_write_time(p, ec);
    if (ec) return std::unexpected(Error{"mtime failed", ec});
    return t;
  };
}
auto FileLoader(std::filesystem::path p) {
  return [p = std::move(p)]() { return ReadFile(p); };
}
```

## When to Use

- Read >> Write ratio (>1000:1)
- Data fits in memory
- Stale reads acceptable for a polling interval
- Want zero reader synchronization overhead in steady state

## Alternatives

| Alternative | Trade-off |
|---|---|
| `std::atomic<shared_ptr<T>>` | Simpler for single value; no token/probe logic |
| `folly::RWSpinLock` | Better throughput on short critical sections |
| Message-passing (channel) | Cleaner for push-based invalidation |

## Related
- [[cpp]]
