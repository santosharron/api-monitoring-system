"""
Dashboard initializer for Kibana integration.
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any

from src.visualization.kibana_integration import KibanaIntegration

logger = logging.getLogger(__name__)

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
    
    async def initialize_dashboards(self):
        """
        Initialize all default Kibana dashboards.
        """
        try:
            logger.info("Initializing Kibana dashboards...")
            
            # Create index patterns
            await asyncio.to_thread(self.kibana.create_index_pattern, "api-metrics-*")
            await asyncio.to_thread(self.kibana.create_index_pattern, "api-anomalies-*")
            await asyncio.to_thread(self.kibana.create_index_pattern, "api-predictions-*")
            
            # Import dashboards
            dashboard_files = self._get_dashboard_files()
            for dashboard_file in dashboard_files:
                await self._import_dashboard(dashboard_file)
                
            # Create default visualizations
            await self._create_default_visualizations()
            
            logger.info("Kibana dashboards initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Kibana dashboards: {str(e)}")
    
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
            
            # Create visualizations
            await asyncio.to_thread(
                self.kibana.create_visualization,
                "line", 
                "API Response Time Chart",
                "api-metrics-*",
                response_time_vis
            )
            
            await asyncio.to_thread(
                self.kibana.create_visualization,
                "area", 
                "API Error Rate Chart",
                "api-metrics-*",
                error_rate_vis
            )
            
            logger.info("Default visualizations created")
        except Exception as e:
            logger.error(f"Error creating default visualizations: {str(e)}")
            
    def get_dashboard_url(self, dashboard_id: str) -> str:
        """
        Get dashboard URL.
        """
        return self.kibana.get_dashboard_url(dashboard_id) 