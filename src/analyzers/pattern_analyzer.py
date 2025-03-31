"""
Pattern analyzer for API metrics.
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

from src.models.api import ApiSource, ApiMetric, Anomaly, Environment

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """Analyzes patterns in API metrics to detect anomalies."""
    
    def __init__(self, api_source=None):
        """
        Initialize the pattern analyzer.
        
        Args:
            api_source: API source to analyze. This parameter is optional and can be None
                        for backward compatibility.
        """
        self.api_source = api_source
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.lof = LocalOutlierFactor(n_neighbors=20, contamination=0.1)
    
    def cleanup(self):
        """Clean up resources used by the analyzer."""
        # Nothing specific to clean up for this analyzer
        # This method is required by the analyzer manager
        pass
    
    def update_config(self, api_source: ApiSource):
        """Update the analyzer configuration with a new API source."""
        self.api_source = api_source
        # Reset models if needed
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.lof = LocalOutlierFactor(n_neighbors=20, contamination=0.1)
    
    async def analyze(self, metrics: List[ApiMetric]) -> List[Anomaly]:
        """Analyze metrics to detect pattern-based anomalies."""
        anomalies = []
        
        try:
            # Group metrics by endpoint
            endpoint_metrics = self._group_by_endpoint(metrics)
            
            # Analyze each endpoint
            for endpoint_id, endpoint_data in endpoint_metrics.items():
                endpoint_anomalies = self._analyze_endpoint_patterns(endpoint_id, endpoint_data)
                anomalies.extend(endpoint_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {str(e)}")
            return []
    
    def _group_by_endpoint(self, metrics: List[ApiMetric]) -> Dict[str, List[ApiMetric]]:
        """Group metrics by endpoint."""
        grouped = {}
        for metric in metrics:
            key = f"{metric.api_id}:{metric.endpoint}:{metric.method}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(metric)
        return grouped
    
    def _analyze_endpoint_patterns(self, endpoint_id: str, metrics: List[ApiMetric]) -> List[Anomaly]:
        """Analyze patterns for a specific endpoint."""
        anomalies = []
        
        try:
            # Sort metrics by timestamp
            metrics.sort(key=lambda x: x.timestamp)
            
            # Analyze response time patterns
            response_time_anomalies = self._analyze_response_time_patterns(endpoint_id, metrics)
            anomalies.extend(response_time_anomalies)
            
            # Analyze error patterns
            error_anomalies = self._analyze_error_patterns(endpoint_id, metrics)
            anomalies.extend(error_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error analyzing endpoint patterns: {str(e)}")
            return []
    
    def _analyze_response_time_patterns(self, endpoint_id: str, metrics: List[ApiMetric]) -> List[Anomaly]:
        """Analyze response time patterns to detect anomalies."""
        anomalies = []
        
        try:
            # Extract response times
            response_times = [metric.response_time for metric in metrics]
            
            if len(response_times) < 20:  # Need enough samples for analysis
                return anomalies
            
            # Convert to numpy array for analysis
            X = np.array(response_times).reshape(-1, 1)
            
            # Fit and predict with Isolation Forest
            self.isolation_forest.fit(X)
            predictions = self.isolation_forest.predict(X)
            
            # Find anomalies
            for i, (metric, prediction) in enumerate(zip(metrics, predictions)):
                if prediction == -1:  # Anomaly detected
                    anomaly = Anomaly(
                        id=f"pattern-{metric.timestamp.timestamp()}",
                        api_id=metric.api_id,
                        type="response_time_pattern",
                        severity=0.8,  # High severity for pattern anomalies
                        description=f"Response time pattern anomaly detected for {endpoint_id}",
                        timestamp=metric.timestamp,
                        metric_value=metric.response_time,
                        expected_value=np.mean(response_times),
                        threshold=np.std(response_times) * 2,
                        environment=metric.environment,
                        context={
                            "endpoint": endpoint_id,
                            "response_times": response_times[i-5:i+5] if i > 5 else response_times[:i+5]
                        }
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error analyzing response time patterns: {str(e)}")
            return []
    
    def _analyze_error_patterns(self, endpoint_id: str, metrics: List[ApiMetric]) -> List[Anomaly]:
        """Analyze error patterns to detect anomalies."""
        anomalies = []
        
        try:
            # Calculate error rate over time windows
            window_size = timedelta(minutes=5)
            error_counts = {}
            
            for metric in metrics:
                window_start = metric.timestamp - (metric.timestamp % window_size)
                if window_start not in error_counts:
                    error_counts[window_start] = {"total": 0, "errors": 0}
                error_counts[window_start]["total"] += 1
                if not metric.success:
                    error_counts[window_start]["errors"] += 1
            
            # Analyze error rates
            for window_start, counts in error_counts.items():
                error_rate = counts["errors"] / counts["total"]
                if error_rate > 0.1:  # More than 10% errors
                    anomaly = Anomaly(
                        id=f"error-{window_start.timestamp()}",
                        api_id=metrics[0].api_id,  # Use first metric's API ID
                        type="error_rate_pattern",
                        severity=0.9,  # Very high severity for error patterns
                        description=f"High error rate detected for {endpoint_id}",
                        timestamp=window_start,
                        metric_value=error_rate,
                        expected_value=0.05,  # Expected 5% error rate
                        threshold=0.1,  # 10% threshold
                        environment=metrics[0].environment,
                        context={
                            "endpoint": endpoint_id,
                            "total_requests": counts["total"],
                            "error_count": counts["errors"]
                        }
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error analyzing error patterns: {str(e)}")
            return [] 