# image-router

**image-router** is developed to solve a critical issue in [CodexPlusPlus](https://github.com/BigPizzaV3/CodexPlusPlus): when CodexPlusPlus is connected to a **text-only LLM backend** (e.g. DeepSeek V4 series), sending an image in chat causes the session to become **permanently unusable** -- the model cannot process the image data and the conversation breaks irrecoverably.

image-router sits as a lightweight HTTP proxy between Codex++ and the text-only backend. It intercepts chat completion requests, detects attached images, performs **vision analysis** via a dedicated VL API (Dashscope Qwen-VL-Plus), then replaces the original image blocks with the analysis result before forwarding the cleaned request upstream.

Vision analysis includes **text extraction** (OCR) and **visual description** of the image content.

## How it works

```
User sends image --> Codex++ --> image-router (:23456) --> Text-only LLM
                                   |
                                   |-- Detects image_url
                                   |-- Calls vision analysis API (Dashscope Qwen-VL-Plus)
                                   |-- Replaces image with analysis text
                                   |-- Forwards clean prompt to upstream
```

## Prompt Structures

### 1. Vision analysis prompt (sent to VL API)

The proxy constructs a prompt asking the VL model to extract all visible text and describe the image:

```
Extract ALL visible text precisely, then describe. Output:
[IMAGE ANALYSIS]
Text content: <extracted text or "none">
Visual description: <description>
```

### 2. Vision analysis output (returned by VL API)

The VL model returns a structured response which is then injected into the user message:

```
[IMAGE ANALYSIS]
Text content: Google Chrome
               WeGame
               Git Bash
               ...
Visual description: A screenshot of a Windows desktop showing application icons on the taskbar and desktop, including Chrome, WeGame, Git Bash, and system tray icons.
```

### 3. Final prompt (sent to the upstream model)

After injection, the upstream model receives the user message with images replaced by the analysis text. For example, a user message that originally contained text + image becomes:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What is the status of this server?"},
    {"type": "text", "text": "[IMAGE ANALYSIS]\nText content: CPU: 45%, Memory: 8.2/16GB\nVisual description: A screenshot of a Linux server monitoring dashboard showing CPU usage of 45% and memory usage of 8.2GB out of 16GB."}
  ]
}
```

Note: the original `image_url` block is removed entirely. Only the text description remains, ensuring the text-only model can process the message without issues.

## Features

- Intercepts `POST /v1/chat/completions` requests
- Detects `image_url` content blocks in the last user message
- Performs vision analysis (text extraction + image description) via a dedicated VL API
- Replaces image blocks with the analysis text before forwarding
- Logs every forwarded prompt to `_debug/prompts.log`
- Supports streaming responses passthrough

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/kanchengw/image-router.git
cd image-router

# 2. Configure VL model API keys
cp .env.example .env
# Edit .env: set VL_API_KEY, VL_MODEL, VL_BASE_URL for your vision analysis provider

# 3. Install dependencies
pip install fastapi uvicorn httpx python-dotenv

# 4. Run the proxy
python main.py

# 5. Configure Codex++ Manager: set supplier Base URL to http://127.0.0.1:23456
#    Then restart Codex++
# 6. Start a session in Codex++ and send an image message
```

## Configuration

| Variable       | Default                                                              | Description                  |
|----------------|----------------------------------------------------------------------|------------------------------|
| `CODEX_PLUS_URL` | `https://api.deepseek.com`                                         | Upstream LLM API endpoint    |
| `VL_API_KEY`   | --                                                                   | Vision analysis API key      |
| `VL_MODEL`     | `qwen-vl-plus`                                                       | Vision analysis model name   |
| `VL_BASE_URL`  | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | Vision analysis API endpoint |
| `VL_ENABLED`   | `true`                                                               | Enable/disable vision analysis |
| `PROXY_PORT`   | `23456`                                                              | Proxy listen port            |










