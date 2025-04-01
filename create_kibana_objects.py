"""
Kibana Objects Creator

This script creates Kibana objects (connectors, rules, visualizations) directly using the Kibana API
rather than generating JSON files for import, which can cause extension errors.
"""
import os
import json
import requests
import base64
from datetime import datetime

# Elasticsearch/Kibana connection information
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "https://ai-agent-monitoring.es.us-east-2.aws.elastic-cloud.com")
KIBANA_HOST = os.getenv("KIBANA_HOST", "https://ai-agent-monitoring.kb.us-east-2.aws.elastic-cloud.com")
USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")

# Authentication header
auth_header = {
    'Authorization': f'Basic {base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()}'
}

def test_connection():
    """Test connection to Kibana"""
    print("Testing connection to Kibana...")
    try:
        response = requests.get(
            f"{KIBANA_HOST}/api/status",
            headers=auth_header,
            verify=True
        )
        if response.status_code == 200:
            print("Successfully connected to Kibana!")
            return True
        else:
            print(f"Failed to connect to Kibana. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error connecting to Kibana: {e}")
        return False

def create_connector(connector_type, connector_name, connector_config):
    """Create a connector (action) in Kibana"""
    print(f"Creating {connector_type} connector '{connector_name}'...")
    
    # Define connector payload
    if connector_type == "slack":
        connector_payload = {
            "name": connector_name,
            "connector_type_id": ".slack",
            "config": {
                "webhookUrl": connector_config.get("webhook_url", "https://hooks.slack.com/services/YOUR_WEBHOOK_URL")
            }
        }
    elif connector_type == "email":
        connector_payload = {
            "name": connector_name,
            "connector_type_id": ".email",
            "config": {
                "from": connector_config.get("from", "api-monitoring@example.com"),
                "host": connector_config.get("host", "smtp.example.com"),
                "port": connector_config.get("port", 587),
                "secure": connector_config.get("secure", True)
            },
            "secrets": {
                "user": connector_config.get("user", "your-username"),
                "password": connector_config.get("password", "your-password")
            }
        }
    else:
        print(f"Unsupported connector type: {connector_type}")
        return None
    
    # Create connector via API
    try:
        response = requests.post(
            f"{KIBANA_HOST}/api/actions/connector",
            headers={**auth_header, 'kbn-xsrf': 'true', 'Content-Type': 'application/json'},
            json=connector_payload,
            verify=True
        )
        
        if response.status_code in [200, 201]:
            print(f"Successfully created {connector_type} connector!")
            return response.json().get('id')
        else:
            print(f"Failed to create connector. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error creating connector: {e}")
        return None

def create_ml_anomaly_rule(job_id, connector_id, rule_name="API Anomaly Alert"):
    """Create a rule for ML anomalies"""
    print(f"Creating ML anomaly rule '{rule_name}' for job {job_id}...")
    
    if not connector_id:
        print("Cannot create rule: No connector ID provided")
        return None
    
    # Define rule payload
    rule_payload = {
        "name": rule_name,
        "tags": ["api", "monitoring", "anomaly"],
        "params": {
            "machineLearningJob": job_id,
            "anomalyScoreThreshold": 75  # Alert when anomaly score is above 75
        },
        "consumer": "alerts",
        "schedule": { "interval": "5m" },  # Check every 5 minutes
        "actions": [
            {
                "group": "threshold_met",
                "id": connector_id,
                "params": {
                    "message": "API Anomaly Detected: {{context.description}}. Score: {{context.anomaly_score}}. API: {{context.api_id}} in {{context.environment}}",
                }
            }
        ],
        "notify_when": "onActionGroupChange",
        "rule_type_id": ".ml"
    }
    
    # Create rule via API
    try:
        response = requests.post(
            f"{KIBANA_HOST}/api/alerting/rule",
            headers={**auth_header, 'kbn-xsrf': 'true', 'Content-Type': 'application/json'},
            json=rule_payload,
            verify=True
        )
        
        if response.status_code in [200, 201]:
            print(f"Successfully created ML anomaly rule!")
            return response.json().get('id')
        else:
            print(f"Failed to create rule. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error creating rule: {e}")
        return None

