"""
Kibana dashboard and visualization management for API Monitoring System.
"""
import json
import logging
import requests
from typing import Dict, Any, List, Optional

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()

class KibanaIntegration:
    """
    Manages Kibana dashboards and visualizations.
    """
    def __init__(self):
        """
        Initialize Kibana integration.
        """
        self.kibana_url = self._get_kibana_url()
        self.headers = {
            "Content-Type": "application/json",
            "kbn-xsrf": "true"
        }
        
        # Add authentication if provided
        if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
            from requests.auth import HTTPBasicAuth
            self.auth = HTTPBasicAuth(settings.ELASTICSEARCH_USERNAME, 
                                      settings.ELASTICSEARCH_PASSWORD)
        else:
            self.auth = None
    
    def _get_kibana_url(self) -> str:
        """
        Get Kibana URL from Elasticsearch URL.
        """
        es_url = settings.ELASTICSEARCH_HOSTS[0]
        return es_url.replace(":9200", ":5601")
    
    def create_index_pattern(self, pattern: str, time_field: str = "timestamp") -> bool:
        """
        Create an index pattern in Kibana.
        """
        try:
            url = f"{self.kibana_url}/api/saved_objects/index-pattern/{pattern}"
            
            data = {
                "attributes": {
                    "title": pattern,
                    "timeFieldName": time_field
                }
            }
            
            response = requests.post(
                url, 
                headers=self.headers,
                auth=self.auth,
                json=data
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created index pattern: {pattern}")
                return True
            else:
                logger.error(f"Failed to create index pattern: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating index pattern: {str(e)}")
            return False
    
    def import_dashboard(self, dashboard_json: Dict[str, Any]) -> bool:
        """
        Import a dashboard into Kibana.
        """
        try:
            url = f"{self.kibana_url}/api/kibana/dashboards/import"
            
            response = requests.post(
                url, 
                headers=self.headers,
                auth=self.auth,
                json=dashboard_json
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Imported dashboard: {dashboard_json.get('title', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to import dashboard: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error importing dashboard: {str(e)}")
            return False
    
    def create_visualization(self, vis_type: str, title: str, index_pattern: str, 
                             vis_state: Dict[str, Any]) -> bool:
        """
        Create a visualization in Kibana.
        """
        try:
            url = f"{self.kibana_url}/api/saved_objects/visualization/{title.lower().replace(' ', '-')}"
            
            data = {
                "attributes": {
                    "title": title,
                    "visState": json.dumps(vis_state),
                    "uiStateJSON": "{}",
                    "description": "",
                    "version": 1,
                    "kibanaSavedObjectMeta": {
                        "searchSourceJSON": json.dumps({
                            "index": index_pattern,
                            "filter": [],
                            "query": {"query": "", "language": "kuery"}
                        })
                    }
                }
            }
            
            response = requests.post(
                url, 
                headers=self.headers,
                auth=self.auth,
                json=data
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created visualization: {title}")
                return True
            else:
                logger.error(f"Failed to create visualization: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            return False
            
    def get_dashboard_url(self, dashboard_id: str) -> str:
        """
        Get URL for a dashboard.
        """
        return f"{self.kibana_url}/app/kibana#/dashboard/{dashboard_id}" 