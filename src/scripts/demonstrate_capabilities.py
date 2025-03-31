"""
Script to demonstrate the capabilities of the API Monitoring System.
"""
import asyncio
import logging
import aiohttp
import os
from typing import Dict, List
from datetime import datetime, timedelta

from src.models.api import Environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_capabilities() -> None:
    """Demonstrate the capabilities of the API Monitoring System."""
    # Set MongoDB and Elasticsearch environment variables for this script
    os.environ["MONGODB_URI"] = "mongodb+srv://santosharron:bNqSxhz3MJ9koiD4@cluster0.aufgz7y.mongodb.net/api_monitoring?retryWrites=true&w=majority&appName=Cluster0"
    os.environ["ELASTICSEARCH_CLOUD_ID"] = "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg=="
    # Using basic authentication instead of API key
    os.environ["ELASTICSEARCH_USERNAME"] = "elastic"
    os.environ["ELASTICSEARCH_PASSWORD"] = "KIuc03ZYAf6IqGkE1zEap1DR"
    # os.environ["ELASTICSEARCH_API_KEY"] = "ZVQ0SjdKVUJkaDl6bzZEMzRCMkE6ckgxc185OEpRV1dzeEwwUEtwLWNLQQ=="
    os.environ["ELASTICSEARCH_HOSTS"] = ""  # Clear this to force using Cloud ID
    
    async with aiohttp.ClientSession() as session:
        base_url = "http://localhost:8000/api/v1"
        
        # 1. List Monitored APIs
        logger.info("\n=== Listing Monitored APIs ===")
        async with session.get(f"{base_url}/sources") as response:
            apis = await response.json()
            if not apis:
                logger.info("No API sources found")
            else:
                for api in apis:
                    # Handle API source as an object with proper attributes
                    logger.info(f"API: {api.get('name')} ({api.get('environment')})")
                    logger.info(f"Description: {api.get('description')}")
                    
                    # Check if endpoints exists and is a list before trying to get its length
                    endpoints = api.get('endpoints', [])
                    logger.info(f"Endpoints: {len(endpoints)}")
                    logger.info("---")
        
        # 2. Get API Metrics
        logger.info("\n=== Getting API Metrics ===")
        for api in apis:
            # Use .get() to safely access dictionary keys
            api_id = api.get('id')
            if not api_id:
                continue
                
            async with session.get(f"{base_url}/metrics", params={"api_id": api_id}) as response:
                metrics = await response.json()
                if metrics and len(metrics) > 0:
                    latest = metrics[-1]
                    logger.info(f"API: {api.get('name')}")
                    logger.info(f"Total Metrics: {len(metrics)}")
                    logger.info(f"Latest Response Time: {latest.get('response_time')}ms")
                    logger.info(f"Success Rate: {latest.get('success')}")
                    logger.info("---")
                else:
                    logger.info(f"No metrics found for API: {api.get('name')}")
                    logger.info("---")
        
        # 3. Check for Anomalies
        logger.info("\n=== Checking for Anomalies ===")
        async with session.get(f"{base_url}/anomalies") as response:
            anomalies = await response.json()
            if anomalies and len(anomalies) > 0:
                for anomaly in anomalies:
                    logger.info(f"Type: {anomaly.get('type')}")
                    logger.info(f"Severity: {anomaly.get('severity')}")
                    logger.info(f"Description: {anomaly.get('description')}")
                    logger.info("---")
            else:
                logger.info("No anomalies detected")
        
        # 4. Get Predictions
        logger.info("\n=== Getting Predictions ===")
        async with session.get(f"{base_url}/predictions") as response:
            predictions = await response.json()
            if predictions and len(predictions) > 0:
                for pred in predictions:
                    logger.info(f"API: {pred.get('api_id')}")
                    logger.info(f"Predicted Issues: {pred.get('predicted_issues')}")
                    logger.info(f"Confidence: {pred.get('confidence')}")
                    logger.info("---")
            else:
                logger.info("No predictions available")
        
        # 5. Check Alerts
        logger.info("\n=== Checking Alerts ===")
        async with session.get(f"{base_url}/alerts") as response:
            alerts = await response.json()
            if alerts and len(alerts) > 0:
                for alert in alerts:
                    logger.info(f"Severity: {alert.get('severity')}")
                    logger.info(f"Title: {alert.get('title')}")
                    logger.info(f"Description: {alert.get('description')}")
                    logger.info("---")
            else:
                logger.info("No active alerts")
        
        # 6. Cross-Environment Analysis
        logger.info("\n=== Cross-Environment Analysis ===")
        async with session.get(f"{base_url}/dashboard/summary") as response:
            try:
                analysis = await response.json()
                if isinstance(analysis, dict):
                    environments = analysis.get('environments', [])
                    correlated_issues = analysis.get('correlated_issues', [])
                    impact_score = analysis.get('impact_score', 0)
                    
                    logger.info(f"Total Environments: {len(environments)}")
                    logger.info(f"Correlated Issues: {len(correlated_issues)}")
                    logger.info(f"Impact Score: {impact_score}")
                else:
                    logger.info("Cross-environment analysis data not available in expected format")
            except Exception as e:
                logger.error(f"Error processing cross-environment analysis: {str(e)}")
            logger.info("---")
        
        logger.info("\n=== Demonstration Complete ===")
        logger.info("You can now access:")
        logger.info("1. Kibana Dashboard: http://localhost:5601")
        logger.info("2. API Documentation: http://localhost:8000/docs")
        logger.info("3. Real-time Monitoring: http://localhost:8000/api/v1/metrics")

async def main():
    """Main function to run the demonstration."""
    try:
        await demonstrate_capabilities()
    except Exception as e:
        logger.error(f"Failed to demonstrate capabilities: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 