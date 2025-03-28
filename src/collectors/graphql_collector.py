"""
GraphQL API collector for API monitoring system.
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp

from config.settings import settings
from src.models.api import ApiSource, ApiMetrics, Environment

logger = logging.getLogger(__name__)

class GraphQLCollector:
    """
    Collector for GraphQL API metrics.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the GraphQL collector.
        
        Args:
            api_source: The API source to collect metrics for.
        """
        self.api_source = api_source
        self.headers = self._prepare_headers(api_source)
        self.last_collection = None
        self.metrics_count = 0
        self._running = False
    
    async def initialize(self):
        """
        Initialize the collector.
        """
        self._running = True
        self.last_collection = None
        self.metrics_count = 0
    
    async def stop(self):
        """
        Stop the collector.
        """
        self._running = False
    
    def is_running(self) -> bool:
        """
        Check if the collector is running.
        
        Returns:
            True if the collector is running, False otherwise.
        """
        return self._running
    
    def _prepare_headers(self, api_source: ApiSource) -> Dict[str, str]:
        """
        Prepare headers for GraphQL requests.
        
        Args:
            api_source: The API source.
            
        Returns:
            Dictionary of headers.
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add authentication if configured
        if api_source.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {api_source.auth_token}"
        elif api_source.auth_type == "api_key":
            # Add API key to headers or as query parameter
            if api_source.auth_header:
                headers[api_source.auth_header] = api_source.auth_token
        
        # Add custom headers if any
        if api_source.headers:
            headers.update(api_source.headers)
        
        return headers
    
    async def collect_metrics(self) -> List[ApiMetrics]:
        """
        Collect metrics from the GraphQL API.
        
        Returns:
            List of API metrics.
        """
        if not self._running:
            logger.warning(f"Collector for API {self.api_source.id} is not running")
            return []
        
        metrics = []
        
        # Update last collection time
        self.last_collection = datetime.utcnow()
        
        # Collect metrics for each endpoint/operation
        for operation in self.api_source.endpoints:
            try:
                operation_metrics = await self._collect_operation_metrics(operation)
                if operation_metrics:
                    metrics.append(operation_metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics for operation {operation.name}: {str(e)}")
        
        # Update metrics count
        self.metrics_count += len(metrics)
        
        return metrics
    
    async def _collect_operation_metrics(self, operation: Any) -> Optional[ApiMetrics]:
        """
        Collect metrics for a specific GraphQL operation.
        
        Args:
            operation: The GraphQL operation.
            
        Returns:
            API metrics for the operation.
        """
        try:
            # Create GraphQL request
            query = operation.query
            variables = operation.variables or {}
            
            payload = {
                "query": query,
                "variables": variables
            }
            
            # Record start time
            start_time = time.time()
            
            # Send request to GraphQL API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_source.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.api_source.timeout or 10
                ) as response:
                    # Record end time
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # convert to ms
                    
                    # Get response
                    status_code = response.status
                    response_body = await response.text()
                    response_size = len(response_body)
                    
                    # Create metrics object
                    metrics = ApiMetrics(
                        id=str(uuid.uuid4()),
                        api_id=self.api_source.id,
                        endpoint_id=operation.id,
                        environment=self.api_source.environment,
                        timestamp=datetime.utcnow(),
                        response_time=response_time,
                        status_code=status_code,
                        response_size=response_size,
                        success=(status_code >= 200 and status_code < 300 and "errors" not in response_body),
                        error_message=None if status_code < 400 else f"HTTP Error: {status_code}",
                        tags=self.api_source.tags,
                        metadata={
                            "operation_name": operation.name,
                            "operation_type": operation.type,
                            "variables_count": len(variables) if variables else 0
                        }
                    )
                    
                    return metrics
                    
        except aiohttp.ClientError as e:
            # Handle connection errors
            logger.error(f"Connection error for GraphQL operation {operation.name}: {str(e)}")
            
            # Create error metrics
            metrics = ApiMetrics(
                id=str(uuid.uuid4()),
                api_id=self.api_source.id,
                endpoint_id=operation.id,
                environment=self.api_source.environment,
                timestamp=datetime.utcnow(),
                response_time=None,
                status_code=None,
                response_size=None,
                success=False,
                error_message=f"Connection error: {str(e)}",
                tags=self.api_source.tags,
                metadata={
                    "operation_name": operation.name,
                    "operation_type": operation.type,
                    "error_type": "connection_error"
                }
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for GraphQL operation {operation.name}: {str(e)}")
            return None 