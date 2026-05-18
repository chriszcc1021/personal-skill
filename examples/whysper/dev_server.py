from __future__ import annotations

import os
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

os.environ.setdefault("WHYSPER_DATA", str(BASE_DIR / ".data"))

from backend import server as backend_server  # noqa: E402

app = FastAPI(title="Whysper Dev Gateway")
app.mount("/whysper", StaticFiles(directory=FRONTEND_DIR, html=True), name="whysper")


@app.get("/")
async def root():
    return RedirectResponse("/whysper/")


def _copy_headers(headers: httpx.Headers) -> dict[str, str]:
    allowed = {"content-type", "content-disposition", "cache-control", "etag"}
    return {k: v for k, v in headers.items() if k.lower() in allowed}


async def _proxy_to_backend(request: Request, target_path: str) -> Response:
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    transport = httpx.ASGITransport(app=backend_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://whysper.local") as client:
        upstream = await client.request(
            request.method,
            target_path,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_copy_headers(upstream.headers),
    )


@app.api_route(
    "/whysper-api/{path:path}",
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
)
async def whysper_api(path: str, request: Request):
    return await _proxy_to_backend(request, f"/api/{path}")


@app.api_route(
    "/whysper-media/{path:path}",
    methods=["GET", "HEAD", "OPTIONS"],
)
async def whysper_media(path: str, request: Request):
    return await _proxy_to_backend(request, f"/media/{path}")


if __name__ == "__main__":
    port = int(os.environ.get("WHYSPER_DEV_PORT", "18084"))
    uvicorn.run("dev_server:app", host="127.0.0.1", port=port, reload=True)
