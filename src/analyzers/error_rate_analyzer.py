"""
Error rate analyzer for API monitoring system.
"""
import logging
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.analyzers.base_analyzer import BaseAnalyzer
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Environment

logger = logging.getLogger(__name__)

class ErrorRateAnalyzer(BaseAnalyzer):
    """
    Analyzer for API error rate metrics.
    This is a simplified implementation.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the error rate analyzer.
        
        Args:
            api_source: The API source configuration.
        """
        super().__init__(api_source)
        self.min_data_points = 20  # Minimum number of data points required for analysis
    
    async def detect_anomalies(self, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect error rate anomalies.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of detected anomalies.
        """
        anomalies = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for error rate anomaly detection")
            return anomalies
        
        try:
            # Group metrics by endpoint
            metrics_by_endpoint = self._group_by_endpoint(metrics)
            
            for endpoint, endpoint_metrics in metrics_by_endpoint.items():
                # Skip if not enough data points
                if len(endpoint_metrics) < self.min_data_points:
                    continue
                
                # Calculate error rate
                error_rate = self._calculate_error_rate(endpoint_metrics)
                
                # Check for high error rate
                if error_rate > 0.05:  # 5% error rate threshold
                    # Calculate severity based on error rate
                    severity = min(1.0, error_rate * 5)  # Scale up to 1.0
                    
                    # Create anomaly
                    anomaly = self.create_anomaly(
                        api_id=self.api_source.id,
                        anomaly_type="high_error_rate",
                        severity=severity,
                        description=f"High error rate detected for {endpoint}",
                        metric_value=error_rate,
                        expected_value=0.01,  # 1% is normally acceptable
                        threshold=0.05,
                        environment=endpoint_metrics[0].environment,
                        context={
                            "endpoint": endpoint,
                            "error_count": sum(1 for m in endpoint_metrics if m.error),
                            "total_count": len(endpoint_metrics),
                            "time_range": f"{endpoint_metrics[0].timestamp.isoformat()} to {endpoint_metrics[-1].timestamp.isoformat()}"
                        }
                    )
                    
                    anomalies.append(anomaly)
        
        except Exception as e:
            logger.error(f"Error detecting error rate anomalies: {str(e)}")
        
        return anomalies
    
    async def predict_issues(self, metrics: List[ApiMetric]) -> List[Prediction]:
        """
        Predict future error rate issues.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of predictions.
        """
        predictions = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for error rate prediction")
            return predictions
        
        try:
            # Group metrics by endpoint
            metrics_by_endpoint = self._group_by_endpoint(metrics)
            
            for endpoint, endpoint_metrics in metrics_by_endpoint.items():
                # Skip if not enough data points
                if len(endpoint_metrics) < self.min_data_points:
                    continue
                
                # Sort by timestamp
                endpoint_metrics.sort(key=lambda x: x.timestamp)
                
                # Split into time windows (e.g., last hour, previous hour)
                now = datetime.utcnow()
                one_hour_ago = now - timedelta(hours=1)
                two_hours_ago = now - timedelta(hours=2)
                
                recent_metrics = [m for m in endpoint_metrics if m.timestamp >= one_hour_ago]
                previous_metrics = [m for m in endpoint_metrics if m.timestamp >= two_hours_ago and m.timestamp < one_hour_ago]
                
                if len(recent_metrics) < 10 or len(previous_metrics) < 10:
                    continue
                
                # Calculate error rates
                recent_error_rate = self._calculate_error_rate(recent_metrics)
                previous_error_rate = self._calculate_error_rate(previous_metrics)
                
                # Detect increasing trend
                if recent_error_rate > previous_error_rate * 1.5 and recent_error_rate > 0.02:
                    # Calculate predicted error rate (simple linear extrapolation)
                    rate_change = recent_error_rate - previous_error_rate
                    predicted_rate = recent_error_rate + rate_change
                    
                    # Calculate confidence based on data points and trend strength
                    confidence = min(0.9, 0.5 + (recent_error_rate / 0.1))
                    
                    # Create prediction
                    prediction = self.create_prediction(
                        api_id=self.api_source.id,
                        prediction_type="error_rate",
                        confidence=confidence,
                        predicted_for=now + timedelta(hours=1),
                        description=f"Error rate trending upward for {endpoint}",
                        metric_value=predicted_rate,
                        current_value=recent_error_rate,
                        trend="increasing",
                        environment=endpoint_metrics[0].environment,
                        context={
                            "endpoint": endpoint,
                            "recent_error_rate": recent_error_rate,
                            "previous_error_rate": previous_error_rate,
                            "rate_change": rate_change,
                            "recent_sample_size": len(recent_metrics),
                            "previous_sample_size": len(previous_metrics)
                        }
                    )
                    
                    predictions.append(prediction)
        
        except Exception as e:
            logger.error(f"Error predicting error rate issues: {str(e)}")
        
        return predictions
    
    def _group_by_endpoint(self, metrics: List[ApiMetric]) -> Dict[str, List[ApiMetric]]:
        """
        Group metrics by endpoint.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Dictionary mapping endpoints to lists of metrics.
        """
        metrics_by_endpoint = {}
        
        for metric in metrics:
            endpoint_key = f"{metric.method}:{metric.endpoint}"
            if endpoint_key not in metrics_by_endpoint:
                metrics_by_endpoint[endpoint_key] = []
            metrics_by_endpoint[endpoint_key].append(metric)
        
        return metrics_by_endpoint
    
    def _calculate_error_rate(self, metrics: List[ApiMetric]) -> float:
        """
        Calculate error rate from metrics.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Error rate (0.0-1.0).
        """
        if not metrics:
            return 0.0
        
        error_count = sum(1 for m in metrics if m.error)
        return error_count / len(metrics)