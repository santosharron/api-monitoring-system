"""
Response time analyzer for API monitoring system.
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pyod.models.knn import KNN
from pyod.models.iforest import IForest
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

from src.analyzers.base_analyzer import BaseAnalyzer
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Environment

logger = logging.getLogger(__name__)

class ResponseTimeAnalyzer(BaseAnalyzer):
    """
    Analyzer for API response time metrics.
    """
    def __init__(self, api_source: ApiSource):
        """
        Initialize the response time analyzer.
        
        Args:
            api_source: The API source configuration.
        """
        super().__init__(api_source)
        self.anomaly_threshold = 0.95  # Default threshold for anomaly detection
        self.min_data_points = 30  # Minimum number of data points required for analysis
        self.history = {}  # Store historical data for different endpoints
    
    async def detect_anomalies(self, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect response time anomalies using machine learning.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of detected anomalies.
        """
        anomalies = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for response time anomaly detection")
            return anomalies
        
        try:
            # Group metrics by endpoint
            metrics_by_endpoint = self._group_by_endpoint(metrics)
            
            for endpoint, endpoint_metrics in metrics_by_endpoint.items():
                # Only analyze if we have enough data points
                if len(endpoint_metrics) < self.min_data_points:
                    continue
                
                # Detect spike anomalies
                spike_anomalies = self._detect_spikes(endpoint, endpoint_metrics)
                anomalies.extend(spike_anomalies)
                
                # Detect pattern change anomalies
                pattern_anomalies = self._detect_pattern_changes(endpoint, endpoint_metrics)
                anomalies.extend(pattern_anomalies)
                
                # Update history with new data
                self._update_history(endpoint, endpoint_metrics)
        
        except Exception as e:
            logger.error(f"Error detecting response time anomalies: {str(e)}")
        
        return anomalies
    
    async def predict_issues(self, metrics: List[ApiMetric]) -> List[Prediction]:
        """
        Predict future response time issues.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            List of predictions.
        """
        predictions = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for response time prediction")
            return predictions
        
        try:
            # Group metrics by endpoint
            metrics_by_endpoint = self._group_by_endpoint(metrics)
            
            for endpoint, endpoint_metrics in metrics_by_endpoint.items():
                # Only predict if we have enough data points
                if len(endpoint_metrics) < self.min_data_points:
                    continue
                
                # Forecast future response times
                forecast = self._forecast_response_times(endpoint, endpoint_metrics)
                if forecast:
                    predicted_value, confidence, timestamp, description = forecast
                    
                    # Get current average response time
                    current_value = np.mean([m.response_time for m in endpoint_metrics[-10:]])
                    
                    # Determine trend
                    trend = "increasing" if predicted_value > current_value else "decreasing" if predicted_value < current_value else "stable"
                    
                    # Create prediction
                    prediction = self.create_prediction(
                        api_id=self.api_source.id,
                        prediction_type="response_time",
                        confidence=confidence,
                        predicted_for=timestamp,
                        description=description,
                        metric_value=predicted_value,
                        current_value=current_value,
                        trend=trend,
                        context={
                            "endpoint": endpoint,
                            "method": endpoint_metrics[0].method,
                            "analysis_time_range": f"{endpoint_metrics[0].timestamp.isoformat()} to {endpoint_metrics[-1].timestamp.isoformat()}"
                        }
                    )
                    
                    predictions.append(prediction)
        
        except Exception as e:
            logger.error(f"Error predicting response time issues: {str(e)}")
        
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
        
        # Sort metrics by timestamp for each endpoint
        for endpoint in metrics_by_endpoint:
            metrics_by_endpoint[endpoint].sort(key=lambda x: x.timestamp)
        
        return metrics_by_endpoint
    
    def _detect_spikes(self, endpoint: str, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect response time spikes using KNN outlier detection.
        
        Args:
            endpoint: The endpoint being analyzed.
            metrics: List of API metrics for the endpoint.
            
        Returns:
            List of spike anomalies.
        """
        anomalies = []
        
        # Extract response times and convert to numpy array
        response_times = np.array([m.response_time for m in metrics]).reshape(-1, 1)
        
        # Scale the data
        scaler = StandardScaler()
        response_times_scaled = scaler.fit_transform(response_times)
        
        # Use K-Nearest Neighbors for outlier detection
        knn = KNN(contamination=0.05)  # Assuming 5% of data points are outliers
        knn.fit(response_times_scaled)
        
        # Get anomaly scores
        outlier_scores = knn.decision_scores_
        is_outlier = knn.predict(response_times_scaled)
        
        # Create anomalies for outliers
        for i, (metric, score, outlier) in enumerate(zip(metrics, outlier_scores, is_outlier)):
            if outlier == 1 and score > self.anomaly_threshold:
                # Calculate moving average as the expected value
                window_size = min(10, len(metrics))
                start_idx = max(0, i - window_size)
                end_idx = min(len(metrics), i + window_size)
                expected_value = np.mean([m.response_time for m in metrics[start_idx:end_idx] if m != metric])
                
                # Calculate threshold as a percentage above the expected value
                threshold = expected_value * 1.5  # 50% above expected value
                
                # Calculate severity based on how much the value exceeds the threshold
                severity = min(1.0, (metric.response_time - expected_value) / expected_value)
                
                # Create anomaly
                anomaly = self.create_anomaly(
                    api_id=self.api_source.id,
                    anomaly_type="response_time_spike",
                    severity=severity,
                    description=f"Response time spike detected for {endpoint}",
                    metric_value=metric.response_time,
                    expected_value=expected_value,
                    threshold=threshold,
                    environment=metric.environment,
                    context={
                        "endpoint": endpoint,
                        "method": metric.method,
                        "status_code": metric.status_code,
                        "timestamp": metric.timestamp.isoformat(),
                        "outlier_score": float(score)
                    }
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_pattern_changes(self, endpoint: str, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect response time pattern changes using Isolation Forest.
        
        Args:
            endpoint: The endpoint being analyzed.
            metrics: List of API metrics for the endpoint.
            
        Returns:
            List of pattern change anomalies.
        """
        anomalies = []
        
        # Check if we have historical data for this endpoint
        if endpoint not in self.history:
            return anomalies
        
        historical_metrics = self.history[endpoint]
        
        # Need at least min_data_points historical metrics
        if len(historical_metrics) < self.min_data_points:
            return anomalies
        
        try:
            # Extract response times and timestamps
            historical_times = np.array([m.response_time for m in historical_metrics]).reshape(-1, 1)
            current_times = np.array([m.response_time for m in metrics]).reshape(-1, 1)
            
            # Create features (e.g., response time, hour of day, day of week)
            historical_features = self._create_time_features(historical_metrics)
            current_features = self._create_time_features(metrics)
            
            # Train Isolation Forest on historical data
            iforest = IForest(contamination=0.1, random_state=42)
            iforest.fit(historical_features)
            
            # Predict on current data
            anomaly_scores = iforest.decision_function(current_features)
            is_anomaly = iforest.predict(current_features)
            
            # Find pattern changes (multiple consecutive anomalies)
            pattern_change_indices = []
            consecutive_count = 0
            
            for i, (score, anomaly) in enumerate(zip(anomaly_scores, is_anomaly)):
                if anomaly == 1:
                    consecutive_count += 1
                    if consecutive_count >= 3:  # At least 3 consecutive anomalies
                        pattern_change_indices.append(i)
                else:
                    consecutive_count = 0
            
            # Create anomalies for pattern changes
            for i in pattern_change_indices:
                metric = metrics[i]
                
                # Calculate expected value from historical data
                expected_value = np.mean(historical_times)
                
                # Calculate threshold
                threshold = expected_value * 1.3  # 30% above historical average
                
                # Calculate severity
                score = anomaly_scores[i]
                severity = min(1.0, float(score) / 0.5)  # Normalize score
                
                # Create anomaly
                anomaly = self.create_anomaly(
                    api_id=self.api_source.id,
                    anomaly_type="response_time_pattern_change",
                    severity=severity,
                    description=f"Response time pattern change detected for {endpoint}",
                    metric_value=metric.response_time,
                    expected_value=float(expected_value),
                    threshold=float(threshold),
                    environment=metric.environment,
                    context={
                        "endpoint": endpoint,
                        "method": metric.method,
                        "timestamp": metric.timestamp.isoformat(),
                        "anomaly_score": float(score),
                        "historical_mean": float(expected_value),
                        "recent_mean": float(np.mean(current_times[-10:]))
                    }
                )
                
                anomalies.append(anomaly)
        
        except Exception as e:
            logger.error(f"Error detecting pattern changes: {str(e)}")
        
        return anomalies
    
    def _forecast_response_times(self, endpoint: str, metrics: List[ApiMetric]) -> Optional[Tuple[float, float, datetime, str]]:
        """
        Forecast future response times using ARIMA model.
        
        Args:
            endpoint: The endpoint being analyzed.
            metrics: List of API metrics for the endpoint.
            
        Returns:
            Tuple of (predicted value, confidence, timestamp, description) or None.
        """
        try:
            # Extract response times and timestamps
            response_times = [m.response_time for m in metrics]
            timestamps = [m.timestamp for m in metrics]
            
            # Create DataFrame
            df = pd.DataFrame({
                'timestamp': timestamps,
                'response_time': response_times
            })
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            # Resample to regular intervals (e.g., minutes)
            df_resampled = df.resample('1T').mean().fillna(method='ffill')
            
            # Fit ARIMA model
            model = ARIMA(df_resampled['response_time'], order=(5,1,0))
            model_fit = model.fit()
            
            # Forecast next hour
            forecast = model_fit.forecast(steps=60)  # 60 minutes
            
            # Get the prediction for 30 minutes in the future
            forecast_value = forecast[30]
            prediction_time = df_resampled.index[-1] + timedelta(minutes=30)
            
            # Calculate confidence
            confidence = 0.8  # Simplified confidence calculation
            
            # Generate description
            current_avg = df_resampled['response_time'][-10:].mean()
            if forecast_value > current_avg * 1.2:
                description = f"Response time projected to increase by {((forecast_value/current_avg)-1)*100:.1f}% in 30 minutes"
            elif forecast_value < current_avg * 0.8:
                description = f"Response time projected to decrease by {(1-(forecast_value/current_avg))*100:.1f}% in 30 minutes"
            else:
                description = "Response time projected to remain stable in the next 30 minutes"
            
            return forecast_value, confidence, prediction_time, description
        
        except Exception as e:
            logger.error(f"Error forecasting response times: {str(e)}")
            return None
    
    def _create_time_features(self, metrics: List[ApiMetric]) -> np.ndarray:
        """
        Create time-based features for anomaly detection.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Numpy array of features.
        """
        features = []
        
        for metric in metrics:
            # Basic features
            response_time = metric.response_time
            hour = metric.timestamp.hour
            day_of_week = metric.timestamp.weekday()
            error = 1 if metric.error else 0
            
            # Additional features
            status_code_group = metric.status_code // 100
            
            # Create feature vector
            feature_vector = [response_time, hour, day_of_week, error, status_code_group]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _update_history(self, endpoint: str, metrics: List[ApiMetric]):
        """
        Update historical data for an endpoint.
        
        Args:
            endpoint: The endpoint.
            metrics: List of API metrics.
        """
        # Initialize history if needed
        if endpoint not in self.history:
            self.history[endpoint] = []
        
        # Add new metrics to history
        self.history[endpoint].extend(metrics)
        
        # Keep only the most recent data points
        max_history = 1000  # Maximum number of historical data points to store
        if len(self.history[endpoint]) > max_history:
            self.history[endpoint] = self.history[endpoint][-max_history:] 