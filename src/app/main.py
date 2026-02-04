"""Main FastAPI application entry point."""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="MCP Article Summarizer",
        description="Agent IA qui consulte des serveurs MCP pour générer un résumé et une liste des articles les plus intéressants",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router, prefix="/api")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "MCP Article Summarizer API",
            "version": "0.1.0",
            "endpoints": {
                "articles": "/api/articles",
                "news": "/api/news",
                "health": "/api/health",
            },
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
