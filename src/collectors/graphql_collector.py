"""
GraphQL API metrics collector.
"""
import logging
import asyncio
import aiohttp
from typing import List, Any, Optional
from datetime import datetime

from src.models.api import ApiSource, ApiMetric, Environment
from src.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)

class GraphqlCollector(BaseCollector):
    """
    Collector for GraphQL APIs.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the GraphQL collector.
        
        Args:
            api_source: The API source configuration.
        """
        super().__init__(api_source)
        self.session = None
        self.last_collection = None
        self.metrics_count = 0
    
    async def initialize(self):
        """
        Initialize the collector.
        """
        # Create a session for GraphQL API requests
        await self._ensure_session()
        logger.debug(f"Initialized GraphQL collector for {self.api_source.name}")
    
    def is_running(self) -> bool:
        """
        Check if the collector is running.
        
        Returns:
            True if the collector is running, False otherwise.
        """
        return self.enabled
    
    async def stop(self):
        """
        Stop the collector.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        logger.debug(f"Stopped GraphQL collector for {self.api_source.name}")
    
    async def _ensure_session(self):
        """
        Ensure that an HTTP session exists.
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)  # Default timeout of 30 seconds
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def collect_metrics(self) -> List[ApiMetric]:
        """
        Collect metrics from the GraphQL API.
        
        Returns:
            List of API metrics.
        """
        metrics = []
        
        try:
            # Collect metrics for each operation
            for operation in self.api_source.endpoints:
                operation_metric = await self._collect_operation_metrics(operation)
                if operation_metric:
                    metrics.append(operation_metric)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting GraphQL metrics: {str(e)}")
            return []
    
    async def _collect_operation_metrics(self, operation: Any) -> Optional[ApiMetric]:
        """Collect metrics for a specific GraphQL operation."""
        try:
            # Prepare GraphQL query
            query = self._prepare_query(operation)
            
            # Make GraphQL request
            start_time = datetime.utcnow()
            
            async with self.session.post(
                self.api_source.base_url,
                json={"query": query},
                headers=self.api_source.headers
            ) as response:
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                # Parse response
                data = await response.json()
                
                # Check for errors
                errors = data.get("errors", [])
                success = not bool(errors)
                
                # Create metric
                metric = ApiMetric(
                    id=f"graphql-{start_time.timestamp()}",
                    api_id=self.api_source.id,
                    endpoint=operation.path,
                    method=operation.method,
                    response_time=response_time,
                    status_code=response.status,
                    success=success,
                    error_message=str(errors[0]) if errors else None,
                    environment=self.api_source.environment,
                    timestamp=start_time,
                    error=not success
                )
                
                return metric
                
        except Exception as e:
            logger.error(f"Error collecting operation metrics: {str(e)}")
            return None
    
    def _prepare_query(self, operation: Any) -> str:
        """Prepare GraphQL query for the operation."""
        # This is a placeholder. In a real implementation,
        # you would generate appropriate GraphQL queries
        # based on the operation type and parameters
        return """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """ 