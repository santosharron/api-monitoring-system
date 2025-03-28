"""
Data models for API monitoring system.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator

class Environment(str, Enum):
    """
    Environment types where APIs can be hosted.
    """
    ON_PREMISES = "on-premises"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OTHER = "other"

class ApiType(str, Enum):
    """
    Types of APIs.
    """
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    SOAP = "soap"
    WEBHOOK = "webhook"
    CUSTOM = "custom"

class ApiSource(BaseModel):
    """
    API source configuration.
    """
    id: str = Field(..., description="Unique identifier for the API source")
    name: str = Field(..., description="Name of the API")
    description: Optional[str] = Field(default=None, description="Description of the API")
    type: ApiType = Field(..., description="Type of the API")
    environment: Environment = Field(..., description="Environment where the API is hosted")
    base_url: HttpUrl = Field(..., description="Base URL of the API")
    endpoints: List[Dict[str, Any]] = Field(default_factory=list, description="Endpoints to monitor")
    auth_type: Optional[str] = Field(default=None, description="Authentication type (bearer, api_key, etc.)")
    auth_token: Optional[str] = Field(default=None, description="Authentication token or key")
    auth_header: Optional[str] = Field(default=None, description="Header name for auth token if needed")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Headers to include in requests")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    sampling_rate: float = Field(default=1.0, description="Sampling rate for monitoring (0.0-1.0)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the API")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    active: bool = Field(default=True, description="Whether monitoring is active")
    
    @validator("sampling_rate")
    def validate_sampling_rate(cls, v):
        """
        Validate that sampling rate is between 0 and 1.
        """
        if v < 0.0 or v > 1.0:
            raise ValueError("Sampling rate must be between 0.0 and 1.0")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "id": "api-123456",
                "name": "payment-service",
                "description": "Payment processing service API",
                "type": "rest",
                "environment": "aws",
                "base_url": "https://api.example.com/payments",
                "endpoints": [
                    {
                        "id": "endpoint-1",
                        "path": "/transactions",
                        "method": "POST",
                        "name": "Create Transaction"
                    }
                ],
                "auth_type": "bearer",
                "auth_token": "xxx",
                "headers": {
                    "Content-Type": "application/json",
                    "X-API-Key": "xxx"
                },
                "timeout": 30,
                "sampling_rate": 1.0,
                "tags": ["payment", "critical", "financial"],
                "active": True
            }
        }

class ApiMetric(BaseModel):
    """
    API metric data (legacy model).
    """
    api_id: str = Field(..., description="ID of the API source")
    timestamp: datetime = Field(..., description="Timestamp when the metric was collected")
    response_time: float = Field(..., description="Response time in milliseconds")
    status_code: int = Field(..., description="HTTP status code")
    error: bool = Field(..., description="Whether the request resulted in an error")
    error_message: Optional[str] = Field(default=None, description="Error message if any")
    endpoint: str = Field(..., description="Specific endpoint that was called")
    method: str = Field(..., description="HTTP method used")
    environment: Environment = Field(..., description="Environment where the API is hosted")
    request_id: Optional[str] = Field(default=None, description="Unique request ID")
    trace_id: Optional[str] = Field(default=None, description="OpenTelemetry trace ID")
    span_id: Optional[str] = Field(default=None, description="OpenTelemetry span ID")
    payload_size: Optional[int] = Field(default=None, description="Size of the request payload in bytes")
    response_size: Optional[int] = Field(default=None, description="Size of the response in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "api_id": "12345",
                "timestamp": "2023-04-01T12:00:00Z",
                "response_time": 150.25,
                "status_code": 200,
                "error": False,
                "endpoint": "/api/v1/payments",
                "method": "POST",
                "environment": "aws",
                "request_id": "req-123456",
                "trace_id": "trace-123456",
                "span_id": "span-123456",
                "payload_size": 1024,
                "response_size": 512,
                "metadata": {
                    "region": "us-east-1",
                    "instance": "i-12345"
                }
            }
        }

class ApiMetrics(BaseModel):
    """
    API metrics data (current model).
    """
    id: str = Field(..., description="Unique identifier for this metric record")
    api_id: str = Field(..., description="ID of the API source")
    endpoint_id: str = Field(..., description="ID of the specific endpoint")
    environment: Environment = Field(..., description="Environment where the API is hosted")
    timestamp: datetime = Field(..., description="Timestamp when the metric was collected")
    response_time: Optional[float] = Field(default=None, description="Response time in milliseconds")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    response_size: Optional[int] = Field(default=None, description="Size of the response in bytes")
    success: bool = Field(..., description="Whether the request was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if any")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "metric-123456",
                "api_id": "api-123456",
                "endpoint_id": "endpoint-1",
                "environment": "aws",
                "timestamp": "2023-04-01T12:00:00Z",
                "response_time": 150.25,
                "status_code": 200,
                "response_size": 512,
                "success": True,
                "tags": ["payment", "critical"],
                "metadata": {
                    "method": "POST",
                    "region": "us-east-1",
                    "instance": "i-12345"
                }
            }
        }

class Anomaly(BaseModel):
    """
    Anomaly detection result.
    """
    id: Optional[str] = Field(default=None, description="Unique identifier for the anomaly")
    api_id: str = Field(..., description="ID of the API source")
    type: str = Field(..., description="Type of anomaly (response_time, error_rate, etc.)")
    severity: float = Field(..., description="Severity score of the anomaly (0.0-1.0)")
    timestamp: datetime = Field(..., description="Timestamp when the anomaly was detected")
    description: str = Field(..., description="Description of the anomaly")
    metric_value: float = Field(..., description="Actual metric value")
    expected_value: Optional[float] = Field(default=None, description="Expected metric value")
    threshold: Optional[float] = Field(default=None, description="Threshold value")
    environment: Environment = Field(..., description="Environment where the anomaly was detected")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context information")
    related_anomalies: List[str] = Field(default=[], description="IDs of related anomalies")
    is_acknowledged: bool = Field(default=False, description="Whether the anomaly has been acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="User who acknowledged the anomaly")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Timestamp when the anomaly was acknowledged")
    
    class Config:
        schema_extra = {
            "example": {
                "api_id": "12345",
                "type": "response_time",
                "severity": 0.85,
                "timestamp": "2023-04-01T12:05:00Z",
                "description": "Response time spike detected",
                "metric_value": 500.5,
                "expected_value": 150.0,
                "threshold": 300.0,
                "environment": "aws",
                "context": {
                    "endpoint": "/api/v1/payments",
                    "method": "POST",
                    "region": "us-east-1"
                },
                "related_anomalies": [],
                "is_acknowledged": False
            }
        }

class Alert(BaseModel):
    """
    Alert generated based on anomalies.
    """
    id: Optional[str] = Field(default=None, description="Unique identifier for the alert")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    severity: str = Field(..., description="Alert severity (critical, high, medium, low)")
    created_at: datetime = Field(..., description="Timestamp when the alert was created")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp when the alert was last updated")
    status: str = Field(default="open", description="Alert status (open, acknowledged, resolved)")
    anomalies: List[str] = Field(..., description="IDs of anomalies related to this alert")
    api_id: str = Field(..., description="ID of the API affected by this alert")
    api_name: str = Field(..., description="Name of the API affected by this alert")
    environment: Environment = Field(..., description="Environment affected by this alert")
    assignee: Optional[str] = Field(default=None, description="User assigned to the alert")
    tags: List[str] = Field(default=[], description="Tags for categorizing the alert")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Payment API Response Time Alert",
                "description": "Multiple response time anomalies detected in the Payment API",
                "severity": "high",
                "created_at": "2023-04-01T12:10:00Z",
                "status": "open",
                "anomalies": ["anom-12345", "anom-12346"],
                "api_id": "12345",
                "api_name": "Payment Service API",
                "environment": "aws",
                "tags": ["payment", "critical", "financial"],
                "metadata": {
                    "affected_customers": 150,
                    "potential_revenue_impact": "high"
                }
            }
        }

class Prediction(BaseModel):
    """
    Prediction of potential issues.
    """
    id: Optional[str] = Field(default=None, description="Unique identifier for the prediction")
    api_id: str = Field(..., description="ID of the API source")
    type: str = Field(..., description="Type of prediction (response_time, error_rate, etc.)")
    confidence: float = Field(..., description="Confidence level of the prediction (0.0-1.0)")
    timestamp: datetime = Field(..., description="Timestamp when the prediction was made")
    predicted_for: datetime = Field(..., description="Timestamp for which the prediction is made")
    description: str = Field(..., description="Description of the prediction")
    metric_value: float = Field(..., description="Predicted metric value")
    current_value: Optional[float] = Field(default=None, description="Current metric value")
    trend: str = Field(..., description="Trend direction (increasing, decreasing, stable)")
    environment: Environment = Field(..., description="Environment for which the prediction is made")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context information")
    
    class Config:
        schema_extra = {
            "example": {
                "api_id": "12345",
                "type": "error_rate",
                "confidence": 0.75,
                "timestamp": "2023-04-01T12:00:00Z",
                "predicted_for": "2023-04-01T14:00:00Z",
                "description": "Increasing error rate predicted",
                "metric_value": 0.05,
                "current_value": 0.01,
                "trend": "increasing",
                "environment": "aws",
                "context": {
                    "endpoint": "/api/v1/payments",
                    "method": "POST",
                    "region": "us-east-1"
                }
            }
        } 