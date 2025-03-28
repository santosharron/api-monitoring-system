"""
Base analyzer for API monitoring system.
"""
import abc
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Environment

logger = logging.getLogger(__name__)

class BaseAnalyzer(abc.ABC):
    """
    Base class for API analyzers.
    """
    def __init__(self, api_source: Optional[ApiSource] = None):
        """
        Initialize the analyzer.
        
        Args:
            api_source: The API source configuration (None for global analyzers).
        """
        self.api_source = api_source
        self.analyzer_type = self.__class__.__name__
    
    def update_config(self, api_source: ApiSource):
        """
        Update the analyzer configuration.
        
        Args:
            api_source: The updated API source configuration.
        """
        self.api_source = api_source
    
    @abc.abstractmethod
    async def detect_anomalies(self, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect anomalies in API metrics.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of detected anomalies.
        """
        pass
    
    @abc.abstractmethod
    async def predict_issues(self, metrics: List[ApiMetric]) -> List[Prediction]:
        """
        Predict future issues based on API metrics.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of predictions.
        """
        pass
    
    def create_anomaly(
        self,
        api_id: str,
        anomaly_type: str,
        severity: float,
        description: str,
        metric_value: float,
        expected_value: Optional[float] = None,
        threshold: Optional[float] = None,
        environment: Optional[Environment] = None,
        context: Optional[Dict[str, Any]] = None,
        related_anomalies: Optional[List[str]] = None
    ) -> Anomaly:
        """
        Create an anomaly.
        
        Args:
            api_id: The ID of the API.
            anomaly_type: The type of anomaly.
            severity: The severity of the anomaly (0.0-1.0).
            description: A description of the anomaly.
            metric_value: The actual metric value.
            expected_value: The expected metric value.
            threshold: The threshold value.
            environment: The environment where the anomaly was detected.
            context: Additional context information.
            related_anomalies: IDs of related anomalies.
            
        Returns:
            An anomaly.
        """
        return Anomaly(
            id=f"anom-{uuid.uuid4()}",
            api_id=api_id,
            type=anomaly_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            description=description,
            metric_value=metric_value,
            expected_value=expected_value,
            threshold=threshold,
            environment=environment or (self.api_source.environment if self.api_source else None),
            context=context or {},
            related_anomalies=related_anomalies or []
        )
    
    def create_prediction(
        self,
        api_id: str,
        prediction_type: str,
        confidence: float,
        predicted_for: datetime,
        description: str,
        metric_value: float,
        current_value: Optional[float] = None,
        trend: str = "increasing",
        environment: Optional[Environment] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Prediction:
        """
        Create a prediction.
        
        Args:
            api_id: The ID of the API.
            prediction_type: The type of prediction.
            confidence: The confidence level of the prediction (0.0-1.0).
            predicted_for: The timestamp for which the prediction is made.
            description: A description of the prediction.
            metric_value: The predicted metric value.
            current_value: The current metric value.
            trend: The trend direction (increasing, decreasing, stable).
            environment: The environment for which the prediction is made.
            context: Additional context information.
            
        Returns:
            A prediction.
        """
        return Prediction(
            id=f"pred-{uuid.uuid4()}",
            api_id=api_id,
            type=prediction_type,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            predicted_for=predicted_for,
            description=description,
            metric_value=metric_value,
            current_value=current_value,
            trend=trend,
            environment=environment or (self.api_source.environment if self.api_source else None),
            context=context or {}
        )
    
    def cleanup(self):
        """
        Clean up resources.
        """
        pass 