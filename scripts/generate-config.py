#!/usr/bin/env python3
"""Generate opencode.json with $HOME-expanded paths.

The semantic_search MCP server config contains absolute paths that vary
per user. This script generates a valid opencode.json with the current
user's home directory substituted.

Usage:
    python3 generate-config.py                  # write to default location
    python3 generate-config.py --dry-run        # preview without writing
    python3 generate-config.py -o /tmp/test.json  # custom output path
"""

import argparse
import json
import sys
from pathlib import Path

# Template with {home} placeholders for user-specific paths.
# Replace {home} with the current user's home directory at runtime.
# Only two paths need expansion:
#   - semantic_search command --directory
#   - semantic_search environment CODE_SEARCH_STORAGE
TEMPLATE = r"""{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "opencode": {
      "name": "OpenCode",
      "models": {
        "qwen-3.6-plus": {
          "name": "Qwen 3.6 Plus",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "glm-5.1": {
          "name": "GLM 5.1",
          "limit": {
            "context": 202000,
            "output": 32768
          }
        },
        "glm-5": {
          "name": "GLM 5",
          "limit": {
            "context": 202000,
            "output": 32768
          }
        },
        "minimax-m2.7": {
          "name": "MiniMax M2.7",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "minimax-m2.5-free": {
          "name": "MiniMax M2.5 Free",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "claude-opus-4-6": {
          "name": "Claude Opus 4.6",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "claude-opus-4-5": {
          "name": "Claude Opus 4.5",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "claude-sonnet-4-6": {
          "name": "Claude Sonnet 4.6",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "claude-sonnet-4-5": {
          "name": "Claude Sonnet 4.5",
          "limit": {
            "context": 200000,
            "output": 16384
          }
        },
        "gpt-5.4": {
          "name": "GPT 5.4",
          "limit": {
            "context": 272000,
            "output": 128000
          }
        },
        "gpt-5.4-mini": {
          "name": "GPT 5.4 Mini",
          "limit": {
            "context": 272000,
            "output": 32768
          }
        },
        "gpt-5.3-codex-spark": {
          "name": "GPT 5.3 Codex Spark",
          "limit": {
            "context": 272000,
            "output": 32768
          }
        },
        "gpt-5.2-codex": {
          "name": "GPT 5.2 Codex",
          "limit": {
            "context": 272000,
            "output": 32768
          }
        },
        "gemini-3.1-pro": {
          "name": "Gemini 3.1 Pro",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "gemini-3.1-flash": {
          "name": "Gemini 3.1 Flash",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "gemini-3-flash": {
          "name": "Gemini 3 Flash",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "grok-4.20": {
          "name": "Grok 4.20",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "doubao-2.0": {
          "name": "Doubao 2.0",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "qwen-3.5-omni": {
          "name": "Qwen 3.5 Omni",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "mistral-large-3": {
          "name": "Mistral Large 3",
          "limit": {
            "context": 256000,
            "output": 16384
          }
        },
        "kimi-k2.5": {
          "name": "Kimi K2.5",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        },
        "nemotron-3-super-free": {
          "name": "Nemotron 3 Super Free",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        }
      }
    },
    "deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "DeepSeek API",
      "options": {
        "baseURL": "https://api.deepseek.com",
        "compatibility": "flexible",
        "includeUsage": true
      },
      "models": {
        "deepseek-v3.2": {
          "name": "DeepSeek V3.2",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        },
        "deepseek-v4": {
          "name": "DeepSeek V4",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "deepseek-chat": {
          "name": "DeepSeek Chat",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        },
        "deepseek-reasoner": {
          "name": "DeepSeek Reasoner",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        }
      }
    },
    "anthropic": {
      "options": {
        "baseURL": "https://api.anthropic.com/v1"
      }
    },
    "openai": {
      "options": {
        "baseURL": "https://api.openai.com/v1"
      }
    },
    "openrouter": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenRouter",
      "options": {
        "baseURL": "https://openrouter.ai/api/v1",
        "compatibility": "compatible",
        "includeUsage": true
      },
      "models": {
        "z-ai/glm-5.1": {
          "name": "GLM 5.1 (via OpenRouter)",
          "limit": {
            "context": 202000,
            "output": 32768
          }
        },
        "minimax/minimax-m2.7": {
          "name": "MiniMax M2.7 (via OpenRouter)",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "moonshotai/kimi-k2.5": {
          "name": "Kimi K2.5 (via OpenRouter)",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        },
        "anthropic/claude-opus-4.6": {
          "name": "Claude Opus 4.6 (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "anthropic/claude-sonnet-4.6": {
          "name": "Claude Sonnet 4.6 (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "anthropic/claude-sonnet-4": {
          "name": "Claude Sonnet 4 (via OpenRouter)",
          "limit": {
            "context": 200000,
            "output": 16384
          }
        },
        "openai/gpt-5.4": {
          "name": "GPT 5.4 (via OpenRouter)",
          "limit": {
            "context": 272000,
            "output": 128000
          }
        },
        "google/gemini-3.1-pro-preview": {
          "name": "Gemini 3.1 Pro Preview (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "google/gemini-3.1-flash-lite-preview": {
          "name": "Gemini 3.1 Flash Lite Preview (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "deepseek/deepseek-v3.2": {
          "name": "DeepSeek V3.2 (via OpenRouter)",
          "limit": {
            "context": 128000,
            "output": 32768
          }
        },
        "x-ai/grok-4.20": {
          "name": "Grok 4.20 (via OpenRouter)",
          "limit": {
            "context": 128000,
            "output": 16384
          }
        },
        "mistral/mistral-large-3": {
          "name": "Mistral Large 3 (via OpenRouter)",
          "limit": {
            "context": 256000,
            "output": 16384
          }
        },
        "qwen/qwen3.6-plus": {
          "name": "Qwen 3.6 Plus (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "qwen/qwen3-coder:free": {
          "name": "Qwen3 Coder Free (via OpenRouter)",
          "limit": {
            "context": 40000,
            "output": 16384
          }
        },
        "nvidia/nemotron-3-super-120b-a12b:free": {
          "name": "Nemotron 3 Super Free (via OpenRouter)",
          "limit": {
            "context": 32000,
            "output": 16384
          }
        },
        "google/gemini-3-flash-preview": {
          "name": "Gemini 3 Flash Preview (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "google/gemini-3-pro-preview": {
          "name": "Gemini 3 Pro Preview (via OpenRouter)",
          "limit": {
            "context": 1000000,
            "output": 32768
          }
        },
        "qwen/qwen3-coder": {
          "name": "Qwen3 Coder (via OpenRouter)",
          "limit": {
            "context": 131072,
            "output": 32768
          }
        }
      }
    }
  },
  "plugin": [
    "oh-my-opencode-slim"
  ],
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "enabled": true
    },
    "grep_app": {
      "type": "remote",
      "url": "https://mcp.grep.app",
      "enabled": true
    },
    "semantic_search": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--directory",
        "{home}/.local/share/opencode-context-local",
        "python",
        "-m",
        "mcp_server.server"
      ],
      "environment": {
        "CODE_SEARCH_STORAGE": "{home}/.opencode_memory",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
      },
      "enabled": true
    }
  },
  "agent": {
    "explore": {
      "disable": false
    },
    "general": {
      "disable": false
    }
  },
  "lsp": {
    "clangd": {
      "command": [
        "clangd",
        "--background-index",
        "--clang-tidy"
      ],
      "extensions": [
        "c",
        "cpp",
        "h",
        "hpp",
        "cc",
        "cxx"
      ]
    },
    "typescript-language-server": {
      "command": [
        "typescript-language-server",
        "--stdio"
      ],
      "languages": [
        "typescript",
        "typescriptreact",
        "javascript",
        "javascriptreact"
      ],
      "extensions": [
        "ts",
        "tsx",
        "js",
        "jsx"
      ]
    },
    "pyright": {
      "command": [
        "pyright-langserver",
        "--stdio"
      ],
      "languages": [
        "python"
      ],
      "extensions": [
        "py",
        "pyi"
      ],
      "settings": {
        "python": {
          "analysis": {
            "autoSearchPaths": true,
            "useLibraryCodeForTypes": true,
            "diagnosticMode": "openFilesOnly",
            "typeCheckingMode": "standard"
          }
        }
      }
    },
    "rust-analyzer": {
      "command": [
        "rust-analyzer"
      ],
      "languages": [
        "rust"
      ],
      "extensions": [
        "rs"
      ],
      "settings": {
        "rust-analyzer": {
          "checkOnSave": {
            "command": "clippy"
          },
          "cargo": {
            "allFeatures": true
          },
          "procMacro": {
            "enable": true
          }
        }
      }
    },
    "gopls": {
      "command": [
        "gopls",
        "serve"
      ],
      "languages": [
        "go",
        "gomod"
      ],
      "extensions": [
        "go",
        "mod"
      ],
      "settings": {
        "gopls": {
          "staticcheck": true,
          "gofumpt": true,
          "analyses": {
            "unusedparams": true,
            "shadow": true
          }
        }
      }
    },
    "kotlin-language-server": {
      "command": [
        "kotlin-language-server-wrapper"
      ],
      "languages": [
        "kotlin"
      ],
      "extensions": [
        "kt",
        "kts"
      ],
      "settings": {
        "kotlin": {
          "compiler": {
            "jvm": {
              "target": "17"
            }
          },
          "indexing": {
            "enabled": true
          },
          "completion": {
            "snippets": {
              "enabled": true
            }
          },
          "diagnostics": {
            "enabled": true
          }
        }
      }
    }
  },
  "permission": "allow"
}"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate opencode.json with $HOME-expanded paths"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.home() / ".config/opencode/opencode.json",
        help="Output path (default: ~/.config/opencode/opencode.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing file",
    )
    args = parser.parse_args()

    # Replace {home} placeholder with the current user's home directory
    config_text = TEMPLATE.replace("{home}", str(Path.home()))

    # Validate generated JSON before writing
    try:
        json.loads(config_text)
    except json.JSONDecodeError as e:
        print(f"Error: generated invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(config_text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(config_text)
        print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
