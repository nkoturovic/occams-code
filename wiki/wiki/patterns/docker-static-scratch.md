---
summary: "Multi-stage Docker build producing a minimal static binary on scratch image"
type: pattern
tags: [docker, cpp, security, container, alpine, scratch, static-linking, kubernetes]
sources: []
related:
created: 2026-04-09
updated: 2026-04-09
confidence: high
---

# Docker: Static Binary → Scratch Image

## Pattern

Two-stage Dockerfile: **Alpine builder** compiles a fully static binary, **scratch** final image contains only the binary.

```dockerfile
FROM alpine:3.23 AS cpp_builder

WORKDIR /workspace
RUN apk add --no-cache build-base cmake boost-static boost-dev

COPY CMakeLists.txt adserver.cpp ./

ARG APP_VERSION
RUN if [ -z "$APP_VERSION" ]; then \
      echo "ERROR: APP_VERSION required"; exit 1; fi

RUN cmake -S . -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DAPP_VERSION="$APP_VERSION" \
    -DENABLE_STATIC_BUILD=ON \
    -DCMAKE_EXE_LINKER_FLAGS="-static"

RUN cmake --build build -j$(nproc)
RUN cmake --install build --prefix /dist --strip

FROM scratch
WORKDIR /app
COPY --from=cpp_builder /dist/bin/adserver .
USER 1001
ENTRYPOINT ["./adserver"]
```

## Properties

| Property | Value |
|---|---|
| **Final image size** | ~5–20 MB (binary only, no OS) |
| **Attack surface** | Zero — no shell, no libc, no package manager |
| **Runtime user** | Non-root (UID 1001) |
| **Binary** | Fully static — no dynamic library deps |
| **Debug symbols** | Stripped by `cmake --install --strip` |

## Why Scratch (not Alpine/Distroless)

- `scratch` = empty filesystem → smallest possible image
- No shell means no exec attacks even if process is compromised
- Works only if binary is fully static (all deps linked in)
- C++ with `-static` + Boost static libs satisfies this

## CMake Flags for Static Linking

```cmake
if(ENABLE_STATIC_BUILD)
  set(Boost_USE_STATIC_LIBS ON)
endif()
# ...
target_link_libraries(adserver PRIVATE Boost::system Boost::json Boost::url Threads::Threads)
```

Combined with `-DCMAKE_EXE_LINKER_FLAGS="-static"` this produces a self-contained binary on Alpine (musl libc).

## Build Arg Validation

```dockerfile
ARG APP_VERSION
RUN if [ -z "$APP_VERSION" ]; then \
      echo "ERROR: APP_VERSION is required! Pass it with --build-arg APP_VERSION=..."; \
      exit 1; fi
```

Also validated at CMake level:
```cmake
if(NOT DEFINED APP_VERSION OR APP_VERSION STREQUAL "")
  message(FATAL_ERROR "APP_VERSION is required")
endif()
```

**Double-guard**: Docker and CMake both reject missing version. Version embedded in binary as compile definition.

## Kubernetes Integration

- Image size → faster pod startup
- No shell → `exec` into container not possible (security bonus)
- Non-root UID is compatible with Kubernetes security contexts

## Limitations

- No `curl`/`wget` in container for debugging; use sidecar or ephemeral debug containers
- C++ exceptions that call into libc (e.g., `std::system_error`) still work with musl
- Some Boost components may not fully static-link on non-musl systems; Alpine (musl) is the safest host
