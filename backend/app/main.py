import argparse
import os
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.core.config import (
    DEFAULT_ENV_FILE_NAME,
    ensure_runtime_dirs,
    load_env_file,
    resolve_log_path,
    setup_file_logger,
    get_settings,
)
from backend.app.core.model_factory import init_agent_llm
from backend.app.services.vector_memory import init_vector_memory
from backend.tools.registry import init_core_tools


def create_app(
    env_dir: str | None = None,
    env_file_name: str = DEFAULT_ENV_FILE_NAME,
    cli_log_path: str | None = None,
) -> FastAPI:
    effective_env_dir = env_dir or os.getenv("ACE_CLAW_ENV_DIR")
    loaded_env = load_env_file(env_dir=effective_env_dir, env_file_name=env_file_name)
    get_settings.cache_clear()
    ensure_runtime_dirs()
    logger = setup_file_logger(resolve_log_path(cli_log_path))

    from backend.app.api.routes.chat import router as chat_router
    from backend.app.api.routes.health import router as health_router
    from backend.app.api.routes.memories import router as memories_router
    from backend.app.api.routes.sessions import router as sessions_router
    from backend.app.api.routes.skills import router as skills_router, skill_manager
    from backend.app.api.routes.usage import router as usage_router

    app = FastAPI(title="AceClaw Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(memories_router)
    app.include_router(sessions_router)
    app.include_router(skills_router)
    app.include_router(usage_router)

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        start = perf_counter()
        response = await call_next(request)
        cost_ms = (perf_counter() - start) * 1000
        client = request.client.host if request.client else "-"
        logger.info(
            "request method=%s path=%s status=%s client=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            client,
            cost_ms,
        )
        return response

    @app.on_event("startup")
    async def on_startup() -> None:
        settings = get_settings()
        init_agent_llm(settings)
        init_vector_memory(settings)
        init_core_tools(settings)
        skill_manager.reload()
        logger.info("startup env=%s log=%s", str(loaded_env) if loaded_env else "none", resolve_log_path(cli_log_path))

    return app


app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AceClaw FastAPI service with Uvicorn.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--env-dir", default=None, help="Directory that must contain .env")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE_NAME, help="Env filename, default is .env")
    parser.add_argument("--log-path", default=None, help="Log file path, overrides env setting")
    args = parser.parse_args()

    uvicorn.run(
        create_app(env_dir=args.env_dir, env_file_name=args.env_file, cli_log_path=args.log_path),
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
