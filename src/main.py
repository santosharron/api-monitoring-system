"""
Main application entry point for API Monitoring System.
"""
import asyncio
import logging
import sys
import signal
import os
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from src.api.routes import router as api_router
from src.storage.database import get_database
from src.collection.collector_manager import CollectorManager
from src.analyzers.analyzer_manager import AnalyzerManager
from src.alerting.alert_manager import AlertManager
from src.visualization.dashboard_initializer import DashboardInitializer

# Create settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="API Monitoring System",
    description="AI-powered API monitoring and anomaly detection system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Application components
collector_manager = None
analyzer_manager = None
alert_manager = None
dashboard_initializer = None

# Flag to control Kibana dashboard initialization
SKIP_KIBANA_INIT = os.getenv("SKIP_KIBANA_INIT", "False").lower() in ("true", "1", "t")

@app.on_event("startup")
async def startup_event():
    """
    Initialize application components on startup.
    """
    global collector_manager, analyzer_manager, alert_manager, dashboard_initializer
    
    try:
        logger.info("Starting API Monitoring System")
        
        # Initialize database connection
        db = get_database()
        await db.connect()
        
        # Update existing metrics with missing IDs
        try:
            updated_count = await db.update_api_metrics_with_missing_id()
            if updated_count > 0:
                logger.info(f"Updated {updated_count} API metrics with missing ID field")
        except Exception as e:
            logger.error(f"Error updating API metrics with missing IDs: {str(e)}")
        
        # Initialize components
        collector_manager = CollectorManager()
        analyzer_manager = AnalyzerManager()
        alert_manager = AlertManager()
        
        # Start components with error handling
        try:
            await collector_manager.start_collection()
        except Exception as e:
            logger.error(f"Error starting collector manager: {str(e)}")
            
        try:
            await analyzer_manager.start_analysis()
        except Exception as e:
            logger.error(f"Error starting analyzer manager: {str(e)}")
            
        try:
            await alert_manager.start_alerting()
        except Exception as e:
            logger.error(f"Error starting alert manager: {str(e)}")
        
        # Initialize Kibana dashboards (only if not skipped)
        if not SKIP_KIBANA_INIT:
            dashboard_initializer = DashboardInitializer()
            try:
                # Run Kibana initialization in a separate task to not block startup
                asyncio.create_task(initialize_kibana_dashboards())
            except Exception as e:
                logger.error(f"Error initializing Kibana dashboards: {str(e)}")
        else:
            logger.info("Skipping Kibana dashboard initialization")
        
        logger.info("API Monitoring System started successfully")
        
        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda signum, frame: asyncio.create_task(shutdown()))
    
    except Exception as e:
        logger.error(f"Error starting API Monitoring System: {str(e)}")
        # Log the error but allow the application to start
        # This enables the API to work even if some components aren't fully functional

async def initialize_kibana_dashboards():
    """
    Initialize Kibana dashboards asynchronously.
    """
    global dashboard_initializer
    
    try:
        if dashboard_initializer:
            logger.info("Initializing Kibana dashboards in background task...")
            await dashboard_initializer.initialize_dashboards()
            logger.info("Kibana dashboards initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Kibana dashboards: {str(e)}")
        # Don't let dashboard init failures affect main app

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup application components on shutdown.
    """
    await shutdown()

async def shutdown():
    """
    Gracefully shutdown application components.
    """
    logger.info("Shutting down API Monitoring System")
    
    # Stop components in reverse order
    if alert_manager:
        try:
            await alert_manager.stop_alerting()
        except Exception as e:
            logger.error(f"Error stopping alert manager: {str(e)}")
    
    if analyzer_manager:
        try:
            await analyzer_manager.stop_analysis()
        except Exception as e:
            logger.error(f"Error stopping analyzer manager: {str(e)}")
    
    if collector_manager:
        try:
            await collector_manager.stop_collection()
        except Exception as e:
            logger.error(f"Error stopping collector manager: {str(e)}")
    
    # Close database connection
    try:
        db = get_database()
        await db.disconnect()
    except Exception as e:
        logger.error(f"Error disconnecting from database: {str(e)}")
    
    logger.info("API Monitoring System shutdown complete")

@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "message": "API Monitoring System",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    db = get_database()
    
    return {
        "status": "ok",
        "components": {
            "collector_manager": "running" if collector_manager and collector_manager.running else "stopped",
            "analyzer_manager": "running" if analyzer_manager and analyzer_manager.running else "stopped",
            "alert_manager": "running" if alert_manager and alert_manager.running else "stopped",
            "kibana_dashboards": "initialized" if dashboard_initializer else "not_initialized",
            "database": {
                "initialized": db.initialized,
                "elasticsearch": "available" if db.es_available else "unavailable",
                "mongodb": "available" if db.mongo_available else "unavailable"
            }
        }
    }

@app.get("/dashboards")
async def get_dashboards():
    """
    Get available dashboards.
    """
    if not dashboard_initializer:
        return {"error": "Dashboard initializer not available"}
    
    return {
        "dashboards": [
            {
                "id": "api-overview-dashboard",
                "name": "API Overview",
                "url": dashboard_initializer.get_dashboard_url("api-overview-dashboard")
            },
            {
                "id": "anomaly-detection-dashboard",
                "name": "Anomaly Detection",
                "url": dashboard_initializer.get_dashboard_url("anomaly-detection-dashboard")
            },
            {
                "id": "cross-environment-dashboard",
                "name": "Cross-Environment Analysis",
                "url": dashboard_initializer.get_dashboard_url("cross-environment-dashboard")
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 