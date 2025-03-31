"""
API models for the monitoring system.
"""
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

class Environment(str, Enum):
    """API environment types."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ON_PREMISES = "on-premises"

class Endpoint(BaseModel):
    """API endpoint configuration."""
    path: str
    method: str
    expected_response_time: int
    timeout: int
    description: Optional[str] = None

class ApiSource(BaseModel):
    """API source configuration."""
    id: str
    name: str
    description: str
    base_url: str
    environment: Environment
    endpoints: List[Endpoint]
    headers: Dict[str, str]
    auth_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    type: str = "rest"  # Default type for REST APIs
    sampling_rate: float = 1.0  # Default to collect all metrics
    timeout: int = 30  # Default timeout in seconds
    endpoint: Optional[str] = None  # Optional single endpoint for health checks
    authentication: Optional[Dict[str, Any]] = None  # Authentication configuration

class ApiMetric(BaseModel):
    """API metric data."""
    id: str
    api_id: str
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    error_message: Optional[str] = None
    environment: Environment
    timestamp: datetime
    error: bool = Field(default=False)  # Required field for validation
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    payload_size: Optional[int] = None
    response_size: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Anomaly(BaseModel):
    """Detected anomaly."""
    id: str
    api_id: str
    type: str
    severity: float
    description: str
    timestamp: datetime
    metric_value: float
    expected_value: float
    threshold: float
    environment: Environment
    context: Dict[str, Any]

class Prediction(BaseModel):
    """Predicted issues."""
    id: str
    api_id: str
    predicted_issues: List[str]
    confidence: float
    timestamp: datetime
    environment: Environment
    context: Dict[str, Any]

class Alert(BaseModel):
    """Alert notification."""
    id: str
    title: str
    description: str
    severity: str
    created_at: datetime
    status: str
    anomalies: List[str]
    apis: List[str]
    environments: List[Environment]
    tags: List[str]
    metadata: Dict[str, Any]

class AnomalyTriggerRequest(BaseModel):
    """Anomaly trigger request model for demo purposes."""
    type: str = Field(..., description="Type of anomaly to trigger")
    environment: Optional[str] = Field(None, description="Environment for single-environment anomalies")
    environments: Optional[List[str]] = Field(None, description="Environments for cross-environment anomalies")
    severity: str = Field("medium", description="Severity of the anomaly (low, medium, high, critical)")
    duration_minutes: int = Field(5, description="Duration of the anomaly in minutes") 