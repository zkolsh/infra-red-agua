from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Diseño de Infraestructura de Red")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors.allow_origins, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(v1_router)


async def _not_connected(_: Request):
    return JSONResponse(status_code=422, content={"detail": "Network is not connected"})
