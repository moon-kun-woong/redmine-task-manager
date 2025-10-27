import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("Redmine Task Manager")
    print("=" * 60)
    print(f"GitLab URL: {settings.GITLAB_URL}")
    print(f"Redmine URL: {settings.REDMINE_URL}")
    print(f"Server: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
