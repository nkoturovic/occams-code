---
summary: "Coroutine-based async HTTP server using Boost.Asio + Boost.Beast"
type: pattern
tags: [cpp, boost, asio, beast, http, async, coroutines, networking]
sources: []
related: cpp
created: 2026-04-09
updated: 2026-04-09
confidence: high
---

# Boost.Asio + Beast Async HTTP Server

Based on the official Beast awaitable example:
https://github.com/boostorg/beast/blob/boost-1.84.0/example/http/server/awaitable/http_server_awaitable.cpp

## Thread Pool Setup

```cpp
const auto numThreads = std::max<std::size_t>(1, std::thread::hardware_concurrency());
asio::io_context context{static_cast<int>(numThreads)};

// Spawn coroutine before running
asio::co_spawn(context, RunServer(endpoint, routes), asio::detached);

// Run numThreads-1 worker threads
std::vector<std::jthread> pool;
pool.reserve(numThreads - 1);
for (auto _ : std::views::iota(0u, numThreads - 1))
  pool.emplace_back([&context] { context.run(); });
context.run();  // main thread also runs
```

**Key:** `io_context` initialized with `numThreads` so it can use the full pool.

## Accept Loop

```cpp
asio::awaitable<void> RunServer(tcp::endpoint ep, std::span<const Route> routes) {
  auto executor = co_await asio::this_coro::executor;
  tcp::acceptor acceptor(executor, ep);
  acceptor.set_option(tcp::acceptor::reuse_address(true));

  for (;;) {
    auto [ec, socket] = co_await acceptor.async_accept(asio::as_tuple(asio::use_awaitable));
    if (ec) {
      if (ec == asio::error::operation_aborted) break;
      // Transient error: back off 100ms and retry
      asio::steady_timer t(executor, 100ms);
      co_await t.async_wait(asio::use_awaitable);
      continue;
    }
    asio::co_spawn(executor, RunSession(std::move(socket), routes), asio::detached);
  }
}
```

- `asio::as_tuple` + structured binding → no exceptions from async errors
- Transient accept errors → sleep + retry instead of crashing
- Each session is an independent coroutine (`asio::detached`)

## Session / Keep-Alive Loop

```cpp
asio::awaitable<std::expected<void, Error>> RunSession(tcp::socket socket, std::span<const Route> routes) {
  beast::tcp_stream stream(std::move(socket));
  beast::flat_buffer buffer;
  HttpRequest req;
  beast::error_code ec;

  for (;;) {
    stream.expires_after(30s);
    req = {};  // reset for reuse

    std::tie(ec, std::ignore) = co_await http::async_read(stream, buffer, req, asio::as_tuple(asio::use_awaitable));
    if (ec == http::error::end_of_stream) break;
    if (ec) co_return std::unexpected(Error{"read failed", ec});

    auto resp = co_await HandleRequest(req, routes);
    auto [msg, status, size] = CreateHttpResponse(std::move(resp), req);
    const bool keepAlive = msg.keep_alive();

    std::tie(ec, std::ignore) = co_await beast::async_write(stream, std::move(msg), asio::as_tuple(asio::use_awaitable));
    if (ec) co_return std::unexpected(Error{"write failed", ec});

    if (!keepAlive) break;
  }

  beast::error_code sderr;
  stream.socket().shutdown(tcp::socket::shutdown_send, sderr);
  co_return {};
}
```

- 30s idle timeout via `stream.expires_after`
- `flat_buffer` reused across requests in keep-alive loop
- `beast::http::message_generator` for efficient response streaming

## Routing

```cpp
struct Route {
  http::verb method;
  std::string_view path;
  Handler handler;  // move_only_function<awaitable<Response>(const HttpRequest&) const>
};

asio::awaitable<Response> HandleRequest(const HttpRequest& req, std::span<const Route> routes) {
  const auto url = boost::urls::parse_origin_form(req.target());
  if (!url) co_return ErrorResponse{bad_request, "Malformed URL"};

  const std::string_view path = url->path();
  auto it = std::ranges::find_if(routes, [&](auto& r) {
    return r.path == path && r.method == req.method();
  });

  // HEAD → GET fallback
  if (it == routes.end() && req.method() == http::verb::head)
    it = std::ranges::find_if(routes, [&](auto& r) { return r.path == path && r.method == http::verb::get; });

  if (it != routes.end()) co_return co_await std::invoke(it->handler, req);

  // 405 if path matches but method doesn't
  if (std::ranges::find(routes, path, &Route::path) != routes.end())
    co_return ErrorResponse{method_not_allowed, "Method not allowed"};

  co_return ErrorResponse{not_found, "404 Not Found"};
}
```

## HTTP Client (Fetch)

```cpp
asio::awaitable<std::expected<HttpResponse, Error>> Fetch(
    std::string_view host, std::string_view target, std::string_view port = "80") {
  auto executor = co_await asio::this_coro::executor;
  tcp::resolver resolver(executor);
  beast::tcp_stream stream(executor);
  stream.expires_after(5s);

  auto [ec, endpoints] = co_await resolver.async_resolve(host, port, asio::as_tuple(asio::use_awaitable));
  if (ec) co_return std::unexpected(Error{"resolve failed", ec});

  std::tie(ec, std::ignore) = co_await stream.async_connect(endpoints, asio::as_tuple(asio::use_awaitable));
  if (ec) co_return std::unexpected(Error{"connect failed", ec});

  http::request<http::empty_body> req{http::verb::get, target, 11};
  req.set(http::field::host, host);
  // ... write, read, shutdown
  co_return resp;
}
```

## Graceful Shutdown

```cpp
asio::signal_set signals(context, SIGINT, SIGTERM);
signals.async_wait([&](auto, auto) { context.stop(); });
```

`context.stop()` causes all `context.run()` calls to return, and `std::jthread` pool cleans up.

## CMake Dependencies

```cmake
find_package(Boost 1.84 REQUIRED CONFIG COMPONENTS system json url)
target_link_libraries(target PRIVATE Boost::system Boost::json Boost::url Threads::Threads)
```

Beast is header-only; linked via `Boost::system`.

## Response Types

```cpp
struct TextResponse  { std::string text; };
struct JsonResponse  { boost::json::value jsonVal; };
struct ErrorResponse { http::status statusCode; std::string errMsg; };
using Response = std::variant<TextResponse, JsonResponse, ErrorResponse>;
```

`CreateHttpResponse` uses `std::visit(overloaded{...}, response)` to finalize into `message_generator`.

## Checklist

- [ ] `io_context` size = `hardware_concurrency()`
- [ ] `expires_after` on every stream before read/write
- [ ] Transient accept error retry (not crash)
- [ ] HEAD → GET fallback in router
- [ ] `keep_alive` checked before loop exit
- [ ] `shutdown_send` on socket after session ends
- [ ] `signal_set` for graceful SIGINT/SIGTERM
- [ ] stdout line-buffered, stderr unbuffered (log flush)

## Related
- [[cpp]]
