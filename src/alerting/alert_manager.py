"""
Alert manager for API monitoring system.
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

from config.settings import Settings
from src.alerting.alert_generator import AlertGenerator
from src.alerting.channels.slack_notifier import SlackNotifier
from src.alerting.channels.email_notifier import EmailNotifier
from src.storage.database import get_database
from src.models.api import ApiSource, Anomaly, Alert, Environment

logger = logging.getLogger(__name__)

# Create settings instance
settings = Settings()

class AlertManager:
    """
    Manager for generating and sending alerts.
    """
    def __init__(self):
        """
        Initialize the alert manager.
        """
        self.running = False
        self.db = get_database()
        self.alert_tasks = []
        self.alert_generator = AlertGenerator()
        self.notifiers = self._initialize_notifiers()
        self.alert_cache = set()  # Cache for recent alert IDs to avoid duplicates
    
    def _initialize_notifiers(self) -> Dict[str, Any]:
        """
        Initialize notification channels.
        
        Returns:
            Dictionary of notifiers.
        """
        notifiers = {}
        
        # Initialize Slack notifier if webhook URL is configured
        if settings.SLACK_WEBHOOK_URL:
            notifiers['slack'] = SlackNotifier(settings.SLACK_WEBHOOK_URL)
        
        # Initialize email notifier if email is enabled
        if settings.EMAIL_ENABLED:
            notifiers['email'] = EmailNotifier(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USERNAME,
                password=settings.EMAIL_PASSWORD,
                from_address=settings.EMAIL_FROM
            )
        
        return notifiers
    
    async def start_alerting(self):
        """
        Start the alerting process.
        """
        logger.info("Starting alert generation and notification")
        self.running = True
        
        # Start alerting tasks
        alert_task = asyncio.create_task(self._alerting_loop())
        self.alert_tasks.append(alert_task)
    
    async def stop_alerting(self):
        """
        Stop the alerting process.
        """
        logger.info("Stopping alert generation and notification")
        self.running = False
        
        # Cancel all alerting tasks
        for task in self.alert_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.alert_tasks:
            await asyncio.gather(*self.alert_tasks, return_exceptions=True)
        
        self.alert_tasks = []
    
    async def _alerting_loop(self):
        """
        Main alerting loop.
        """
        while self.running:
            try:
                # Check if MongoDB is available
                if not self.db.mongo_available:
                    logger.warning("MongoDB not available, skipping alert processing")
                    await asyncio.sleep(settings.ANOMALY_DETECTION_INTERVAL)
                    continue
                
                # Get recent unprocessed anomalies
                try:
                    anomalies = await self.db.get_unprocessed_anomalies()
                except AttributeError:
                    logger.warning("Database method not available, skipping alert processing")
                    await asyncio.sleep(settings.ANOMALY_DETECTION_INTERVAL)
                    continue
                
                if anomalies:
                    logger.debug(f"Processing {len(anomalies)} new anomalies")
                    
                    # Group anomalies by API and other dimensions
                    grouped_anomalies = self._group_anomalies(anomalies)
                    
                    # Generate alerts from grouped anomalies
                    alerts = self.alert_generator.generate_alerts(grouped_anomalies)
                    
                    if alerts:
                        # Store alerts in database
                        await self.db.store_alerts(alerts)
                        logger.info(f"Generated and stored {len(alerts)} alerts")
                        
                        # Send notifications for high severity alerts
                        await self._send_notifications(alerts)
                        
                        # Mark anomalies as processed
                        anomaly_ids = [anomaly.id for anomaly in anomalies]
                        await self.db.mark_anomalies_processed(anomaly_ids)
                
                # Sleep before next alerting cycle
                await asyncio.sleep(settings.ANOMALY_DETECTION_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Alerting loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in alerting loop: {str(e)}")
                await asyncio.sleep(5)  # Sleep a bit before retrying
    
    def _group_anomalies(self, anomalies: List[Anomaly]) -> Dict[str, List[Anomaly]]:
        """
        Group anomalies by API, type, and other dimensions.
        
        Args:
            anomalies: List of anomalies.
            
        Returns:
            Dictionary of grouped anomalies.
        """
        grouped = {}
        
        for anomaly in anomalies:
            # Group by API ID and anomaly type
            key = f"{anomaly.api_id}:{anomaly.type}"
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(anomaly)
        
        return grouped
    
    async def _send_notifications(self, alerts: List[Alert]):
        """
        Send notifications for alerts.
        
        Args:
            alerts: List of alerts.
        """
        for alert in alerts:
            # Skip if already notified recently
            if alert.id in self.alert_cache:
                continue
            
            # Only send notifications for high and critical severity alerts
            if alert.severity.lower() not in ['high', 'critical']:
                continue
            
            try:
                # Send to all configured notification channels
                for channel, notifier in self.notifiers.items():
                    try:
                        await notifier.send_alert(alert)
                        logger.info(f"Sent alert {alert.id} notification via {channel}")
                    except Exception as e:
                        logger.error(f"Error sending {channel} notification for alert {alert.id}: {str(e)}")
                
                # Add to cache to avoid duplicate notifications
                self.alert_cache.add(alert.id)
                
                # Trim cache if it gets too large
                if len(self.alert_cache) > 1000:
                    self.alert_cache = set(list(self.alert_cache)[-500:])
            
            except Exception as e:
                logger.error(f"Error processing notifications for alert {alert.id}: {str(e)}")
    
    async def resolve_alert(self, alert_id: str, resolved_by: str):
        """
        Resolve an alert.
        
        Args:
            alert_id: The ID of the alert to resolve.
            resolved_by: The user who resolved the alert.
        """
        try:
            # Check if MongoDB is available
            if not self.db.mongo_available:
                logger.warning(f"MongoDB not available, cannot resolve alert {alert_id}")
                return
                
            # Update alert status in database
            await self.db.update_alert_status(
                alert_id=alert_id,
                status="resolved",
                updated_by=resolved_by,
                updated_at=datetime.utcnow()
            )
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            
            # Remove from cache
            if alert_id in self.alert_cache:
                self.alert_cache.remove(alert_id)
        
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {str(e)}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """
        Acknowledge an alert.
        
        Args:
            alert_id: The ID of the alert to acknowledge.
            acknowledged_by: The user who acknowledged the alert.
        """
        try:
            # Check if MongoDB is available
            if not self.db.mongo_available:
                logger.warning(f"MongoDB not available, cannot acknowledge alert {alert_id}")
                return
                
            # Update alert status in database
            await self.db.update_alert_status(
                alert_id=alert_id,
                status="acknowledged",
                updated_by=acknowledged_by,
                updated_at=datetime.utcnow()
            )
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
    
    async def snooze_alert(self, alert_id: str, duration_minutes: int, snoozed_by: str):
        """
        Snooze an alert for a specified duration.
        
        Args:
            alert_id: The ID of the alert to snooze.
            duration_minutes: The duration to snooze the alert for (in minutes).
            snoozed_by: The user who snoozed the alert.
        """
        try:
            # Check if MongoDB is available
            if not self.db.mongo_available:
                logger.warning(f"MongoDB not available, cannot snooze alert {alert_id}")
                return
                
            # Get the alert
            alert = await self.db.get_alert(alert_id)
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return
            
            # Calculate snooze end time
            snooze_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
            
            # Update alert in database
            await self.db.update_alert(
                alert_id=alert_id,
                updates={
                    "status": "snoozed",
                    "updated_by": snoozed_by,
                    "updated_at": datetime.utcnow(),
                    "snooze_until": snooze_until,
                    "metadata": {
                        **(alert.metadata or {}),
                        "snoozed_by": snoozed_by,
                        "snooze_duration_minutes": duration_minutes
                    }
                }
            )
            logger.info(f"Alert {alert_id} snoozed for {duration_minutes} minutes by {snoozed_by}")
            
            # Remove from cache
            if alert_id in self.alert_cache:
                self.alert_cache.remove(alert_id)
        
        except Exception as e:
            logger.error(f"Error snoozing alert {alert_id}: {str(e)}")
    
    async def get_active_alerts(self, api_id: Optional[str] = None, environment: Optional[Environment] = None) -> List[Alert]:
        """
        Get active alerts, optionally filtered by API ID and environment.
        
        Args:
            api_id: Optional API ID to filter by.
            environment: Optional environment to filter by.
            
        Returns:
            List of active alerts.
        """
        try:
            # Check if MongoDB is available
            if not self.db.mongo_available:
                logger.warning("MongoDB not available, cannot get active alerts")
                return []
                
            # Get all open and acknowledged alerts
            alerts = await self.db.get_alerts(
                statuses=["open", "acknowledged"],
                api_id=api_id,
                environment=environment
            )
            
            return alerts
        
        except Exception as e:
            logger.error(f"Error getting active alerts: {str(e)}")
            return [] 