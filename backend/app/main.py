"""FastAPI application entry point."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .api import tenders, analytics, coverage, suppliers, detailed_tenders, con_tenders, market_analysis, system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Tender Analysis API",
    description="API for analyzing scraped tender data from Georgian procurement portal",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tenders.router)
app.include_router(analytics.router)
app.include_router(detailed_tenders.router)
app.include_router(suppliers.router)
app.include_router(coverage.router)
app.include_router(con_tenders.router)
app.include_router(market_analysis.router)
app.include_router(system.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Tender Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "tenders": "/api/tenders",
            "analytics": "/api/analytics",
            "detailed_tenders": "/api/detailed-tenders",
            "suppliers": "/api/suppliers"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

