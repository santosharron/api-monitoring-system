"""
Cross-environment analyzer for API monitoring system.
This analyzer detects anomalies and makes predictions across different environments.
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from src.analyzers.base_analyzer import BaseAnalyzer
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Environment

logger = logging.getLogger(__name__)

class CrossEnvironmentAnalyzer(BaseAnalyzer):
    """
    Analyzer for detecting anomalies and making predictions across different environments.
    """
    def __init__(self):
        """
        Initialize the cross-environment analyzer.
        """
        super().__init__(None)  # This is a global analyzer, not tied to a specific API
        self.min_data_points = 20  # Minimum number of data points required for analysis
        self.history = {}  # Store historical data for different API-environment combinations
    
    async def detect_anomalies(self, metrics: List[ApiMetric]) -> List[Anomaly]:
        """
        Detect anomalies across different environments.
        
        Args:
            metrics: List of API metrics from all APIs.
            
        Returns:
            List of detected anomalies.
        """
        anomalies = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for cross-environment anomaly detection")
            return anomalies
        
        try:
            # Group metrics by API ID and endpoint
            metrics_by_api = self._group_by_api(metrics)
            
            # Analyze each API separately
            for api_id, api_metrics in metrics_by_api.items():
                # Group by endpoint
                endpoints = self._group_by_endpoint(api_metrics)
                
                for endpoint, endpoint_metrics in endpoints.items():
                    # Check if we have metrics from multiple environments
                    environments = self._get_environments(endpoint_metrics)
                    
                    if len(environments) <= 1:
                        continue  # Need at least two environments to compare
                    
                    # Detect cross-environment anomalies
                    env_anomalies = self._detect_environment_discrepancies(api_id, endpoint, endpoint_metrics, environments)
                    anomalies.extend(env_anomalies)
                    
                    # Detect propagation anomalies (issues spreading across environments)
                    prop_anomalies = self._detect_propagation_patterns(api_id, endpoint, endpoint_metrics, environments)
                    anomalies.extend(prop_anomalies)
                    
                    # Update history
                    self._update_history(api_id, endpoint, endpoint_metrics)
        
        except Exception as e:
            logger.error(f"Error detecting cross-environment anomalies: {str(e)}")
        
        return anomalies
    
    async def predict_issues(self, metrics: List[ApiMetric]) -> List[Prediction]:
        """
        Predict issues across different environments.
        
        Args:
            metrics: List of API metrics from all APIs.
            
        Returns:
            List of predictions.
        """
        predictions = []
        
        if not metrics or len(metrics) < self.min_data_points:
            logger.debug("Not enough data points for cross-environment prediction")
            return predictions
        
        try:
            # Group metrics by API ID and endpoint
            metrics_by_api = self._group_by_api(metrics)
            
            # Analyze each API separately
            for api_id, api_metrics in metrics_by_api.items():
                # Group by endpoint
                endpoints = self._group_by_endpoint(api_metrics)
                
                for endpoint, endpoint_metrics in endpoints.items():
                    # Check if we have metrics from multiple environments
                    environments = self._get_environments(endpoint_metrics)
                    
                    if len(environments) <= 1:
                        continue  # Need at least two environments to compare
                    
                    # Predict cross-environment issues
                    env_predictions = self._predict_environment_issues(api_id, endpoint, endpoint_metrics, environments)
                    predictions.extend(env_predictions)
        
        except Exception as e:
            logger.error(f"Error predicting cross-environment issues: {str(e)}")
        
        return predictions
    
    def _group_by_api(self, metrics: List[ApiMetric]) -> Dict[str, List[ApiMetric]]:
        """
        Group metrics by API ID.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Dictionary mapping API IDs to lists of metrics.
        """
        metrics_by_api = {}
        
        for metric in metrics:
            if metric.api_id not in metrics_by_api:
                metrics_by_api[metric.api_id] = []
            metrics_by_api[metric.api_id].append(metric)
        
        return metrics_by_api
    
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
    
    def _get_environments(self, metrics: List[ApiMetric]) -> Set[Environment]:
        """
        Get unique environments from metrics.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Set of environments.
        """
        return set(metric.environment for metric in metrics)
    
    def _group_by_environment(self, metrics: List[ApiMetric]) -> Dict[Environment, List[ApiMetric]]:
        """
        Group metrics by environment.
        
        Args:
            metrics: List of API metrics.
            
        Returns:
            Dictionary mapping environments to lists of metrics.
        """
        metrics_by_env = {}
        
        for metric in metrics:
            if metric.environment not in metrics_by_env:
                metrics_by_env[metric.environment] = []
            metrics_by_env[metric.environment].append(metric)
        
        # Sort metrics by timestamp for each environment
        for env in metrics_by_env:
            metrics_by_env[env].sort(key=lambda x: x.timestamp)
        
        return metrics_by_env
    
    def _detect_environment_discrepancies(
        self, 
        api_id: str, 
        endpoint: str, 
        metrics: List[ApiMetric],
        environments: Set[Environment]
    ) -> List[Anomaly]:
        """
        Detect discrepancies between environments for the same API/endpoint.
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            metrics: List of API metrics.
            environments: Set of environments.
            
        Returns:
            List of anomalies.
        """
        anomalies = []
        
        # Group metrics by environment
        metrics_by_env = self._group_by_environment(metrics)
        
        # Need at least two environments with enough data points
        viable_envs = [env for env, env_metrics in metrics_by_env.items() 
                      if len(env_metrics) >= self.min_data_points]
        
        if len(viable_envs) < 2:
            return anomalies
        
        # Calculate statistics for each environment
        env_stats = {}
        for env in viable_envs:
            env_metrics = metrics_by_env[env]
            response_times = [m.response_time for m in env_metrics]
            error_rates = self._calculate_error_rate(env_metrics)
            
            env_stats[env] = {
                'mean_response_time': np.mean(response_times),
                'std_response_time': np.std(response_times),
                'error_rate': error_rates,
                'metrics': env_metrics
            }
        
        # Compare environments
        for i, env1 in enumerate(viable_envs):
            for env2 in viable_envs[i+1:]:
                # Check for response time discrepancies
                rt_anomalies = self._check_response_time_discrepancy(
                    api_id, endpoint, env_stats[env1], env_stats[env2], env1, env2
                )
                anomalies.extend(rt_anomalies)
                
                # Check for error rate discrepancies
                er_anomalies = self._check_error_rate_discrepancy(
                    api_id, endpoint, env_stats[env1], env_stats[env2], env1, env2
                )
                anomalies.extend(er_anomalies)
        
        return anomalies
    
    def _check_response_time_discrepancy(
        self,
        api_id: str,
        endpoint: str,
        env1_stats: Dict[str, Any],
        env2_stats: Dict[str, Any],
        env1: Environment,
        env2: Environment
    ) -> List[Anomaly]:
        """
        Check for response time discrepancies between environments.
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            env1_stats: Statistics for environment 1.
            env2_stats: Statistics for environment 2.
            env1: Environment 1.
            env2: Environment 2.
            
        Returns:
            List of anomalies.
        """
        anomalies = []
        
        rt1 = env1_stats['mean_response_time']
        rt2 = env2_stats['mean_response_time']
        std1 = env1_stats['std_response_time']
        std2 = env2_stats['std_response_time']
        
        # Calculate the difference relative to the average response time
        avg_rt = (rt1 + rt2) / 2
        relative_diff = abs(rt1 - rt2) / avg_rt
        
        # Check if the difference is significant
        if relative_diff > 0.3:  # 30% difference threshold
            # Calculate severity based on the relative difference
            severity = min(1.0, relative_diff)
            
            # Determine which environment is slower
            slower_env = env1 if rt1 > rt2 else env2
            faster_env = env2 if rt1 > rt2 else env1
            slower_rt = max(rt1, rt2)
            faster_rt = min(rt1, rt2)
            
            # Create anomaly
            anomaly = self.create_anomaly(
                api_id=api_id,
                anomaly_type="cross_environment_response_time",
                severity=severity,
                description=f"Response time discrepancy between {slower_env.value} and {faster_env.value} environments for {endpoint}",
                metric_value=slower_rt,
                expected_value=faster_rt,
                threshold=faster_rt * 1.3,  # 30% above the faster environment
                environment=slower_env,
                context={
                    "endpoint": endpoint,
                    "comparison_environment": faster_env.value,
                    "relative_difference": f"{relative_diff:.2f}",
                    "slower_environment_rt": f"{slower_rt:.2f}ms",
                    "faster_environment_rt": f"{faster_rt:.2f}ms"
                }
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _check_error_rate_discrepancy(
        self,
        api_id: str,
        endpoint: str,
        env1_stats: Dict[str, Any],
        env2_stats: Dict[str, Any],
        env1: Environment,
        env2: Environment
    ) -> List[Anomaly]:
        """
        Check for error rate discrepancies between environments.
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            env1_stats: Statistics for environment 1.
            env2_stats: Statistics for environment 2.
            env1: Environment 1.
            env2: Environment 2.
            
        Returns:
            List of anomalies.
        """
        anomalies = []
        
        er1 = env1_stats['error_rate']
        er2 = env2_stats['error_rate']
        
        # Check if one environment has significantly higher error rate
        if er1 > 0.05 and er1 > (er2 * 2):  # Environment 1 has >5% error rate and 2x higher than env2
            # Calculate severity
            severity = min(1.0, er1)
            
            # Create anomaly
            anomaly = self.create_anomaly(
                api_id=api_id,
                anomaly_type="cross_environment_error_rate",
                severity=severity,
                description=f"Higher error rate in {env1.value} compared to {env2.value} for {endpoint}",
                metric_value=er1,
                expected_value=er2,
                threshold=max(0.05, er2 * 2),  # Threshold is either 5% or double the comparison environment
                environment=env1,
                context={
                    "endpoint": endpoint,
                    "comparison_environment": env2.value,
                    "high_error_rate": f"{er1:.2%}",
                    "comparison_error_rate": f"{er2:.2%}"
                }
            )
            
            anomalies.append(anomaly)
        
        elif er2 > 0.05 and er2 > (er1 * 2):  # Environment 2 has >5% error rate and 2x higher than env1
            # Calculate severity
            severity = min(1.0, er2)
            
            # Create anomaly
            anomaly = self.create_anomaly(
                api_id=api_id,
                anomaly_type="cross_environment_error_rate",
                severity=severity,
                description=f"Higher error rate in {env2.value} compared to {env1.value} for {endpoint}",
                metric_value=er2,
                expected_value=er1,
                threshold=max(0.05, er1 * 2),  # Threshold is either 5% or double the comparison environment
                environment=env2,
                context={
                    "endpoint": endpoint,
                    "comparison_environment": env1.value,
                    "high_error_rate": f"{er2:.2%}",
                    "comparison_error_rate": f"{er1:.2%}"
                }
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_propagation_patterns(
        self, 
        api_id: str, 
        endpoint: str, 
        metrics: List[ApiMetric],
        environments: Set[Environment]
    ) -> List[Anomaly]:
        """
        Detect propagation patterns (issues that spread from one environment to another).
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            metrics: List of API metrics.
            environments: Set of environments.
            
        Returns:
            List of anomalies.
        """
        anomalies = []
        
        # Check if we have historical data
        history_key = f"{api_id}:{endpoint}"
        if history_key not in self.history:
            return anomalies
        
        # Group metrics by environment
        metrics_by_env = self._group_by_environment(metrics)
        
        # Group historical metrics by environment
        historical_metrics = self.history[history_key]
        historical_by_env = self._group_by_environment(historical_metrics)
        
        # Time window for recent metrics (last hour)
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        # Check for changes in each environment
        env_changes = {}
        for env in environments:
            if env not in metrics_by_env or env not in historical_by_env:
                continue
                
            recent_metrics = [m for m in metrics_by_env[env] if m.timestamp >= recent_time]
            if not recent_metrics:
                continue
                
            # Calculate error rates
            historical_error_rate = self._calculate_error_rate(historical_by_env[env])
            recent_error_rate = self._calculate_error_rate(recent_metrics)
            
            # Calculate response time changes
            historical_rt = np.mean([m.response_time for m in historical_by_env[env]])
            recent_rt = np.mean([m.response_time for m in recent_metrics])
            
            # Record significant changes
            significant_change = False
            change_type = []
            
            if recent_error_rate > (historical_error_rate * 2) and recent_error_rate > 0.05:
                significant_change = True
                change_type.append("error_rate")
            
            if recent_rt > (historical_rt * 1.5):
                significant_change = True
                change_type.append("response_time")
            
            if significant_change:
                env_changes[env] = {
                    "change_type": change_type,
                    "timestamp": recent_metrics[0].timestamp,  # First timestamp of the recent change
                    "error_rate": recent_error_rate,
                    "response_time": recent_rt
                }
        
        # If we have changes in multiple environments, check for propagation patterns
        if len(env_changes) >= 2:
            # Sort environments by timestamp of change
            sorted_envs = sorted(env_changes.keys(), key=lambda e: env_changes[e]["timestamp"])
            
            # Check for sequential changes (within 30 minutes)
            for i in range(len(sorted_envs) - 1):
                env1 = sorted_envs[i]
                env2 = sorted_envs[i + 1]
                
                time_diff = (env_changes[env2]["timestamp"] - env_changes[env1]["timestamp"]).total_seconds()
                if time_diff <= 1800:  # 30 minutes
                    # Check if the same types of changes occurred
                    common_changes = set(env_changes[env1]["change_type"]) & set(env_changes[env2]["change_type"])
                    
                    if common_changes:
                        # Create propagation anomaly
                        change_str = " and ".join(common_changes)
                        anomaly = self.create_anomaly(
                            api_id=api_id,
                            anomaly_type="cross_environment_propagation",
                            severity=0.8,  # High severity for propagation patterns
                            description=f"{change_str.replace('_', ' ').title()} issue propagating from {env1.value} to {env2.value} for {endpoint}",
                            metric_value=env_changes[env2]["response_time"] if "response_time" in common_changes else env_changes[env2]["error_rate"],
                            expected_value=None,
                            threshold=None,
                            environment=env2,
                            context={
                                "endpoint": endpoint,
                                "source_environment": env1.value,
                                "propagation_time_seconds": time_diff,
                                "change_type": list(common_changes),
                                "source_timestamp": env_changes[env1]["timestamp"].isoformat(),
                                "target_timestamp": env_changes[env2]["timestamp"].isoformat()
                            }
                        )
                        
                        anomalies.append(anomaly)
        
        return anomalies
    
    def _predict_environment_issues(
        self, 
        api_id: str, 
        endpoint: str, 
        metrics: List[ApiMetric],
        environments: Set[Environment]
    ) -> List[Prediction]:
        """
        Predict issues that may propagate across environments.
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            metrics: List of API metrics.
            environments: Set of environments.
            
        Returns:
            List of predictions.
        """
        predictions = []
        
        # Group metrics by environment
        metrics_by_env = self._group_by_environment(metrics)
        
        # Need at least two environments with enough data points
        viable_envs = [env for env, env_metrics in metrics_by_env.items() 
                      if len(env_metrics) >= self.min_data_points]
        
        if len(viable_envs) < 2:
            return predictions
        
        # Identify environments with recent issues
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        problem_envs = []
        
        for env in viable_envs:
            env_metrics = metrics_by_env[env]
            recent_metrics = [m for m in env_metrics if m.timestamp >= recent_time]
            
            if not recent_metrics:
                continue
            
            # Check for recent issues
            has_issues = False
            issue_type = []
            
            # Check error rates
            recent_error_rate = self._calculate_error_rate(recent_metrics)
            if recent_error_rate > 0.1:  # 10% error rate threshold
                has_issues = True
                issue_type.append("error_rate")
            
            # Check response times
            recent_rt = [m.response_time for m in recent_metrics]
            all_rt = [m.response_time for m in env_metrics]
            
            if np.mean(recent_rt) > (np.mean(all_rt) * 1.5):
                has_issues = True
                issue_type.append("response_time")
            
            if has_issues:
                problem_envs.append((env, issue_type))
        
        # If we found problematic environments, predict propagation to other environments
        if problem_envs:
            # Use the deployment/release flow to predict propagation
            # This is a simplified approach: on-prem -> cloud -> multi-cloud
            env_order = {
                Environment.ON_PREMISES: 1,
                Environment.AWS: 2,
                Environment.AZURE: 2,
                Environment.GCP: 2,
                Environment.OTHER: 3
            }
            
            for problem_env, issue_types in problem_envs:
                # Predict propagation to higher order environments
                problem_order = env_order.get(problem_env, 0)
                
                for target_env in viable_envs:
                    if target_env == problem_env:
                        continue
                    
                    target_order = env_order.get(target_env, 0)
                    
                    # Only predict propagation to higher order environments
                    if target_order <= problem_order:
                        continue
                    
                    # Calculate prediction confidence based on order difference
                    order_diff = target_order - problem_order
                    confidence = max(0.6, 1.0 - (order_diff * 0.1))
                    
                    # Predict propagation within the next hour
                    prediction_time = datetime.utcnow() + timedelta(minutes=30)
                    
                    for issue_type in issue_types:
                        if issue_type == "error_rate":
                            # Get current error rate in the problematic environment
                            problem_error_rate = self._calculate_error_rate(metrics_by_env[problem_env])
                            
                            prediction = self.create_prediction(
                                api_id=api_id,
                                prediction_type="cross_environment_error_propagation",
                                confidence=confidence,
                                predicted_for=prediction_time,
                                description=f"Error rate increase likely to propagate from {problem_env.value} to {target_env.value} for {endpoint}",
                                metric_value=problem_error_rate,
                                current_value=self._calculate_error_rate(metrics_by_env[target_env]),
                                trend="increasing",
                                environment=target_env,
                                context={
                                    "endpoint": endpoint,
                                    "source_environment": problem_env.value,
                                    "current_source_error_rate": f"{problem_error_rate:.2%}",
                                    "prediction_basis": "Recent error rate increase in source environment"
                                }
                            )
                            
                            predictions.append(prediction)
                        
                        elif issue_type == "response_time":
                            # Get current response time in the problematic environment
                            problem_rt = np.mean([m.response_time for m in metrics_by_env[problem_env]])
                            
                            prediction = self.create_prediction(
                                api_id=api_id,
                                prediction_type="cross_environment_response_time_propagation",
                                confidence=confidence,
                                predicted_for=prediction_time,
                                description=f"Response time increase likely to propagate from {problem_env.value} to {target_env.value} for {endpoint}",
                                metric_value=problem_rt,
                                current_value=np.mean([m.response_time for m in metrics_by_env[target_env]]),
                                trend="increasing",
                                environment=target_env,
                                context={
                                    "endpoint": endpoint,
                                    "source_environment": problem_env.value,
                                    "current_source_response_time": f"{problem_rt:.2f}ms",
                                    "prediction_basis": "Recent response time increase in source environment"
                                }
                            )
                            
                            predictions.append(prediction)
        
        return predictions
    
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
    
    def _update_history(self, api_id: str, endpoint: str, metrics: List[ApiMetric]):
        """
        Update historical data for an API endpoint.
        
        Args:
            api_id: The API ID.
            endpoint: The endpoint.
            metrics: List of API metrics.
        """
        history_key = f"{api_id}:{endpoint}"
        
        # Initialize history if needed
        if history_key not in self.history:
            self.history[history_key] = []
        
        # Add new metrics to history
        self.history[history_key].extend(metrics)
        
        # Keep only the most recent data points
        max_history = 1000  # Maximum number of historical data points to store
        if len(self.history[history_key]) > max_history:
            self.history[history_key] = self.history[history_key][-max_history:] 