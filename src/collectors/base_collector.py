"""
Base collector for API monitoring system.
"""
import abc
import time
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.models.api import ApiSource, ApiMetric, Environment

logger = logging.getLogger(__name__)

class BaseCollector(abc.ABC):
    """
    Base class for API collectors.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the collector.
        
        Args:
            api_source: The API source configuration.
        """
        self.api_source = api_source
        self.last_collection_time = 0
        self.collection_interval = 60  # Default collection interval in seconds
        self.enabled = api_source.is_active
    
    def update_config(self, api_source: ApiSource):
        """
        Update the collector configuration.
        
        Args:
            api_source: The updated API source configuration.
        """
        self.api_source = api_source
        self.enabled = api_source.is_active
    
    def should_collect(self) -> bool:
        """
        Determine if metrics should be collected based on sampling rate and
        collection interval.
        
        Returns:
            True if metrics should be collected, False otherwise.
        """
        if not self.enabled:
            return False
        
        current_time = time.time()
        
        # Check if enough time has passed since last collection
        if current_time - self.last_collection_time < self.collection_interval:
            return False
        
        # Apply sampling rate
        if self.api_source.sampling_rate < 1.0:
            if random.random() > self.api_source.sampling_rate:
                return False
        
        return True
    
    @abc.abstractmethod
    async def collect_metrics(self) -> List[ApiMetric]:
        """
        Collect metrics from the API.
        
        Returns:
            List of API metrics.
        """
        pass
    
    def create_metric(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        error: bool,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        payload_size: Optional[int] = None,
        response_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApiMetric:
        """
        Create an API metric.
        
        Args:
            endpoint: The API endpoint.
            method: The HTTP method.
            response_time: The response time in milliseconds.
            status_code: The HTTP status code.
            error: Whether the request resulted in an error.
            error_message: The error message, if any.
            request_id: The request ID, if any.
            trace_id: The OpenTelemetry trace ID, if any.
            span_id: The OpenTelemetry span ID, if any.
            payload_size: The request payload size in bytes, if available.
            response_size: The response size in bytes, if available.
            metadata: Additional metadata, if any.
            
        Returns:
            An API metric.
        """
        self.last_collection_time = time.time()
        
        return ApiMetric(
            id=str(uuid.uuid4()),  # Generate a unique ID for the metric
            api_id=self.api_source.id,
            timestamp=datetime.utcnow(),
            response_time=response_time,
            status_code=status_code,
            error=error,
            error_message=error_message,
            endpoint=endpoint,
            method=method,
            environment=self.api_source.environment,
            success=not error,  # Set success to the opposite of error
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
            payload_size=payload_size,
            response_size=response_size,
            metadata=metadata or {}
        )
    
    def cleanup(self):
        """
        Clean up resources.
        """
        pass 