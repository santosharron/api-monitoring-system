"""
Dashboard initializer for Kibana integration.
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from functools import wraps

from src.visualization.kibana_integration import KibanaIntegration

logger = logging.getLogger(__name__)

# Timeout decorator for async functions
def async_timeout(timeout_sec):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_sec)
            except asyncio.TimeoutError:
                logger.warning(f"Function {func.__name__} timed out after {timeout_sec} seconds")
                return None
        return wrapper
    return decorator

class DashboardInitializer:
    """
    Initializes and manages Kibana dashboards.
    """
    def __init__(self):
        """
        Initialize the dashboard initializer.
        """
        self.kibana = KibanaIntegration()
        self.dashboards_dir = os.path.join(os.path.dirname(__file__), "dashboards")
        self.is_available = self._check_kibana_available()
    
    def _check_kibana_available(self) -> bool:
        """
        Check if Kibana is available by checking if cloud settings are provided.
        """
        from config.settings import settings
        if settings.ELASTICSEARCH_CLOUD_ID and settings.ELASTICSEARCH_API_KEY:
            logger.info("Kibana cloud configuration detected")
            return True
        elif settings.KIBANA_URL:
            logger.info(f"Kibana URL configured: {settings.KIBANA_URL}")
            return True
        else:
            logger.warning("Kibana configuration not found. Dashboards will be disabled.")
            return False
    
    @async_timeout(30)  # 30 second timeout for entire initialization
    async def initialize_dashboards(self):
        """
        Initialize all default Kibana dashboards.
        """
        if not self.is_available:
            logger.info("Skipping Kibana dashboard initialization - Kibana not configured")
            return
            
        try:
            logger.info("Initializing Kibana dashboards...")
            
            # Create index patterns with individual timeouts
            await self._create_index_pattern_with_timeout("api-metrics-*")
            await self._create_index_pattern_with_timeout("api-anomalies-*")
            await self._create_index_pattern_with_timeout("api-predictions-*")
            
            # Import dashboards
            dashboard_files = self._get_dashboard_files()
            import_tasks = [self._import_dashboard_with_timeout(file) for file in dashboard_files]
            # Run dashboard imports concurrently to speed up initialization
            await asyncio.gather(*import_tasks, return_exceptions=True)
                
            # Create default visualizations
            await self._create_default_visualizations()
            
            logger.info("Kibana dashboards initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Kibana dashboards: {str(e)}")
    
    @async_timeout(5)  # 5 second timeout for index pattern creation
    async def _create_index_pattern_with_timeout(self, pattern: str) -> Optional[bool]:
        """
        Create an index pattern with timeout.
        """
        try:
            return await asyncio.to_thread(self.kibana.create_index_pattern, pattern)
        except Exception as e:
            logger.error(f"Error creating index pattern {pattern}: {str(e)}")
            return None
    
    def _get_dashboard_files(self) -> List[str]:
        """
        Get dashboard files from the dashboards directory.
        """
        dashboard_files = []
        try:
            if os.path.exists(self.dashboards_dir):
                for file in os.listdir(self.dashboards_dir):
                    if file.endswith(".json"):
                        dashboard_files.append(os.path.join(self.dashboards_dir, file))
        except Exception as e:
            logger.error(f"Error getting dashboard files: {str(e)}")
        
        return dashboard_files
    
    @async_timeout(5)  # 5 second timeout for dashboard import
    async def _import_dashboard_with_timeout(self, dashboard_file: str) -> Optional[bool]:
        """
        Import a dashboard from a file with timeout.
        """
        return await self._import_dashboard(dashboard_file)
    
    async def _import_dashboard(self, dashboard_file: str) -> bool:
        """
        Import a dashboard from a file.
        """
        try:
            with open(dashboard_file, "r") as f:
                dashboard_json = json.load(f)
            
            result = await asyncio.to_thread(self.kibana.import_dashboard, dashboard_json)
            
            if result:
                logger.info(f"Imported dashboard from {dashboard_file}")
            else:
                logger.warning(f"Failed to import dashboard from {dashboard_file}")
                
            return result
        except Exception as e:
            logger.error(f"Error importing dashboard from {dashboard_file}: {str(e)}")
            return False
    
    async def _create_default_visualizations(self):
        """
        Create default visualizations for dashboards.
        """
        try:
            # Response Time Line Chart
            response_time_vis = {
                "title": "API Response Time",
                "type": "line",
                "params": {
                    "type": "line",
                    "addTooltip": True,
                    "addLegend": True,
                    "legendPosition": "right",
                    "times": [],
                    "addTimeMarker": False
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "avg",
                        "schema": "metric",
                        "params": {
                            "field": "response_time"
                        }
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "date_histogram",
                        "schema": "segment",
                        "params": {
                            "field": "timestamp",
                            "timeRange": {"from": "now-24h", "to": "now"},
                            "useNormalizedEsInterval": True,
                            "interval": "auto"
                        }
                    },
                    {
                        "id": "3",
                        "enabled": True,
                        "type": "terms",
                        "schema": "group",
                        "params": {
                            "field": "environment",
                            "size": 10,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }
            
            # Error Rate Chart
            error_rate_vis = {
                "title": "API Error Rate",
                "type": "area",
                "params": {
                    "type": "area",
                    "addTooltip": True,
                    "addLegend": True,
                    "legendPosition": "right",
                    "times": [],
                    "addTimeMarker": False
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "avg",
                        "schema": "metric",
                        "params": {
                            "field": "error_rate"
                        }
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "date_histogram",
                        "schema": "segment",
                        "params": {
                            "field": "timestamp",
                            "timeRange": {"from": "now-24h", "to": "now"},
                            "useNormalizedEsInterval": True,
                            "interval": "auto"
                        }
                    },
                    {
                        "id": "3",
                        "enabled": True,
                        "type": "terms",
                        "schema": "group",
                        "params": {
                            "field": "environment",
                            "size": 10,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }
            
            # Create visualizations with timeouts
            await self._create_visualization_with_timeout("api-response-time-chart", "line", "API Response Time Chart", "api-metrics-*", response_time_vis)
            await self._create_visualization_with_timeout("api-error-rate-chart", "area", "API Error Rate Chart", "api-metrics-*", error_rate_vis)
            
            logger.info("Default visualizations created")
        except Exception as e:
            logger.error(f"Error creating default visualizations: {str(e)}")

    @async_timeout(5)  # 5 second timeout for visualization creation
    async def _create_visualization_with_timeout(self, vis_id: str, vis_type: str, title: str, index_pattern: str, vis_data: Dict) -> Optional[bool]:
        """
        Create a visualization with timeout.
        """
        try:
            return await asyncio.to_thread(self.kibana.create_visualization, vis_id, vis_type, title, index_pattern, vis_data)
        except Exception as e:
            logger.error(f"Error creating visualization {title}: {str(e)}")
            return None
            
    def get_dashboard_url(self, dashboard_id: str) -> str:
        """
        Get dashboard URL.
        """
        if not self.is_available:
            return "#kibana-not-available"
            
        return self.kibana.get_dashboard_url(dashboard_id) 