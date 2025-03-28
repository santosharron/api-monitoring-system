"""
Slack notification channel for alerts.
"""
import json
import logging
import aiohttp
from typing import Dict, Any

from src.models.api import Alert

logger = logging.getLogger(__name__)

class SlackNotifier:
    """
    Notifier for sending alerts to Slack.
    """
    def __init__(self, webhook_url: str):
        """
        Initialize the Slack notifier.
        
        Args:
            webhook_url: The Slack webhook URL.
        """
        self.webhook_url = webhook_url
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert to Slack.
        
        Args:
            alert: The alert to send.
            
        Returns:
            True if the alert was sent successfully, False otherwise.
        """
        try:
            # Create Slack message
            message = self._format_alert(alert)
            
            # Send message to Slack webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Successfully sent alert {alert.id} to Slack")
                        return True
                    else:
                        logger.error(f"Failed to send alert {alert.id} to Slack. Status: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending alert {alert.id} to Slack: {str(e)}")
            return False
    
    def _format_alert(self, alert: Alert) -> Dict[str, Any]:
        """
        Format an alert as a Slack message.
        
        Args:
            alert: The alert to format.
            
        Returns:
            The formatted Slack message.
        """
        # Determine color based on severity
        color = self._get_severity_color(alert.severity)
        
        # Create message attachments
        attachments = [
            {
                "color": color,
                "title": f"API Alert: {alert.title}",
                "title_link": f"/alerts/{alert.id}",
                "text": alert.description,
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert.severity,
                        "short": True
                    },
                    {
                        "title": "Status",
                        "value": alert.status,
                        "short": True
                    },
                    {
                        "title": "API",
                        "value": alert.api_name,
                        "short": True
                    },
                    {
                        "title": "Environment",
                        "value": alert.environment,
                        "short": True
                    },
                    {
                        "title": "Created At",
                        "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "short": False
                    }
                ],
                "footer": "API Monitoring System",
                "ts": int(alert.created_at.timestamp())
            }
        ]
        
        # Create main message
        message = {
            "text": f"*{alert.severity.upper()} Alert*: {alert.title}",
            "attachments": attachments
        }
        
        return message
    
    def _get_severity_color(self, severity: str) -> str:
        """
        Get the color for the severity level.
        
        Args:
            severity: The severity level.
            
        Returns:
            The color for the severity level.
        """
        severity_colors = {
            "critical": "#FF0000",  # Red
            "high": "#FFA500",      # Orange
            "medium": "#FFFF00",    # Yellow
            "low": "#00FF00"        # Green
        }
        return severity_colors.get(severity.lower(), "#808080")  # Default gray 