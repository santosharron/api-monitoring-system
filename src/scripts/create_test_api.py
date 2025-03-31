"""
Script to create a test API source for monitoring.
"""
import asyncio
import logging
from datetime import datetime

from src.storage.database import get_database
from src.models.api import ApiSource, Environment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_api():
    """Create a test API source in the database."""
    db = get_database()
    await db.connect()
    
    try:
        # Create test API source
        test_api = ApiSource(
            id="test-api-1",
            name="Test API",
            description="A test API for monitoring",
            base_url="https://api.example.com",
            environment=Environment.AWS,
            endpoints=[
                {
                    "path": "/health",
                    "method": "GET",
                    "expected_response_time": 200,
                    "timeout": 5000
                },
                {
                    "path": "/users",
                    "method": "GET",
                    "expected_response_time": 300,
                    "timeout": 5000
                }
            ],
            headers={
                "User-Agent": "API-Monitoring-System/1.0"
            },
            auth_type="none",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store in database
        await db.store_api_source(test_api)
        logger.info(f"Created test API source: {test_api.name}")
        
    except Exception as e:
        logger.error(f"Error creating test API: {str(e)}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_test_api()) 