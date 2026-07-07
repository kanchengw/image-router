# image-router

A lightweight HTTP proxy that intercepts chat completion requests, detects images, runs them through a VL (vision-language) model for analysis, replaces the image with the analysis text, and forwards the modified request to the upstream API.

Designed to sit between a chat client (e.g. Codex++) and a text-only LLM backend, enabling vision capabilities without native multimodal support.

## Features

- Intercepts `POST /v1/chat/completions` requests
- Detects `image_url` content blocks in the last user message
- Sends detected images to a VL model (default: Qwen-VL-Plus via Dashscope) for analysis
- Replaces image blocks with the VL analysis text before forwarding
- Logs every forwarded prompt to `_debug/prompts.log`
- Supports streaming responses passthrough

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/kanchengw/image-router.git
cd image-router

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Install dependencies
pip install fastapi uvicorn httpx python-dotenv

# 4. Run
python main.py
```

## Configuration

| Variable       | Default                                                              | Description                  |
|----------------|----------------------------------------------------------------------|------------------------------|
| `CODEX_PLUS_URL` | `https://api.deepseek.com`                                         | Upstream LLM API endpoint    |
| `VL_API_KEY`   | —                                                                    | VL model API key             |
| `VL_MODEL`     | `qwen-vl-plus`                                                       | VL model name                |
| `VL_BASE_URL`  | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | VL API endpoint              |
| `VL_ENABLED`   | `true`                                                               | Enable/disable VL analysis   |
| `PROXY_PORT`   | `23456`                                                              | Proxy listen port            |

## Logs

- `_debug/last_forwarded.json` — last forwarded request payload (overwritten each request)
- `_debug/prompts.log` — append-only log of every forwarded prompt, with VL status and user content
- `proxy.log` — runtime logs
