"""
Email notification channel for alerts.
"""
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any

from src.models.api import Alert

logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Notifier for sending alerts via email.
    """
    def __init__(
        self, 
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        recipients: Optional[List[str]] = None
    ):
        """
        Initialize the email notifier.
        
        Args:
            host: SMTP server host.
            port: SMTP server port.
            username: SMTP username.
            password: SMTP password.
            from_address: Email from address.
            recipients: List of default recipients (optional).
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.recipients = recipients or []
    
    async def send_alert(self, alert: Alert, recipients: Optional[List[str]] = None) -> bool:
        """
        Send an alert email.
        
        Args:
            alert: The alert to send.
            recipients: Optional list of recipients, uses default if None.
            
        Returns:
            True if the alert was sent successfully, False otherwise.
        """
        try:
            # Use provided recipients or default recipients
            to_addresses = recipients or self.recipients
            
            if not to_addresses:
                logger.warning(f"No recipients for alert {alert.id}, email not sent")
                return False
            
            # Create email message
            subject = f"{alert.severity.upper()} Alert: {alert.title}"
            html_body, text_body = self._format_alert(alert)
            
            # Run the SMTP operations in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._send_email,
                to_addresses,
                subject,
                text_body,
                html_body
            )
            
            if result:
                logger.info(f"Successfully sent alert {alert.id} via email to {', '.join(to_addresses)}")
            else:
                logger.error(f"Failed to send alert {alert.id} via email")
            
            return result
                        
        except Exception as e:
            logger.error(f"Error sending alert {alert.id} via email: {str(e)}")
            return False
    
    def _send_email(
        self, 
        to_addresses: List[str],
        subject: str,
        text_body: str,
        html_body: str
    ) -> bool:
        """
        Send an email using the SMTP server.
        
        Args:
            to_addresses: List of recipient addresses.
            subject: Email subject.
            text_body: Plain text email body.
            html_body: HTML email body.
            
        Returns:
            True if the email was sent successfully, False otherwise.
        """
        try:
            # Create multipart message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = ", ".join(to_addresses)
            
            # Add text and HTML parts
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in SMTP operation: {str(e)}")
            return False
    
    def _format_alert(self, alert: Alert) -> tuple[str, str]:
        """
        Format an alert as email content.
        
        Args:
            alert: The alert to format.
            
        Returns:
            Tuple of (html_body, text_body).
        """
        # Format HTML body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f8f9fa; padding: 10px; }}
                .alert-critical {{ color: #721c24; background-color: #f8d7da; }}
                .alert-high {{ color: #856404; background-color: #fff3cd; }}
                .alert-medium {{ color: #0c5460; background-color: #d1ecf1; }}
                .alert-low {{ color: #155724; background-color: #d4edda; }}
                .content {{ padding: 15px; }}
                .footer {{ font-size: 12px; color: #6c757d; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>API Monitoring System Alert</h2>
            </div>
            <div class="content alert-{alert.severity.lower()}">
                <h3>{alert.title}</h3>
                <p><strong>Alert ID:</strong> {alert.id}</p>
                <p><strong>Severity:</strong> {alert.severity}</p>
                <p><strong>Status:</strong> {alert.status}</p>
                <p><strong>API:</strong> {alert.api_name}</p>
                <p><strong>Environment:</strong> {alert.environment}</p>
                <p><strong>Created At:</strong> {alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                <p><strong>Description:</strong><br>{alert.description}</p>
            </div>
            <div class="footer">
                This is an automated alert from the API Monitoring System.
            </div>
        </body>
        </html>
        """
        
        # Format plain text body
        text_body = f"""
        API Monitoring System Alert
        
        {alert.title}
        
        Alert ID: {alert.id}
        Severity: {alert.severity}
        Status: {alert.status}
        API: {alert.api_name}
        Environment: {alert.environment}
        Created At: {alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
        
        Description:
        {alert.description}
        
        This is an automated alert from the API Monitoring System.
        """
        
        return html_body, text_body 