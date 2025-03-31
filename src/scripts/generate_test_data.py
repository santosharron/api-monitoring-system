"""
Script to generate test data for API monitoring.
"""
import asyncio
import logging
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict

from src.models.api import ApiMetric, Environment
from src.storage.database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_test_data() -> None:
    """Generate test data for API monitoring."""
    # Ensure MongoDB connection uses the correct URI with database name
    os.environ["MONGODB_URI"] = "mongodb+srv://santosharron:bNqSxhz3MJ9koiD4@cluster0.aufgz7y.mongodb.net/api_monitoring?retryWrites=true&w=majority&appName=Cluster0"
    logger.info(f"Setting MongoDB URI: {os.environ['MONGODB_URI'][:20]}...")
    
    # Set Elasticsearch cloud configuration
    os.environ["ELASTICSEARCH_CLOUD_ID"] = "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg=="
    # Using basic authentication instead of API key
    os.environ["ELASTICSEARCH_USERNAME"] = "elastic"
    os.environ["ELASTICSEARCH_PASSWORD"] = "KIuc03ZYAf6IqGkE1zEap1DR"
    # os.environ["ELASTICSEARCH_API_KEY"] = "ZVQ0SjdKVUJkaDl6bzZEMzRCMkE6ckgxc185OEpRV1dzeEwwUEtwLWNLQQ=="
    os.environ["ELASTICSEARCH_HOSTS"] = ""  # Clear this to force using Cloud ID
    logger.info("Setting Elasticsearch Cloud configuration")
    
    # Get database instance and connect
    db = get_database()
    await db.connect()
    
    # Get API sources
    api_sources = await db.get_api_sources()
    if not api_sources:
        logger.error("No API sources found. Please create API sources first.")
        return
    
    # Generate metrics for the last hour
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    metrics: List[ApiMetric] = []
    current_time = start_time
    
    while current_time <= end_time:
        for api_source in api_sources:
            for endpoint in api_source.endpoints:
                # Generate response time with some randomness
                base_response_time = endpoint.expected_response_time
                response_time = base_response_time + random.uniform(-50, 50)
                
                # Generate success rate (95% success rate)
                success = random.random() > 0.05
                status_code = 200 if success else random.choice([400, 401, 403, 404, 500])
                
                # Create metric
                metric = ApiMetric(
                    id=f"metric-{current_time.timestamp()}",
                    api_id=api_source.id,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    response_time=response_time,
                    status_code=status_code,
                    success=success,
                    error_message=None if success else "Test error message",
                    environment=api_source.environment,
                    timestamp=current_time,
                    error=not success
                )
                
                metrics.append(metric)
        
        current_time += timedelta(minutes=1)
    
    # Store metrics in batches
    batch_size = 100
    for i in range(0, len(metrics), batch_size):
        batch = metrics[i:i + batch_size]
        try:
            await db.store_metrics(batch)
            logger.info(f"Stored {len(batch)} metrics")
        except Exception as e:
            logger.error(f"Failed to store metrics batch: {str(e)}")
            raise

async def main():
    """Main function to generate test data."""
    try:
        await generate_test_data()
        logger.info("Successfully generated test data")
    except Exception as e:
        logger.error(f"Failed to generate test data: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 