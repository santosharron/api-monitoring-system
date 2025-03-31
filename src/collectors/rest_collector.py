"""
REST API collector for API monitoring system.
"""
import logging
import aiohttp
import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.collectors.base_collector import BaseCollector
from src.models.api import ApiSource, ApiMetric

logger = logging.getLogger(__name__)

class RestApiCollector(BaseCollector):
    """
    Collector for REST APIs.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the REST API collector.
        
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
        # Create a session for REST API requests
        await self._ensure_session()
        logger.debug(f"Initialized REST API collector for {self.api_source.name}")
    
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
        logger.debug(f"Stopped REST API collector for {self.api_source.name}")
    
    async def _ensure_session(self):
        """
        Ensure that an HTTP session exists.
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)  # Default timeout of 30 seconds
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def collect_metrics(self) -> List[ApiMetric]:
        """
        Collect metrics from the REST API.
        
        Returns:
            List of API metrics.
        """
        metrics = []
        
        try:
            await self._ensure_session()
            
            # For REST APIs, we'll make a health check request to the base endpoint
            url = str(self.api_source.endpoint) if self.api_source.endpoint else self.api_source.base_url
            headers = self.api_source.headers or {}
            
            # Add authentication if configured
            if self.api_source.authentication:
                await self._add_authentication(headers)
            
            # Generate request and trace IDs for tracking
            request_id = str(uuid.uuid4())
            trace_id = str(uuid.uuid4())
            span_id = str(uuid.uuid4())
            
            headers["X-Request-ID"] = request_id
            
            # Add OpenTelemetry headers if available
            headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
            
            start_time = time.time()
            error = False
            error_message = None
            status_code = 0
            payload_size = 0
            response_size = 0
            
            try:
                async with self.session.get(url, headers=headers) as response:
                    status_code = response.status
                    response_body = await response.read()
                    response_size = len(response_body)
                    
                    # Check if response is an error
                    if status_code >= 400:
                        error = True
                        error_message = f"HTTP error {status_code}"
            except aiohttp.ClientError as e:
                error = True
                error_message = f"Connection error: {str(e)}"
                # For cloud environments, simulate a response to keep metrics flowing
                status_code = 503  # Service Unavailable
            except asyncio.TimeoutError:
                error = True
                error_message = "Request timed out"
                # For cloud environments, simulate a response to keep metrics flowing
                status_code = 504  # Gateway Timeout
            finally:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Create environment-specific metadata
            metadata = self._get_environment_metadata()
            
            # Add cloud-specific metadata
            metadata["is_cloud_environment"] = True
            metadata["collection_timestamp"] = datetime.utcnow().isoformat()
            
            # Create metric
            metric = self.create_metric(
                endpoint=url,
                method="GET",
                response_time=response_time,
                status_code=status_code,
                error=error,
                error_message=error_message,
                request_id=request_id,
                trace_id=trace_id,
                span_id=span_id,
                payload_size=payload_size,
                response_size=response_size,
                metadata=metadata
            )
            
            metrics.append(metric)
            
            # Update metrics counter
            self.metrics_count += 1
            self.last_collection = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error collecting REST API metrics for {self.api_source.name}: {str(e)}")
        
        return metrics
    
    async def _add_authentication(self, headers: Dict[str, str]):
        """
        Add authentication headers.
        
        Args:
            headers: The headers dictionary to modify.
        """
        auth = self.api_source.authentication
        if not auth:
            return
        
        auth_type = auth.get("type", "").lower()
        
        if auth_type == "bearer":
            token = auth.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "basic":
            username = auth.get("username")
            password = auth.get("password")
            if username and password:
                import base64
                auth_string = f"{username}:{password}"
                encoded = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "apikey":
            key = auth.get("key")
            header_name = auth.get("header_name", "X-API-Key")
            if key:
                headers[header_name] = key
    
    def _get_environment_metadata(self) -> Dict[str, Any]:
        """
        Get environment-specific metadata.
        
        Returns:
            Dictionary with environment metadata.
        """
        metadata = {}
        
        # Add environment-specific metadata
        if self.api_source.environment.value == "aws":
            # In a real implementation, we might get AWS metadata from EC2 metadata service
            metadata["cloud_provider"] = "aws"
            metadata["region"] = "us-east-1"  # Example region
        elif self.api_source.environment.value == "azure":
            metadata["cloud_provider"] = "azure"
            metadata["region"] = "eastus"  # Example region
        elif self.api_source.environment.value == "gcp":
            metadata["cloud_provider"] = "gcp"
            metadata["region"] = "us-central1"  # Example region
        elif self.api_source.environment.value == "on-premises":
            metadata["datacenter"] = "dc-1"  # Example datacenter
        
        return metadata
    
    def cleanup(self):
        """
        Clean up resources.
        """
        if self.session and not self.session.closed:
            if not self.session.closed:
                # Create a new event loop to close the session
                try:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(self.session.close())
                    loop.close()
                except Exception as e:
                    logger.error(f"Error closing aiohttp session: {str(e)}")
                    if not self.session.closed:
                        # Fallback
                        self.session._connector._close()
                        self.session._connector = None 