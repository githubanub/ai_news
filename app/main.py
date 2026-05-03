from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.routes_articles import router as articles_router
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_slack import router as slack_router
from app.api.routes_webflow import router as webflow_router
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic AI News System", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
    app.include_router(slack_router, prefix="/webhooks/slack", tags=["slack"])
    app.include_router(webflow_router, prefix="/webflow", tags=["webflow"])
    app.include_router(articles_router, prefix="/articles", tags=["articles"])
    return app


app = create_app()
