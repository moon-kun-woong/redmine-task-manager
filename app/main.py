import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.config import settings
from app.utils import setup_logging, cleanup_old_logs
from app.analyzer import CommitAnalyzer
from app.webhook import WebhookHandler, WebhookQueue

logger = setup_logging(settings.LOG_LEVEL)

analyzer = None
webhook_handler = None
webhook_queue = WebhookQueue()
cleanup_task = None


async def periodic_log_cleanup():
    while True:
        try:
            await asyncio.sleep(86400)
            cleanup_old_logs(days=settings.LOG_RETENTION_DAYS)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic log cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer, webhook_handler, cleanup_task

    logger.info("Starting Redmine Task Manager...")
    logger.info(f"GitLab URL: {settings.GITLAB_URL}")
    logger.info(f"Redmine URL: {settings.REDMINE_URL}")

    cleanup_old_logs(days=settings.LOG_RETENTION_DAYS)

    cleanup_task = asyncio.create_task(periodic_log_cleanup())

    analyzer = CommitAnalyzer()
    webhook_handler = WebhookHandler(analyzer)

    logger.info("Application started successfully")

    yield

    logger.info("Shutting down...")

    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Redmine Task Manager",
    description="GitLab to Redmine sync service with LLM analysis",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Redmine Task Manager",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "gitlab_url": settings.GITLAB_URL,
        "redmine_url": settings.REDMINE_URL,
        "queue_size": webhook_queue.size()
    }


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_token: str = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: str = Header(None, alias="X-Gitlab-Event")
):

    try:
        body = await request.json()

        logger.info(f"Received GitLab webhook: event={x_gitlab_event}")

        if not webhook_handler.verify_token(x_gitlab_token or ""):
            logger.warning("Invalid webhook token")
            raise HTTPException(status_code=401, detail="Invalid token")

        background_tasks.add_task(process_webhook, body, x_gitlab_token)

        return {
            "status": "queued",
            "message": "Webhook received and queued for processing"
        }

    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def process_webhook(payload: dict, gitlab_token: str):
    try:
        result = await webhook_handler.handle_push_event(payload, gitlab_token)
        logger.info(f"Webhook processed: {result.get('status')}")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)


@app.get("/queue/status")
async def queue_status():
    return {
        "queue_size": webhook_queue.size(),
        "is_empty": webhook_queue.is_empty()
    }


@app.post("/test/analyze")
async def test_analyze(commit_data: dict):

    try:
        result = analyzer.process_commit(commit_data)
        return result
    except Exception as e:
        logger.error(f"Error in test analyze: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
