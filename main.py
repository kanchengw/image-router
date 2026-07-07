import json
import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="image-router")

load_dotenv()

CODEX_PLUS_URL = os.environ.get("CODEX_PLUS_URL", "https://api.deepseek.com")
VL_API_KEY = os.environ.get("VL_API_KEY", "")
VL_MODEL = os.environ.get("VL_MODEL", "qwen-vl-plus")
VL_BASE_URL = os.environ.get("VL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
VL_ENABLED = os.environ.get("VL_ENABLED", "true").lower() == "true"

_http = httpx.AsyncClient(
    timeout=httpx.Timeout(120.0, connect=10.0),
    limits=httpx.Limits(max_keepalive_connections=0, max_connections=50),
)

_SKIP_TYPES = {"image_url", "input_image", "image_file", "input_file", "file"}

def _vl_headers():
    return {
        "Authorization": f"Bearer {VL_API_KEY}",
        "Content-Type": "application/json",
    }

async def analyze_image(image_url: str) -> str | None:
    if not VL_API_KEY:
        return None
    try:
        parts = []
        if image_url:
            parts.append({"type": "image_url", "image_url": {"url": image_url}})
        parts.append({"type": "text", "text": "Extract ALL visible text precisely, then describe. Output:\n[IMAGE ANALYSIS]\nText content: <text or none>\nVisual description: <description>"})
        vl = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        r = await vl.post(VL_BASE_URL, json={
            "model": VL_MODEL,
            "messages": [{"role": "user", "content": parts}],
            "stream": False
        }, headers=_vl_headers())
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        print(f"[image-router] vision analysis API returned {r.status_code}")
    except Exception as e:
        print(f"[image-router] vision analysis error: {e}")
    return None

def _img_too_large(url: str, mb: int = 4) -> bool:
    if url.startswith("data:image"):
        try:
            b64 = url.split(",", 1)[1]
            return (len(b64) * 3 / 4) / (1024 * 1024) > mb
        except:
            return False
    return False

@app.api_route("/{path:path}", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
async def proxy(path: str, req: Request):
    target = f"{CODEX_PLUS_URL.rstrip('/')}/{path}"
    body = await req.body()
    analysis = None
    img_idx = None

    if req.method == "POST" and body:
        try:
            j = json.loads(body)
            if VL_ENABLED and VL_API_KEY:
                img_url = None
                for key in ("messages", "input"):
                    msgs = j.get(key)
                    if isinstance(msgs, list):
                        if not msgs:
                            continue
                        last = msgs[-1]
                        c = last.get("content") if isinstance(last, dict) else None
                        if isinstance(c, list):
                            for block in c:
                                t = block.get("type", "")
                                if t in _SKIP_TYPES:
                                    src = block.get("image_url") or block.get(t) or {}
                                    url = src.get("url", "") if isinstance(src, dict) else str(src)
                                    if url:
                                        img_url, img_idx = url, len(msgs) - 1
                                        break
                    if img_url:
                        break
                if img_url:
                    if _img_too_large(img_url):
                        analysis = "[IMAGE ANALYSIS]\nText content: (image too large)\nVisual description: (image too large)"
                        print(f"[image-router] image too large, skipped")
                    else:
                        r = await analyze_image(img_url)
                        if r:
                            analysis = r
                            print(f"[image-router] vision analysis OK ({len(r)} chars)")
                        else:
                            analysis = "[IMAGE ANALYSIS]\nText content: (recognition failed)\nVisual description: (recognition failed)"
                            print(f"[image-router] vision analysis FAILED")

            for key in ("messages", "input"):
                msgs = j.get(key)
                if isinstance(msgs, list):
                    for idx, msg in enumerate(msgs):
                        c = msg.get("content")
                        if isinstance(c, list):
                            inject = analysis if idx == img_idx else None
                            msg["content"] = [b for b in c if b.get("type", "") not in _SKIP_TYPES]
                            if inject:
                                msg["content"].append({"type": "text", "text": inject})
                            if not msg["content"]:
                                msg["content"] = [{"type": "text", "text": inject or "(image removed)"}]
                        msg.pop("image", None)
                        msg.pop("image_url", None)
            body = json.dumps(j).encode()
        except Exception:
            pass

    hdrs = {}
    for k in ("authorization", "content-type", "user-agent"):
        v = req.headers.get(k, "")
        if v:
            hdrs[k] = v

    try:
        r = await _http.request(method=req.method, url=target, content=body, headers=hdrs, params=dict(req.query_params))
        if r.status_code >= 400:
            return JSONResponse({"id":"err","object":"chat.completion","created":int(__import__("time").time()),"model":"unknown","choices":[{"index":0,"message":{"role":"assistant","content":f"[upstream {r.status_code}]"},"finish_reason":"stop"}]}, status_code=200)
        ct = r.headers.get("content-type", "")
        if "text/event-stream" in ct:
            return StreamingResponse(r.aiter_bytes(), status_code=200, media_type=ct)
        data = r.json() if r.text else {}
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        return JSONResponse({"id":"err","object":"chat.completion","created":int(__import__("time").time()),"model":"unknown","choices":[{"index":0,"message":{"role":"assistant","content":f"[proxy error: {type(e).__name__}]"},"finish_reason":"stop"}]}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PROXY_PORT", "23456"))
    status = "ON" if VL_ENABLED and VL_API_KEY else "OFF"
    print(f"[image-router] running on :{port} -> {CODEX_PLUS_URL} (vision analysis={status})")
    uvicorn.run("main:app", host="127.0.0.1", port=port, log_level="info")
