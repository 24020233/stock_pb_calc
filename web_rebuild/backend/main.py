#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.articles import router as articles_router
from config import get_settings
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up...")
    logger.info(f"Database: {get_settings().mysql_database}@{get_settings().mysql_host}")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await Database.close_pool()
    logger.info("Database pool closed.")


# Create FastAPI app
app = FastAPI(
    title="WeChat MP Crawler API",
    description="API for crawling WeChat MP articles using Dajiala API",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(articles_router)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "WeChat MP Crawler API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
