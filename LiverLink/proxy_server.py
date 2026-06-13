"""
LiverLink — Proxy Server
Serves upload.html and proxies /apps/* and /run to the ADK server.
Everything on one origin → no CORS issues.
"""

import httpx
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ADK_BASE = "http://127.0.0.1:8000"
APP_NAME = "liverlink_pipeline"
HERE = Path(__file__).parent

app = FastAPI(max_request_body_size=20 * 1024 * 1024)  # 20 MB

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def index():
    return (HERE / "upload.html").read_text()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{ADK_BASE}/{path}"
    body = await request.body()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            content=body,
            # Strip origin/referer so ADK's origin-check middleware lets it through
            headers={k: v for k, v in request.headers.items()
                     if k.lower() not in ("host", "origin", "referer")},
            params=dict(request.query_params),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info",
                http="h11", limit_max_requests=None,
                timeout_keep_alive=120)