def create_ndjson_export_file(job_id):
    """
    Create an NDJSON file that can be imported into Kibana.
    This is the proper format for Kibana saved objects import.
    """
    print("Creating NDJSON export file for Kibana import...")
    
    # Create a visualization for anomalies
    visualization = {
        "attributes": {
            "title": "API Anomalies Overview",
            "visState": json.dumps({
                "title": "API Anomalies Overview",
                "type": "metrics",
                "params": {
                    "id": "61ca57f0-469d-11e7-af02-69e470af7417",
                    "type": "timeseries",
                    "series": [
                        {
                            "id": "anomaly-score",
                            "color": "#68BC00",
                            "split_mode": "terms",
                            "metrics": [
                                {
                                    "id": "1",
                                    "type": "max",
                                    "field": "anomaly_score"
                                }
                            ],
                            "seperate_axis": 0,
                            "axis_position": "right",
                            "formatter": "number",
                            "chart_type": "line",
                            "line_width": 1,
                            "point_size": 1,
                            "fill": 0.5,
                            "stacked": "none",
                            "terms_field": "api_id.keyword",
                            "split_color_mode": "gradient",
                            "label": "Anomaly Score"
                        }
                    ],
                    "time_field": "@timestamp",
                    "index_pattern": ".ml-anomalies-*",
                    "interval": "auto",
                    "axis_position": "left",
                    "axis_formatter": "number",
                    "show_legend": 1,
                    "show_grid": 1
                },
                "aggs": []
            }),
            "uiStateJSON": "{}",
            "description": "Shows anomaly scores for API monitoring",
            "version": 1,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
            }
        },
        "type": "visualization",
        "id": f"api-anomalies-viz-{job_id}"
    }
    
    # Create a dashboard containing the visualization
    dashboard = {
        "attributes": {
            "title": "API Anomalies Dashboard",
            "hits": 0,
            "description": "Dashboard for monitoring API anomalies",
            "panelsJSON": json.dumps([
                {
                    "panelIndex": "1",
                    "gridData": {
                        "x": 0,
                        "y": 0,
                        "w": 24,
                        "h": 15,
                        "i": "1"
                    },
                    "id": f"api-anomalies-viz-{job_id}",
                    "type": "visualization",
                    "version": "7.10.0"
                }
            ]),
            "optionsJSON": "{\"hidePanelTitles\":false,\"useMargins\":true}",
            "version": 1,
            "timeRestore": True,
            "timeTo": "now",
            "timeFrom": "now-24h",
            "refreshInterval": {
                "pause": False,
                "value": 60000
            },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
            }
        },
        "type": "dashboard",
        "id": f"api-anomalies-dashboard-{job_id}"
    }
    
    # Create NDJSON content - each JSON object on a new line without commas
    ndjson_content = f"{json.dumps(visualization)}\n{json.dumps(dashboard)}"
    
    # Save to file with .ndjson extension (the correct format for Kibana imports)
    os.makedirs("kibana_imports", exist_ok=True)
    file_path = f"kibana_imports/api_monitoring_objects.ndjson"
    
    with open(file_path, 'w') as f:
        f.write(ndjson_content)
    
    print(f"NDJSON export file created at {file_path}")
    print("This file can be imported in Kibana via Stack Management > Saved Objects > Import")
    
    return file_path

def main():
    """Main execution flow"""
    print("=== Kibana Objects Creator ===")
    
    # Test connection
    if not test_connection():
        print("Exiting due to connection issues.")
        return
    
    # Get ML job ID
    job_id = input("Enter your ML job ID (e.g., api_performance_anomalies): ")
    if not job_id:
        print("No job ID provided. Exiting.")
        return
    
    # Create connector
    print("\nConnector Creation")
    print("1. Create a Slack connector")
    print("2. Create an Email connector")
    print("3. Skip connector creation (if you already have one)")
    
    connector_choice = input("\nEnter your choice (1-3): ")
    
    connector_id = None
    if connector_choice == "1":
        webhook_url = input("Enter Slack webhook URL: ")
        connector_id = create_connector("slack", "API Monitoring Slack", {"webhook_url": webhook_url})
    elif connector_choice == "2":
        email = input("Enter 'from' email address: ")
        smtp_host = input("Enter SMTP host: ")
        smtp_user = input("Enter SMTP username: ")
        smtp_pass = input("Enter SMTP password: ")
        
        connector_id = create_connector("email", "API Monitoring Email", {
            "from": email,
            "host": smtp_host,
            "user": smtp_user,
            "password": smtp_pass
        })
    elif connector_choice == "3":
        connector_id = input("Enter your existing connector ID: ")
    else:
        print("Invalid choice. Skipping connector creation.")
    
    # Create alert rule if we have a connector
    if connector_id:
        rule_id = create_ml_anomaly_rule(job_id, connector_id)
        if rule_id:
            print(f"Successfully created rule with ID: {rule_id}")
    else:
        print("Skipping rule creation since no connector ID is available.")
    
    # Create NDJSON export file for dashboards and visualizations
    ndjson_file = create_ndjson_export_file(job_id)
    
    print("\n=== Setup Summary ===")
    print(f"ML Job ID: {job_id}")
    if connector_id:
        print(f"Connector ID: {connector_id}")
    if 'rule_id' in locals() and rule_id:
        print(f"Rule ID: {rule_id}")
    print(f"NDJSON Export File: {ndjson_file}")
    
    print("\n=== Next Steps ===")
    print("1. Import the NDJSON file in Kibana:")
    print("   Go to Stack Management > Saved Objects > Import")
    print("   Select the file: " + ndjson_file)
    print("\n2. To test your setup, run the trigger_anomaly.py script to inject anomalous data.")

if __name__ == "__main__":
    main() 