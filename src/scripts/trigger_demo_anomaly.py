"""
Script to trigger demo anomalies for the API Monitoring System.
This demonstrates how to properly trigger anomalies for the hackathon presentation.
"""
import asyncio
import logging
import aiohttp
import os
import json
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def trigger_anomaly(anomaly_type: str, environment: str = None, environments: list = None, 
                         severity: str = "medium", duration_minutes: int = 5):
    """Trigger a demo anomaly."""
    
    # Prepare request payload
    payload = {
        "type": anomaly_type,
        "severity": severity,
        "duration_minutes": duration_minutes
    }
    
    # Add environment or environments based on which is provided
    if environment:
        payload["environment"] = environment
    if environments:
        payload["environments"] = environments
    
    # Convert payload to JSON string
    payload_json = json.dumps(payload)
    
    logger.info(f"Triggering anomaly with payload: {payload_json}")
    
    async with aiohttp.ClientSession() as session:
        url = "http://localhost:8000/api/v1/demo/trigger-anomaly"
        headers = {"Content-Type": "application/json"}
        
        try:
            async with session.post(url, data=payload_json, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response body: {response_text}")
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully triggered anomaly: {result}")
                    return result
                else:
                    logger.error(f"Failed to trigger anomaly: HTTP {response.status}")
                    logger.error(f"Error details: {response_text}")
                    return None
        except Exception as e:
            logger.error(f"Exception during request: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

async def main():
    """Main function to trigger anomalies."""
    parser = argparse.ArgumentParser(description="Trigger demo anomalies for API Monitoring System")
    parser.add_argument("--type", choices=["response_time", "error_rate", "cross_environment"], 
                        required=True, help="Type of anomaly to trigger")
    parser.add_argument("--env", help="Environment for single-environment anomalies")
    parser.add_argument("--envs", nargs="+", help="Environments for cross-environment anomalies")
    parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], 
                        default="medium", help="Severity of the anomaly")
    parser.add_argument("--duration", type=int, default=5, help="Duration in minutes")
    
    args = parser.parse_args()
    
    # For cross-environment type, ensure environments are provided
    if args.type == "cross_environment" and not args.envs:
        logger.error("For cross_environment anomalies, --envs argument is required")
        return
    
    # For other types, ensure environment is provided
    if args.type != "cross_environment" and not args.env:
        logger.error(f"For {args.type} anomalies, --env argument is required")
        return
    
    try:
        await trigger_anomaly(
            anomaly_type=args.type,
            environment=args.env,
            environments=args.envs,
            severity=args.severity,
            duration_minutes=args.duration
        )
    except Exception as e:
        logger.error(f"Failed to trigger anomaly: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 