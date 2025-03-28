"""
Alert generator for API monitoring system.
"""
import logging
import uuid
from typing import Dict, List, Set
from datetime import datetime

from src.models.api import Anomaly, Alert, Environment

logger = logging.getLogger(__name__)

class AlertGenerator:
    """
    Generator for creating alerts from anomalies.
    """
    def __init__(self):
        """
        Initialize the alert generator.
        """
        self.severity_thresholds = {
            "critical": 0.9,   # Anomalies with severity >= 0.9 are critical
            "high": 0.7,       # Anomalies with severity >= 0.7 are high
            "medium": 0.4,     # Anomalies with severity >= 0.4 are medium
            "low": 0.0         # All other anomalies are low
        }
    
    def generate_alerts(self, grouped_anomalies: Dict[str, List[Anomaly]]) -> List[Alert]:
        """
        Generate alerts from grouped anomalies.
        
        Args:
            grouped_anomalies: Dictionary of grouped anomalies.
            
        Returns:
            List of generated alerts.
        """
        alerts = []
        
        for group_key, anomalies in grouped_anomalies.items():
            if not anomalies:
                continue
                
            # Generate alert for this group
            alert = self._create_alert_from_group(group_key, anomalies)
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _create_alert_from_group(self, group_key: str, anomalies: List[Anomaly]) -> Alert:
        """
        Create an alert from a group of anomalies.
        
        Args:
            group_key: The group key.
            anomalies: List of anomalies in the group.
            
        Returns:
            Generated alert.
        """
        if not anomalies:
            return None
        
        # Extract API ID and anomaly type from the group key
        api_id, anomaly_type = group_key.split(":", 1)
        
        # Calculate max severity across all anomalies
        max_severity = max(anomaly.severity for anomaly in anomalies)
        
        # Determine alert severity
        alert_severity = self._get_alert_severity(max_severity)
        
        # Get unique environments affected
        environments = self._get_affected_environments(anomalies)
        
        # Create alert title and description
        title, description = self._generate_alert_text(anomalies, anomaly_type, environments)
        
        # Create alert
        alert = Alert(
            id=f"alert-{uuid.uuid4()}",
            title=title,
            description=description,
            severity=alert_severity,
            created_at=datetime.utcnow(),
            status="open",
            anomalies=[anomaly.id for anomaly in anomalies],
            apis=[api_id],
            environments=list(environments),
            tags=self._generate_tags(anomalies, anomaly_type),
            metadata=self._generate_metadata(anomalies)
        )
        
        return alert
    
    def _get_alert_severity(self, max_anomaly_severity: float) -> str:
        """
        Determine alert severity based on the maximum anomaly severity.
        
        Args:
            max_anomaly_severity: Maximum severity across all anomalies.
            
        Returns:
            Alert severity (critical, high, medium, low).
        """
        if max_anomaly_severity >= self.severity_thresholds["critical"]:
            return "critical"
        elif max_anomaly_severity >= self.severity_thresholds["high"]:
            return "high"
        elif max_anomaly_severity >= self.severity_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def _get_affected_environments(self, anomalies: List[Anomaly]) -> Set[Environment]:
        """
        Get unique environments affected by anomalies.
        
        Args:
            anomalies: List of anomalies.
            
        Returns:
            Set of affected environments.
        """
        return {anomaly.environment for anomaly in anomalies if anomaly.environment}
    
    def _generate_alert_text(self, anomalies: List[Anomaly], anomaly_type: str, environments: Set[Environment]) -> tuple:
        """
        Generate alert title and description.
        
        Args:
            anomalies: List of anomalies.
            anomaly_type: Type of anomalies.
            environments: Set of affected environments.
            
        Returns:
            Tuple of (title, description).
        """
        # First anomaly for reference
        first_anomaly = anomalies[0]
        
        # Readable anomaly type
        readable_type = anomaly_type.replace("_", " ").title()
        
        # Environment string
        env_str = ", ".join(env.value for env in environments)
        
        # Get API details (would come from database in a real implementation)
        api_name = f"API {first_anomaly.api_id}"  # Placeholder
        
        # Generate title
        if len(anomalies) == 1:
            title = f"{readable_type} Anomaly Detected in {api_name}"
        else:
            title = f"Multiple {readable_type} Anomalies Detected in {api_name}"
        
        # Include environments in title if there are multiple
        if len(environments) == 1:
            title += f" ({next(iter(environments)).value})"
        elif len(environments) > 1:
            title += f" (Multiple Environments)"
        
        # Generate description
        if len(anomalies) == 1:
            description = first_anomaly.description
            
            # Add additional context
            if first_anomaly.expected_value is not None and first_anomaly.metric_value is not None:
                description += f" Current value: {first_anomaly.metric_value:.2f}, Expected: {first_anomaly.expected_value:.2f}."
            
            if first_anomaly.threshold is not None:
                description += f" Threshold: {first_anomaly.threshold:.2f}."
            
            # Add environment info
            description += f" Environment: {first_anomaly.environment.value}."
            
        else:
            description = f"{len(anomalies)} {readable_type.lower()} anomalies detected in {api_name}."
            
            # Add environment info
            if len(environments) == 1:
                description += f" Environment: {next(iter(environments)).value}."
            else:
                description += f" Environments affected: {env_str}."
            
            # Add severity info
            max_severity = max(anomaly.severity for anomaly in anomalies)
            avg_severity = sum(anomaly.severity for anomaly in anomalies) / len(anomalies)
            description += f" Max severity: {max_severity:.2f}, Average severity: {avg_severity:.2f}."
        
        return title, description
    
    def _generate_tags(self, anomalies: List[Anomaly], anomaly_type: str) -> List[str]:
        """
        Generate tags for the alert.
        
        Args:
            anomalies: List of anomalies.
            anomaly_type: Type of anomalies.
            
        Returns:
            List of tags.
        """
        tags = [anomaly_type]
        
        # Add environment tags
        environments = self._get_affected_environments(anomalies)
        for env in environments:
            tags.append(f"env:{env.value}")
        
        # Add endpoint tags if they exist in context
        endpoints = set()
        for anomaly in anomalies:
            if anomaly.context and "endpoint" in anomaly.context:
                endpoints.add(anomaly.context["endpoint"])
        
        for endpoint in endpoints:
            # Simplify endpoint path for tagging
            simplified = endpoint.split("/")[-1] if "/" in endpoint else endpoint
            if simplified:
                tags.append(f"endpoint:{simplified}")
        
        return tags
    
    def _generate_metadata(self, anomalies: List[Anomaly]) -> Dict:
        """
        Generate metadata for the alert.
        
        Args:
            anomalies: List of anomalies.
            
        Returns:
            Metadata dictionary.
        """
        metadata = {
            "anomaly_count": len(anomalies),
            "timestamps": [anomaly.timestamp.isoformat() for anomaly in anomalies],
            "severities": [anomaly.severity for anomaly in anomalies],
            "avg_severity": sum(anomaly.severity for anomaly in anomalies) / len(anomalies)
        }
        
        # Add endpoint information if available
        endpoints = {}
        for anomaly in anomalies:
            if anomaly.context and "endpoint" in anomaly.context:
                endpoint = anomaly.context["endpoint"]
                method = anomaly.context.get("method", "UNKNOWN")
                key = f"{method}:{endpoint}"
                
                if key not in endpoints:
                    endpoints[key] = 0
                endpoints[key] += 1
        
        if endpoints:
            metadata["affected_endpoints"] = endpoints
        
        return metadata 