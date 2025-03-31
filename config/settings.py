"""
Configuration settings for API Monitoring System.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union

class Settings:
    """
    Application settings without pydantic.
    """
    def __init__(self):
        # Application settings
        self.DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.CLOUD_DEPLOYMENT = os.getenv("CLOUD_DEPLOYMENT", "False").lower() in ("true", "1", "t")
        
        # CORS settings
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        
        # Database settings
        self.MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/api_monitoring")
        self.ELASTICSEARCH_HOSTS = os.getenv("ELASTICSEARCH_HOSTS", "https://aa1685245a834737a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:443").split(",")
        self.ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", None)
        self.ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", None)
        self.ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", None)
        self.ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY", None)
        self.KIBANA_URL = os.getenv("KIBANA_URL", None)
        
        # Data collection settings
        self.COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "60"))  # seconds
        
        # Anomaly detection settings
        self.ANOMALY_DETECTION_INTERVAL = int(os.getenv("ANOMALY_DETECTION_INTERVAL", "300"))  # seconds
        self.ANOMALY_DETECTION_WINDOW = int(os.getenv("ANOMALY_DETECTION_WINDOW", "3600"))  # seconds
        
        # Alerting settings
        self.SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", None)
        
        # Email settings
        self.EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() in ("true", "1", "t")
        self.EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        self.EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
        self.EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
        self.EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
        self.EMAIL_FROM = os.getenv("EMAIL_FROM", "alerts@apimonitoring.com")
        
        # Redis for caching and pub/sub
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
        
        # OpenTelemetry settings
        self.OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        
        # AWS settings
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        
        # Environment-specific settings
        self.ENVIRONMENTS = os.getenv("ENVIRONMENTS", "on-premises,aws,azure,gcp").split(",")
        
        # System resource settings
        self.COLLECTOR_THREADS = int(os.getenv("COLLECTOR_THREADS", "5"))
        self.ANALYZER_THREADS = int(os.getenv("ANALYZER_THREADS", "3"))

# Create settings instance
settings = Settings()

# Configure logging based on settings
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) 