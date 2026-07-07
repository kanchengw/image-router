# image-router

**image-router** is developed to solve a critical issue in [CodexPlusPlus](https://github.com/BigPizzaV3/CodexPlusPlus): when CodexPlusPlus is connected to a **text-only LLM backend** (e.g. DeepSeek V4 series), sending an image in chat causes the session to become **permanently unusable** -- the model cannot process the image data and the conversation breaks irrecoverably.

image-router sits as a lightweight HTTP proxy between Codex++ and the text-only backend. It intercepts chat completion requests, detects attached images, runs them through a VL (vision-language) model for text analysis, replaces the image blocks with the analysis result, and forwards the cleaned request to the upstream API.

## How it works

```
User sends image --> Codex++ --> image-router (:23456) --> Text-only LLM
                                   |
                                   |-- Detects image_url
                                   |-- Sends to VL model (Dashscope Qwen-VL-Plus)
                                   |-- Replaces image with analysis text
                                   |-- Forwards clean prompt to upstream
```

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

# 4. Run the proxy
python main.py

# 5. Launch Codex++, go to any session, and send an image message
```

## Configuration

| Variable       | Default                                                              | Description                  |
|----------------|----------------------------------------------------------------------|------------------------------|
| `CODEX_PLUS_URL` | `https://api.deepseek.com`                                         | Upstream LLM API endpoint    |
| `VL_API_KEY`   | --                                                                   | VL model API key             |
| `VL_MODEL`     | `qwen-vl-plus`                                                       | VL model name                |
| `VL_BASE_URL`  | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | VL API endpoint              |
| `VL_ENABLED`   | `true`                                                               | Enable/disable VL analysis   |
| `PROXY_PORT`   | `23456`                                                              | Proxy listen port            |

## Logs

- `_debug/last_forwarded.json` - last forwarded request payload (overwritten each request)
- `_debug/prompts.log` - append-only log of every forwarded prompt, with VL status and user content
- `proxy.log` - runtime logs
