"""
Kibana dashboard and visualization management for API Monitoring System.
"""
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from requests.exceptions import RequestException, Timeout

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
        if settings.ELASTICSEARCH_API_KEY:
            self.headers["Authorization"] = f"ApiKey {settings.ELASTICSEARCH_API_KEY}"
            self.auth = None
            logger.info("Using API key authentication for Kibana")
        elif settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
            from requests.auth import HTTPBasicAuth
            self.auth = HTTPBasicAuth(settings.ELASTICSEARCH_USERNAME, 
                                      settings.ELASTICSEARCH_PASSWORD)
            logger.info("Using basic authentication for Kibana")
        else:
            self.auth = None
            logger.warning("No authentication configured for Kibana")
            
        # Set default request timeout
        self.timeout = 5  # 5 seconds
    
    def _get_kibana_url(self) -> str:
        """
        Get Kibana URL from Elasticsearch URL.
        """
        # If using Cloud ID, we need to use a different approach to get the Kibana URL
        if settings.ELASTICSEARCH_CLOUD_ID:
            # For Elastic Cloud, we need to construct the Kibana URL 
            kibana_url = settings.KIBANA_URL
            if kibana_url:
                logger.info(f"Using configured Kibana URL: {kibana_url}")
                return kibana_url
                
            # Try to derive from cloud ID if KIBANA_URL not set
            try:
                import base64
                # Cloud ID format: name:base64_encoded_data
                cloud_id = settings.ELASTICSEARCH_CLOUD_ID
                encoded_part = cloud_id.split(':', 1)[1]
                decoded = base64.b64decode(encoded_part).decode('utf-8')
                segments = decoded.split('$')
                
                if len(segments) >= 3:
                    domain = segments[0]
                    kibana_uuid = segments[2]
                    kibana_url = f"https://{kibana_uuid}.{domain}"
                    logger.info(f"Derived Kibana URL from Cloud ID: {kibana_url}")
                    return kibana_url
            except Exception as e:
                logger.warning(f"Failed to derive Kibana URL from Cloud ID: {str(e)}")
            
            logger.warning("Using Cloud ID but KIBANA_URL is not set. Kibana integration may not work properly.")
            # Fallback to a generic elastic.co URL
            return "https://cloud.elastic.co"
        
        # For standard deployments, derive Kibana URL from Elasticsearch URL
        if not settings.ELASTICSEARCH_HOSTS or len(settings.ELASTICSEARCH_HOSTS) == 0:
            logger.warning("No Elasticsearch hosts configured. Kibana integration will not work.")
            return "http://localhost:5601"
            
        es_url = settings.ELASTICSEARCH_HOSTS[0]
        kibana_url = es_url.replace(":9200", ":5601")
        logger.info(f"Using derived Kibana URL: {kibana_url}")
        return kibana_url
    
    def create_index_pattern(self, pattern_id: str, time_field: str = "timestamp") -> bool:
        """
        Create an index pattern in Kibana.
        """
        try:
            url = f"{self.kibana_url}/api/saved_objects/index-pattern/{pattern_id}"
            
            data = {
                "attributes": {
                    "title": pattern_id,
                    "timeFieldName": time_field
                }
            }
            
            response = requests.post(
                url, 
                headers=self.headers,
                auth=self.auth,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created index pattern: {pattern_id}")
                return True
            elif response.status_code == 409:
                # Already exists, which is fine
                logger.info(f"Index pattern already exists: {pattern_id}")
                return True
            else:
                logger.error(f"Failed to create index pattern {pattern_id}: {response.status_code} - {response.text}")
                return False
                
        except Timeout:
            logger.error(f"Timeout creating index pattern: {pattern_id}")
            return False
        except RequestException as e:
            logger.error(f"Network error creating index pattern: {str(e)}")
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
                json=dashboard_json,
                timeout=self.timeout
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Imported dashboard: {dashboard_json.get('title', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to import dashboard: {response.status_code} - {response.text}")
                return False
                
        except Timeout:
            logger.error(f"Timeout importing dashboard: {dashboard_json.get('title', 'Unknown')}")
            return False
        except RequestException as e:
            logger.error(f"Network error importing dashboard: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error importing dashboard: {str(e)}")
            return False
    
    def create_visualization(self, vis_id: str, vis_type: str, title: str, index_pattern: str, 
                             vis_state: Dict[str, Any]) -> bool:
        """
        Create a visualization in Kibana.
        
        Args:
            vis_id: The ID of the visualization
            vis_type: The type of visualization (line, pie, etc.)
            title: The title of the visualization
            index_pattern: The index pattern to use
            vis_state: The visualization state
        """
        try:
            url = f"{self.kibana_url}/api/saved_objects/visualization/{vis_id}"
            
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
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created visualization: {title}")
                return True
            elif response.status_code == 409:
                # Already exists, which is fine
                logger.info(f"Visualization already exists: {title}")
                return True
            else:
                logger.error(f"Failed to create visualization: {response.status_code} - {response.text}")
                return False
                
        except Timeout:
            logger.error(f"Timeout creating visualization: {title}")
            return False
        except RequestException as e:
            logger.error(f"Network error creating visualization: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            return False
            
    def get_dashboard_url(self, dashboard_id: str) -> str:
        """
        Get URL for a dashboard.
        """
        if settings.ELASTICSEARCH_CLOUD_ID:
            # For Elastic Cloud, the URL format might be different
            return f"{self.kibana_url}/app/dashboards#/view/{dashboard_id}"
            
        return f"{self.kibana_url}/app/kibana#/dashboard/{dashboard_id}" 