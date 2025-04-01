"""
Machine Learning Job and Alert Creator

This script:
1. Connects to Elasticsearch
2. Creates an ML job for API anomaly detection
3. Sets up an alert rule that triggers when anomalies are detected
4. Configures a notification connector (placeholder for you to customize)
"""
import os
import json
import urllib.parse
import time
from elasticsearch import Elasticsearch
import requests
from datetime import datetime, timedelta

# Configuration parameters (normally would be in .env)
ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", 
                                  "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")
KIBANA_BASE_URL = os.getenv("KIBANA_BASE_URL", "https://ai-agent-monitoring.kb.us-east-2.aws.elastic-cloud.com")

# Create directories for storing configurations
os.makedirs("jobs", exist_ok=True)
os.makedirs("alerts", exist_ok=True)

# Connect to Elasticsearch
print("Connecting to Elasticsearch...")
try:
    es = Elasticsearch(
        cloud_id=ELASTICSEARCH_CLOUD_ID,
        basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
    )
    
    # Test connection
    info = es.info()
    print(f"Successfully connected to Elasticsearch cluster: {info['cluster_name']}")
except Exception as e:
    print(f"Failed to connect to Elasticsearch: {e}")
    exit(1)

def create_ml_job():
    """Create a machine learning job for API anomaly detection"""
    print("Creating ML job for API anomaly detection...")
    
    # Define the ML job
    api_anomaly_job = {
        "job_id": "api_performance_anomalies",
        "description": "Detects anomalies in API performance across environments",
        "analysis_config": {
          "bucket_span": "10m",  # Analyze data in 10-minute buckets
          "detectors": [
            {
              "function": "high_mean",  # Detect unusually high average values
              "field_name": "response_time_ms",
              "over_field_name": "api_endpoint",
              "partition_field_name": "environment"
            },
            {
              "function": "high_count",  # Detect unusually high count of error events
              "field_name": "error_count",
              "partition_field_name": "api_id"
            }
          ],
          "influencers": [
            "api_endpoint",
            "environment",
            "service_name",
            "api_id"
          ]
        },
        "data_description": {
          "time_field": "@timestamp"
        },
        "model_plot_config": {
          "enabled": True,
          "annotations_enabled": True
        }
    }
    
    # Save job config to file
    with open('jobs/api_performance_anomalies.json', 'w') as f:
        json.dump(api_anomaly_job, f, indent=2)
    
    # Create the job in Elasticsearch
    try:
        # Create the ML job
        es.ml.put_job(job_id=api_anomaly_job["job_id"], body=api_anomaly_job)
        print(f"Created job: {api_anomaly_job['job_id']}")
        
        # Create a datafeed for the job
        datafeed_id = f"{api_anomaly_job['job_id']}-datafeed"
        datafeed_config = {
            "job_id": api_anomaly_job["job_id"],
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Created datafeed: {datafeed_id}")
        
        # Start the datafeed
        try:
            es.ml.start_datafeed(datafeed_id=datafeed_id, start="now-7d")
            print(f"Started datafeed: {datafeed_id}")
        except Exception as e:
            print(f"Note: Could not start datafeed. You may need to manually start it: {e}")
        
        return api_anomaly_job["job_id"]
    except Exception as e:
        print(f"Error creating ML job: {e}")
        return None

def create_connector_config():
    """
    Create a connector configuration for alerts.
    
    This creates a configuration file you can use to setup a connector
    in Kibana UI. In a production environment, you would use Kibana API
    to create this automatically.
    """
    # Create a sample Slack connector config
    slack_connector = {
        "name": "API Monitoring Slack",
        "connector_type_id": ".slack",
        "config": {
            "webhookUrl": "https://hooks.slack.com/services/YOUR_WEBHOOK_URL"
        }
    }
    
    # Create a sample email connector config
    email_connector = {
        "name": "API Monitoring Email",
        "connector_type_id": ".email",
        "config": {
            "from": "api-monitoring@example.com",
            "host": "smtp.example.com",
            "port": 587,
            "secure": True
        },
        "secrets": {
            "user": "your-username",
            "password": "your-password"
        }
    }
    
    # Save connector configs
    os.makedirs("connectors", exist_ok=True)
    with open('connectors/slack_connector.json', 'w') as f:
        json.dump(slack_connector, f, indent=2)
    
    with open('connectors/email_connector.json', 'w') as f:
        json.dump(email_connector, f, indent=2)
    
    print("Created connector configurations in 'connectors' directory")
    print("Use these configurations to create connectors in Kibana UI")

def create_alert_rule_config(job_id):
    """
    Create an alert rule configuration file.
    
    This creates a configuration file you can use to setup an alert rule
    in Kibana UI. In a production environment, you would use Kibana API
    to create this automatically.
    """
    if not job_id:
        print("Cannot create alert rule: No ML job ID provided")
        return
    
    # Create an alert rule for ML job anomalies
    ml_alert_rule = {
        "name": "API Anomaly Detection Alert",
        "tags": ["api", "monitoring", "anomaly"],
        "enabled": True,
        "rule_type_id": "ml",
        "consumer": "alerts",
        "params": {
            "machineLearningJob": job_id,
            "anomalyScoreThreshold": 75  # Alert when anomaly score is above 75
        },
        "schedule": { "interval": "5m" },  # Check every 5 minutes
        "actions": [
            {
                "group": "threshold_met",
                "id": "CONNECTOR_ID_GOES_HERE",  # Replace with actual connector ID after creating in Kibana
                "params": {
                    "message": "API Anomaly Detected: {{context.description}}. Score: {{context.anomaly_score}}. API: {{context.api_id}} in {{context.environment}}",
                }
            }
        ],
        "notify_when": "onActionGroupChange"
    }
    
    # Save alert rule config
    with open('alerts/api_anomaly_alert.json', 'w') as f:
        json.dump(ml_alert_rule, f, indent=2)
    
    print("Created alert rule configuration in 'alerts/api_anomaly_alert.json'")
    print("Follow these steps to create the alert in Kibana:")
    print("1. Go to Kibana > Stack Management > Rules and Connectors")
    print("2. First create a connector (email, Slack, etc.)")
    print("3. Create a new rule using the configuration in 'alerts/api_anomaly_alert.json'")
    print("4. Replace 'CONNECTOR_ID_GOES_HERE' with your actual connector ID")
    print("5. Save the rule")

def provide_kibana_urls(job_id):
    """Provide URLs to access Kibana ML views and dashboards"""
    if not job_id:
        print("Cannot provide URLs: No ML job ID available")
        return
    
    # URL encode the job ID
    encoded_job_id = urllib.parse.quote(job_id)
    
    # ML job URL
    ml_job_url = f"{KIBANA_BASE_URL}/app/ml#/jobs/single_metric/{encoded_job_id}"
    
    # Anomaly Explorer URL
    anomaly_explorer_url = f"{KIBANA_BASE_URL}/app/ml#/explorer?_g=(ml:(jobIds:!('{encoded_job_id}')))"
    
    # Print URLs
    print("\n==== URLs for ML Job and Alerts ====")
    print(f"1. ML Job Overview: {ml_job_url}")
    print(f"2. Anomaly Explorer: {anomaly_explorer_url}")
    print(f"3. Alert Rules: {KIBANA_BASE_URL}/app/management/insightsAndAlerting/triggersActions/alerts")
    print(f"4. Connectors: {KIBANA_BASE_URL}/app/management/insightsAndAlerting/triggersActions/connectors")

def create_sample_visualization():
    """Create a sample Kibana visualization configuration file for ML results"""
    # Define a visualization for anomaly results
    anomaly_viz = {
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
                    "index_pattern": "ml_anomalies*",
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
            "savedSearchId": "",
            "version": 1
        }
    }
    
    # Save visualization config
    os.makedirs("visualizations", exist_ok=True)
    with open('visualizations/api_anomalies_viz.json', 'w') as f:
        json.dump(anomaly_viz, f, indent=2)
    
    print("Created visualization configuration in 'visualizations/api_anomalies_viz.json'")
    print("To import this visualization:")
    print("1. Go to Kibana > Stack Management > Saved Objects")
    print("2. Click Import")
    print("3. Select the 'visualizations/api_anomalies_viz.json' file")

def main():
    try:
        # Step 1: Create ML job
        job_id = create_ml_job()
        
        # Step 2: Create connector configuration
        create_connector_config()
        
        # Step 3: Create alert rule configuration
        create_alert_rule_config(job_id)
        
        # Step 4: Create sample visualization
        create_sample_visualization()
        
        # Step 5: Provide Kibana URLs
        provide_kibana_urls(job_id)
        
        print("\nSetup completed! Follow the instructions above to finish setting up your alerts in Kibana.")
        print("\nAfter setup is complete, you can inject test anomalies using the 'trigger_anomaly.py' script.")
        
    except Exception as e:
        print(f"An error occurred during setup: {e}")

if __name__ == "__main__":
    main() 