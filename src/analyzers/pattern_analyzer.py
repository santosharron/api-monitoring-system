"""
Pattern analyzer for API monitoring system.
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from src.models.api import ApiSource, ApiMetrics, Anomaly, Environment

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """
    Analyzer for detecting patterns in API metrics.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the pattern analyzer.
        
        Args:
            api_source: The API source to analyze.
        """
        self.api_source = api_source
        self.patterns = {}
        self.last_analysis = None
    
    async def analyze(self, metrics: List[ApiMetrics]) -> List[Anomaly]:
        """
        Analyze metrics to detect patterns.
        
        Args:
            metrics: List of API metrics to analyze.
            
        Returns:
            List of anomalies detected.
        """
        if not metrics:
            logger.debug(f"No metrics to analyze for {self.api_source.name}")
            return []
        
        # Record analysis time
        self.last_analysis = datetime.utcnow()
        
        # Group metrics by endpoint
        endpoint_metrics = self._group_by_endpoint(metrics)
        
        # Detect patterns and anomalies
        anomalies = []
        
        for endpoint_id, metrics_list in endpoint_metrics.items():
            # Perform pattern analysis on metrics for this endpoint
            endpoint_anomalies = self._analyze_endpoint_patterns(endpoint_id, metrics_list)
            anomalies.extend(endpoint_anomalies)
        
        return anomalies
    
    def _group_by_endpoint(self, metrics: List[ApiMetrics]) -> Dict[str, List[ApiMetrics]]:
        """
        Group metrics by endpoint.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Dictionary of metrics grouped by endpoint ID.
        """
        grouped = {}
        
        for metric in metrics:
            endpoint_id = metric.endpoint_id
            
            if endpoint_id not in grouped:
                grouped[endpoint_id] = []
            
            grouped[endpoint_id].append(metric)
        
        return grouped
    
    def _analyze_endpoint_patterns(self, endpoint_id: str, metrics: List[ApiMetrics]) -> List[Anomaly]:
        """
        Analyze patterns in metrics for a specific endpoint.
        
        Args:
            endpoint_id: The endpoint ID.
            metrics: List of metrics for the endpoint.
            
        Returns:
            List of anomalies detected.
        """
        anomalies = []
        
        # Sort metrics by timestamp
        metrics.sort(key=lambda m: m.timestamp)
        
        # Check for response time patterns
        response_time_anomalies = self._analyze_response_time_patterns(endpoint_id, metrics)
        anomalies.extend(response_time_anomalies)
        
        # Check for error patterns
        error_anomalies = self._analyze_error_patterns(endpoint_id, metrics)
        anomalies.extend(error_anomalies)
        
        return anomalies
    
    def _analyze_response_time_patterns(self, endpoint_id: str, metrics: List[ApiMetrics]) -> List[Anomaly]:
        """
        Analyze response time patterns.
        
        Args:
            endpoint_id: The endpoint ID.
            metrics: List of metrics for the endpoint.
            
        Returns:
            List of response time anomalies detected.
        """
        anomalies = []
        
        # Extract response times (skip None values)
        response_times = [m.response_time for m in metrics if m.response_time is not None]
        
        if not response_times or len(response_times) < 5:
            # Not enough data for pattern analysis
            return []
        
        # Calculate statistics
        mean_rt = np.mean(response_times)
        std_rt = np.std(response_times)
        
        # Check for recent outliers (last 3 values)
        for i, metric in enumerate(metrics[-3:]):
            if metric.response_time is None:
                continue
            
            # Check if response time is an outlier (>3 standard deviations)
            if std_rt > 0 and abs(metric.response_time - mean_rt) > 3 * std_rt:
                # Create anomaly
                anomaly = Anomaly(
                    api_id=self.api_source.id,
                    type="response_time_outlier",
                    severity=min(0.9, abs(metric.response_time - mean_rt) / (4 * std_rt)),
                    timestamp=datetime.utcnow(),
                    description=f"Response time outlier detected for endpoint {endpoint_id}",
                    metric_value=metric.response_time,
                    expected_value=mean_rt,
                    threshold=mean_rt + 3 * std_rt,
                    environment=self.api_source.environment,
                    context={
                        "endpoint_id": endpoint_id,
                        "standard_deviation": std_rt,
                        "z_score": (metric.response_time - mean_rt) / std_rt,
                        "metric_id": metric.id
                    }
                )
                anomalies.append(anomaly)
        
        # Check for trends (increasing or decreasing pattern)
        if len(response_times) >= 10:
            # Use simple linear regression to detect trend
            x = np.arange(len(response_times))
            y = np.array(response_times)
            
            # Calculate slope
            slope = np.polyfit(x, y, 1)[0]
            
            # Normalize slope to make it comparable
            normalized_slope = slope * len(response_times) / mean_rt if mean_rt > 0 else 0
            
            # Check if there's a significant trend
            if abs(normalized_slope) > 0.5:  # Threshold for trend detection
                trend_type = "increasing" if normalized_slope > 0 else "decreasing"
                
                # Only report increasing trends as anomalies (decreasing is good)
                if trend_type == "increasing":
                    anomaly = Anomaly(
                        api_id=self.api_source.id,
                        type="response_time_trend",
                        severity=min(0.8, abs(normalized_slope) / 2),
                        timestamp=datetime.utcnow(),
                        description=f"{trend_type.capitalize()} response time trend detected for endpoint {endpoint_id}",
                        metric_value=normalized_slope,
                        expected_value=0,
                        threshold=0.5,
                        environment=self.api_source.environment,
                        context={
                            "endpoint_id": endpoint_id,
                            "trend_type": trend_type,
                            "slope": slope,
                            "data_points": len(response_times)
                        }
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _analyze_error_patterns(self, endpoint_id: str, metrics: List[ApiMetrics]) -> List[Anomaly]:
        """
        Analyze error patterns.
        
        Args:
            endpoint_id: The endpoint ID.
            metrics: List of metrics for the endpoint.
            
        Returns:
            List of error anomalies detected.
        """
        anomalies = []
        
        if len(metrics) < 5:
            # Not enough data for pattern analysis
            return []
        
        # Count failures in recent metrics (last 10 or fewer)
        recent_metrics = metrics[-min(10, len(metrics)):]
        failure_count = sum(1 for m in recent_metrics if not m.success)
        error_rate = failure_count / len(recent_metrics)
        
        # Check if error rate is unusually high (>20%)
        if error_rate > 0.2:
            anomaly = Anomaly(
                api_id=self.api_source.id,
                type="error_rate",
                severity=min(0.95, error_rate * 1.5),  # Higher severity for higher error rates
                timestamp=datetime.utcnow(),
                description=f"High error rate detected for endpoint {endpoint_id}",
                metric_value=error_rate,
                expected_value=0.05,  # Expect low error rate
                threshold=0.2,
                environment=self.api_source.environment,
                context={
                    "endpoint_id": endpoint_id,
                    "failure_count": failure_count,
                    "total_count": len(recent_metrics),
                    "recent_error_messages": [m.error_message for m in recent_metrics if not m.success and m.error_message]
                }
            )
            anomalies.append(anomaly)
        
        # Check for repeated same errors
        error_messages = {}
        for metric in recent_metrics:
            if not metric.success and metric.error_message:
                if metric.error_message not in error_messages:
                    error_messages[metric.error_message] = 0
                error_messages[metric.error_message] += 1
        
        # If the same error appears multiple times
        for error_msg, count in error_messages.items():
            if count >= 3:  # Multiple occurrences of the same error
                error_rate = count / len(recent_metrics)
                anomaly = Anomaly(
                    api_id=self.api_source.id,
                    type="repeated_error",
                    severity=min(0.9, count / len(recent_metrics) * 2),
                    timestamp=datetime.utcnow(),
                    description=f"Repeated error detected for endpoint {endpoint_id}",
                    metric_value=count,
                    expected_value=1,
                    threshold=3,
                    environment=self.api_source.environment,
                    context={
                        "endpoint_id": endpoint_id,
                        "error_message": error_msg,
                        "occurrences": count,
                        "total_metrics": len(recent_metrics)
                    }
                )
                anomalies.append(anomaly)
        
        return anomalies 