from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import captcha, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="ZXtextAI PyTools Service",
        version="1.0.0",
        description="Python 工具能力服务，提供 OCR、验证码检测和自动化辅助能力。",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(captcha.router, prefix="/captcha", tags=["captcha"])
    return app
