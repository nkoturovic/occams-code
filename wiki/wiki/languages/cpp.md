---
summary: C++ conventions and best practices based on the C++ Core Guidelines
type: language
tags:
  - cpp
  - c++23
  - core-guidelines
  - conventions
  - style
  - best-practices
sources: []
related: boost-asio-beast-http, rcu-cached-resource
created: 2026-04-09
updated: 2026-04-09
confidence: high
---

# C++ Conventions

**Authoritative Reference:** [C++ Core Guidelines](https://github.com/isocpp/cppcoreguidelines) — Bjarne Stroustrup & Herb Sutter.

> "Within C++ is a smaller, simpler, safer language struggling to get out." — Bjarne Stroustrup

The Guidelines focus on relatively high-level issues: interfaces, resource management, memory management, and concurrency. They lead to statically type-safe code with no resource leaks.

## Core Principles (from Guidelines)

- **P.1: Express ideas directly in code** — Compilers don't read comments
- **P.2: Write in ISO Standard C++** — Avoid extensions
- **P.3: Express intent** — Say what should be done, not just how
- **P.4: Prefer static type safety** — Use `std::variant` over unions, `span` over pointers
- **P.5: Prefer compile-time checking** — Use `static_assert`
- **P.6: Check at run time what can't be checked at compile time**
- **P.7: Catch run-time errors early**
- **P.8: Don't leak resources** — Use RAII
- **P.9: Don't waste time or space**
- **P.10: Prefer immutable data**
- **P.11: Encapsulate messy constructs**

## Interview Assignment Patterns

The following patterns are extracted from a time-boxed interview assignment. Standard: **C++23**.

> These reflect what was practical under interview time constraints. Treat as a practical complement to the Guidelines.

## Formatting

- **Style**: Google, 120-column limit, clang-format enforced
- **`.clang-format`**: `BasedOnStyle: Google`, `ColumnLimit: 120`, `AlignAfterOpenBracket: DontAlign`, `ContinuationIndentWidth: 2`
- `clang-format off/on` blocks for visitor/lambda tables where auto-format hurts readability

## Error Handling

- **Use `std::expected<T, Error>`** instead of exceptions for hot-path / async code
- Reserve exceptions for startup failures only (e.g., configuration load)
- `Error` struct carries `const char* msg` + `std::error_code ec`; `ToString()` renders both
- Chain errors with `std::unexpected(Error{...})` — no stack unwinding

```cpp
struct Error {
  const char* msg{nullptr};
  std::error_code ec{};
  std::string ToString() const;
};
// Usage
[[nodiscard]] std::expected<std::string, Error> ReadFile(const std::filesystem::path& path);
```

## Sum Types / Discriminated Unions

- Use `std::variant` for closed sets of response/result types
- Use the `overloaded` helper for pattern matching via `std::visit`:

```cpp
template <class... Ts>
struct overloaded : Ts... { using Ts::operator()...; };
template <class... Ts>
overloaded(Ts...) -> overloaded<Ts...>;

std::visit(overloaded{
  [](TextResponse& r) { ... },
  [](JsonResponse& r) { ... },
  [](ErrorResponse& r) { ... },
}, response);
```

## Async / Coroutines

- **`asio::awaitable<T>`** for all async functions; use `co_return` / `co_await`
- **`asio::as_tuple`** with structured bindings for error handling (avoids exceptions):
  ```cpp
  auto [ec, socket] = co_await acceptor.async_accept(asio::as_tuple(asio::use_awaitable));
  ```
- **`std::tie(ec, std::ignore)`** for operations where the size/count return is unused
- `std::move_only_function` for handler types that capture unique resources

## Callbacks / Handlers

```cpp
// Handler type that stores coroutine-returning lambdas
using Handler = std::move_only_function<asio::awaitable<Response>(const HttpRequest&) const>;
```
- `std::move_only_function` is preferred over `std::function` when moves are sufficient (avoids copy overhead)

## Threading

- `std::jthread` for all background threads (RAII, automatic join)
- Size thread pool to `std::thread::hardware_concurrency()` with `std::max(1, ...)` guard
- Use `std::shared_mutex` for read-heavy data: `shared_lock` for reads, `unique_lock` for writes

## File I/O

- **Zero-copy read** via `std::string::resize_and_overwrite`:
  ```cpp
  content.resize_and_overwrite(fsize, [&](char* buf, std::size_t n) {
    file.read(buf, n);
    return file.gcount();  // actual bytes read
  });
  ```
- Always pre-check `std::filesystem::file_size` before opening to preallocate

## Logging

- **Consteval log level strings** — no runtime string lookup
- **Stack-allocated buffer** with `std::array<char, 1024>` + `static_assert` on arg size
- **Compile-time level filtering** with `if constexpr`
- Error/warning → `stderr`; info/access/debug → `stdout`
- Force buffering mode at startup: `_IOLBF` for stdout, `_IONBF` for stderr

```cpp
template <LogLevel Level, typename... Args>
void Log(std::format_string<Args...> fmt, Args&&... args) {
  if constexpr (Level > ActiveLogLevel) return;
  static_assert((sizeof(Args) + ...) < 512, "Log arguments too large for stack");
  // ...
}
```

## Modern Ranges / Algorithms

- `std::ranges::find_if` over manual loops
- `std::views::iota(0u, N)` for index ranges without raw ints
- `std::ranges::find(container, value, projection)` for projection-based find

## Environment Variables

```cpp
inline std::optional<std::string_view> GetEnv(const char* key) noexcept {
  if (const char* val = std::getenv(key); val && *val) return std::string_view{val};
  return std::nullopt;
}
```
- Returns `std::optional<std::string_view>` — zero allocation, RAII-safe

## Build

- CMake 3.28+, `CMAKE_CXX_STANDARD 23`, `CMAKE_CXX_STANDARD_REQUIRED ON`
- Pass version and app name as compile definitions:
  ```cmake
  target_compile_definitions(target PRIVATE APPNAME="${PROJECT_NAME}" VERSION="${APP_VERSION}")
  ```
- Validate required args at cmake time with `message(FATAL_ERROR ...)`

## Related
- [[boost-asio-beast-http]]
- [[rcu-cached-resource]]
