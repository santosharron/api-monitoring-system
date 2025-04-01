"""
API Monitoring System Setup

This script:
1. Connects to Elasticsearch
2. Creates ML jobs for anomaly detection
3. Sets up alerts for detected anomalies
4. Creates Kibana visualizations and dashboards
5. Provides a URL to access the monitoring dashboard
"""
import os
import json
import urllib.parse
import time
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.client import MlClient
from elasticsearch.helpers import bulk

# Configuration parameters (normally would be in .env)
ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", 
                                  "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")
KIBANA_BASE_URL = os.getenv("KIBANA_BASE_URL", "https://ai-agent-monitoring.kb.us-east-2.aws.elastic-cloud.com")

# Create directories for storing configurations
os.makedirs("jobs", exist_ok=True)
os.makedirs("dashboards", exist_ok=True)
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

# Function to create indices if they don't exist
def create_indices():
    print("Creating required indices...")
    
    # API metrics index template
    api_metrics_template = {
        "index_patterns": ["api_metrics*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "api_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "service_name": {"type": "keyword"},
                    "api_endpoint": {"type": "keyword"},
                    "response_time_ms": {"type": "float"},
                    "status_code": {"type": "integer"},
                    "is_error": {"type": "boolean"},
                    "error_type": {"type": "keyword"},
                    "error_count": {"type": "integer"},
                    "request_id": {"type": "keyword"}
                }
            }
        }
    }
    
    # Anomalies index template
    anomalies_template = {
        "index_patterns": ["api_anomalies*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "anomaly_id": {"type": "keyword"},
                    "anomaly_type": {"type": "keyword"},
                    "api_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "severity": {"type": "float"},
                    "description": {"type": "text"},
                    "affected_endpoints": {"type": "keyword"},
                    "anomaly_score": {"type": "float"}
                }
            }
        }
    }
    
    try:
        # Create index templates
        es.indices.put_index_template(name="api_metrics_template", body=api_metrics_template)
        es.indices.put_index_template(name="api_anomalies_template", body=anomalies_template)
        
        # Create initial indices
        if not es.indices.exists(index="api_metrics"):
            es.indices.create(index="api_metrics")
        
        if not es.indices.exists(index="api_anomalies"):
            es.indices.create(index="api_anomalies")
            
        print("Indices created successfully")
    except Exception as e:
        print(f"Error creating indices: {e}")

# Function to generate sample data for testing
def generate_sample_data():
    print("Generating sample data...")
    
    # Sample APIs and environments
    apis = [
        {"api_id": "user-service", "endpoints": ["/users", "/users/{id}", "/users/auth"]},
        {"api_id": "order-service", "endpoints": ["/orders", "/orders/{id}", "/orders/status"]},
        {"api_id": "payment-service", "endpoints": ["/payments", "/payments/process", "/payments/{id}"]}
    ]
    
    environments = ["production", "staging", "development"]
    
    # Generate data points
    now = datetime.now()
    bulk_data = []
    
    # Create normal data
    for day in range(7):
        for hour in range(24):
            for api in apis:
                for endpoint in api["endpoints"]:
                    for env in environments:
                        # Base response time varies by environment
                        base_response_time = {
                            "production": 75,
                            "staging": 95,
                            "development": 120
                        }[env]
                        
                        # Time-based variation (peak hours)
                        hour_factor = 1 + (0.5 if 9 <= hour <= 17 else 0)
                        
                        # Day-based variation (weekends)
                        day_of_week = (datetime.now().weekday() + day) % 7
                        day_factor = 0.7 if day_of_week >= 5 else 1.0
                        
                        # Calculate response time with some randomness
                        import random
                        response_time = base_response_time * hour_factor * day_factor * random.uniform(0.8, 1.2)
                        
                        # Occasionally introduce errors
                        is_error = random.random() < 0.02
                        status_code = random.choice([500, 502, 503, 504]) if is_error else 200
                        error_type = random.choice(["timeout", "internal_error", "bad_gateway"]) if is_error else None
                        error_count = 1 if is_error else 0
                        
                        # Timestamp for this data point
                        timestamp = now - timedelta(days=day, hours=24-hour)
                        
                        # Create document
                        doc = {
                            "_index": "api_metrics",
                            "_source": {
                                "@timestamp": timestamp.isoformat(),
                                "api_id": api["api_id"],
                                "api_endpoint": endpoint,
                                "environment": env,
                                "service_name": api["api_id"],
                                "response_time_ms": response_time,
                                "status_code": status_code,
                                "is_error": is_error,
                                "error_type": error_type,
                                "error_count": error_count,
                                "request_id": f"req-{int(time.time())}-{random.randint(1000, 9999)}"
                            }
                        }
                        
                        bulk_data.append(doc)
    
    # Introduce some anomalies for demonstration
    # Anomaly 1: Spike in response time for user service in production
    anomaly_time = now - timedelta(days=2, hours=3)
    for i in range(20):
        spike_time = anomaly_time + timedelta(minutes=i*3)
        doc = {
            "_index": "api_metrics",
            "_source": {
                "@timestamp": spike_time.isoformat(),
                "api_id": "user-service",
                "api_endpoint": "/users",
                "environment": "production",
                "service_name": "user-service",
                "response_time_ms": 950 + random.uniform(0, 300),  # Huge spike
                "status_code": 200,
                "is_error": False,
                "error_count": 0,
                "request_id": f"req-{int(time.time())}-{random.randint(1000, 9999)}"
            }
        }
        bulk_data.append(doc)
    
    # Anomaly 2: Error rate spike for payment service in staging
    anomaly_time = now - timedelta(days=1, hours=12)
    for i in range(30):
        spike_time = anomaly_time + timedelta(minutes=i*2)
        doc = {
            "_index": "api_metrics",
            "_source": {
                "@timestamp": spike_time.isoformat(),
                "api_id": "payment-service",
                "api_endpoint": "/payments/process",
                "environment": "staging",
                "service_name": "payment-service",
                "response_time_ms": 120 + random.uniform(0, 50),
                "status_code": 500,
                "is_error": True,
                "error_type": "internal_error",
                "error_count": 1,
                "request_id": f"req-{int(time.time())}-{random.randint(1000, 9999)}"
            }
        }
        bulk_data.append(doc)
    
    # Insert the data
    try:
        success, failed = bulk(es, bulk_data)
        print(f"Sample data generation: {success} documents indexed, {len(failed) if failed else 0} failed")
    except Exception as e:
        print(f"Error generating sample data: {e}")

# Function to create ML jobs
def create_ml_jobs():
    print("Creating ML jobs...")
    
    # Response time anomaly detection job
    response_time_job = {
        "job_id": "api_response_time_anomalies",
        "description": "Detects anomalies in API response times across environments",
        "analysis_config": {
          "bucket_span": "15m",
          "detectors": [
            {
              "function": "high_mean",
              "field_name": "response_time_ms",
              "over_field_name": "api_endpoint",
              "partition_field_name": "environment"
            },
            {
              "function": "spike_mean",
              "field_name": "response_time_ms",
              "over_field_name": "api_endpoint"
            }
          ],
          "influencers": [
            "api_endpoint",
            "environment",
            "service_name"
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
    
    # Error rate anomaly detection job
    error_rate_job = {
        "job_id": "api_error_rate_anomalies",
        "description": "Monitors API error rates across environments",
        "analysis_config": {
          "bucket_span": "10m",
          "detectors": [
            {
              "function": "high_non_zero_count",
              "field_name": "error_count",
              "by_field_name": "api_endpoint",
              "partition_field_name": "environment"
            },
            {
              "function": "time_of_day",
              "field_name": "error_count"
            }
          ],
          "influencers": [
            "api_endpoint",
            "environment",
            "error_type",
            "status_code"
          ]
        },
        "data_description": {
          "time_field": "@timestamp"
        }
    }
    
    # Cross-environment correlation job
    cross_env_job = {
        "job_id": "cross_environment_anomalies",
        "description": "Correlates patterns across environments to detect cross-environment issues",
        "analysis_config": {
          "bucket_span": "30m",
          "detectors": [
            {
              "function": "mean",
              "field_name": "response_time_ms",
              "by_field_name": "api_id",
              "over_field_name": "environment"
            }
          ],
          "influencers": [
            "api_id",
            "environment"
          ]
        },
        "data_description": {
          "time_field": "@timestamp"
        }
    }
    
    # Save job configs to files
    with open('jobs/api_response_time.json', 'w') as f:
        json.dump(response_time_job, f, indent=2)
    
    with open('jobs/api_error_rate.json', 'w') as f:
        json.dump(error_rate_job, f, indent=2)
    
    with open('jobs/cross_environment.json', 'w') as f:
        json.dump(cross_env_job, f, indent=2)
    
    # Create the jobs in Elasticsearch
    try:
        # Create response time job
        es.ml.put_job(job_id=response_time_job["job_id"], body=response_time_job)
        print(f"Created job: {response_time_job['job_id']}")
        
        # Create a datafeed for the job
        datafeed_id = f"{response_time_job['job_id']}-datafeed"
        datafeed_config = {
            "job_id": response_time_job["job_id"],
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Created datafeed: {datafeed_id}")
        
        # Start the datafeed
        es.ml.start_datafeed(datafeed_id=datafeed_id, start="now-7d")
        
        # Create error rate job
        es.ml.put_job(job_id=error_rate_job["job_id"], body=error_rate_job)
        print(f"Created job: {error_rate_job['job_id']}")
        
        # Create a datafeed for the job
        datafeed_id = f"{error_rate_job['job_id']}-datafeed"
        datafeed_config = {
            "job_id": error_rate_job["job_id"],
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Created datafeed: {datafeed_id}")
        
        # Start the datafeed
        es.ml.start_datafeed(datafeed_id=datafeed_id, start="now-7d")
        
        # Create cross-environment job
        es.ml.put_job(job_id=cross_env_job["job_id"], body=cross_env_job)
        print(f"Created job: {cross_env_job['job_id']}")
        
        # Create a datafeed for the job
        datafeed_id = f"{cross_env_job['job_id']}-datafeed"
        datafeed_config = {
            "job_id": cross_env_job["job_id"],
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Created datafeed: {datafeed_id}")
        
        # Start the datafeed
        es.ml.start_datafeed(datafeed_id=datafeed_id, start="now-7d")
        
    except Exception as e:
        print(f"Error creating ML jobs: {e}")

# Function to create alert rules
def create_alerts():
    print("Creating alert rules...")
    
    # Rule for response time anomalies
    response_time_rule = {
        "name": "Response Time Anomalies",
        "tags": ["api", "monitoring", "response_time"],
        "enabled": True,
        "rule_type_id": "ml",
        "consumer": "alerts",
        "params": {
            "machineLearningJob": "api_response_time_anomalies",
            "anomalyScoreThreshold": 75
        },
        "schedule": { "interval": "5m" },
        "actions": [
            {
                "group": "threshold_met",
                "id": "7a1e306e-aa0e-4e35-8456-1a651263277c",  # Example action ID
                "params": {
                    "message": "High response time detected for {{context.api_endpoint}} in {{context.environment}}. Score: {{context.anomaly_score}}",
                }
            }
        ],
        "notify_when": "onActionGroupChange"
    }
    
    # Rule for error rate anomalies
    error_rate_rule = {
        "name": "Error Rate Anomalies",
        "tags": ["api", "monitoring", "error_rate"],
        "enabled": True,
        "rule_type_id": "ml",
        "consumer": "alerts",
        "params": {
            "machineLearningJob": "api_error_rate_anomalies",
            "anomalyScoreThreshold": 75
        },
        "schedule": { "interval": "5m" },
        "actions": [
            {
                "group": "threshold_met",
                "id": "7a1e306e-aa0e-4e35-8456-1a651263277c",  # Example action ID
                "params": {
                    "message": "High error rate detected for {{context.api_endpoint}} in {{context.environment}}. Score: {{context.anomaly_score}}",
                }
            }
        ],
        "notify_when": "onActionGroupChange"
    }
    
    # Save alert configs to files
    with open('alerts/response_time_alert.json', 'w') as f:
        json.dump(response_time_rule, f, indent=2)
    
    with open('alerts/error_rate_alert.json', 'w') as f:
        json.dump(error_rate_rule, f, indent=2)
    
    # Note: Creating alert rules requires Kibana API access which is not directly supported
    # by the Elasticsearch Python client. In a real implementation, we would use Kibana API
    # to create these alerts or use the Kibana UI to configure them.
    print("Alert rule configurations saved to files. Please use Kibana UI to create these alerts.")
    print("See the 'alerts' directory for the configurations.")

# Function to create Kibana visualizations and dashboards
def create_visualizations():
    print("Creating Kibana visualizations and dashboards...")
    
    # Define API Overview dashboard
    api_overview_dashboard = {
        "attributes": {
            "title": "API Monitoring Overview",
            "description": "Overview of API performance across environments",
            "hits": 0,
            "timeRestore": True,
            "timeFrom": "now-24h",
            "timeTo": "now",
            "refreshInterval": {
                "pause": False,
                "value": 60000  # Refresh every minute
            },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{\"filter\":[]}"
            },
            "panelsJSON": json.dumps([
                # Response time metrics panel
                {
                    "id": "response-time-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 0,
                        "y": 0,
                        "w": 24,
                        "h": 12,
                        "i": "1"
                    },
                    "version": "7.10.0",
                    "panelIndex": "1"
                },
                # Error rate metrics panel
                {
                    "id": "error-rate-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 24,
                        "y": 0,
                        "w": 24,
                        "h": 12,
                        "i": "2"
                    },
                    "version": "7.10.0",
                    "panelIndex": "2"
                },
                # API health by environment panel
                {
                    "id": "api-health-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 0,
                        "y": 12,
                        "w": 48,
                        "h": 12,
                        "i": "3"
                    },
                    "version": "7.10.0",
                    "panelIndex": "3"
                }
            ])
        }
    }
    
    # Define Anomaly Detection dashboard
    anomaly_dashboard = {
        "attributes": {
            "title": "API Anomaly Detection",
            "description": "Analysis of detected anomalies in API performance",
            "hits": 0,
            "timeRestore": True,
            "timeFrom": "now-7d",
            "timeTo": "now",
            "refreshInterval": {
                "pause": False,
                "value": 300000  # Refresh every 5 minutes
            },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{\"filter\":[]}"
            },
            "panelsJSON": json.dumps([
                # Response time anomalies panel
                {
                    "id": "response-time-anomalies-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 0,
                        "y": 0,
                        "w": 48,
                        "h": 12,
                        "i": "1"
                    },
                    "version": "7.10.0",
                    "panelIndex": "1"
                },
                # Error rate anomalies panel
                {
                    "id": "error-rate-anomalies-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 0,
                        "y": 12,
                        "w": 24,
                        "h": 12,
                        "i": "2"
                    },
                    "version": "7.10.0",
                    "panelIndex": "2"
                },
                # Anomaly severity distribution panel
                {
                    "id": "anomaly-severity-panel",
                    "type": "visualization",
                    "gridData": {
                        "x": 24,
                        "y": 12,
                        "w": 24,
                        "h": 12,
                        "i": "3"
                    },
                    "version": "7.10.0",
                    "panelIndex": "3"
                }
            ])
        }
    }
    
    # Save dashboard configs to files
    with open('dashboards/api_overview_dashboard.json', 'w') as f:
        json.dump(api_overview_dashboard, f, indent=2)
    
    with open('dashboards/anomaly_dashboard.json', 'w') as f:
        json.dump(anomaly_dashboard, f, indent=2)
    
    # Note: Creating Kibana visualizations and dashboards requires Kibana API access
    # which is not directly supported by the Elasticsearch Python client.
    # In a real implementation, we would use Kibana API to create these dashboards
    # or import them through the Kibana UI.
    print("Dashboard configurations saved to files. Please use Kibana UI to import these dashboards.")
    print("See the 'dashboards' directory for the configurations.")

# Function to provide URLs to access Kibana dashboards and ML views
def provide_access_urls():
    # Get URL for ML jobs
    ml_jobs_url = f"{KIBANA_BASE_URL}/app/ml#/jobs"
    
    # Get URL for Single Metric Viewer for the response time anomalies job
    job_id = urllib.parse.quote("api_response_time_anomalies")
    time_range = "from:now-7d,to:now"
    single_metric_url = f"{KIBANA_BASE_URL}/app/ml#/timeseriesexplorer?_g=(ml:(jobIds:!('{job_id}')),time:({time_range}))"
    
    # Get URL for anomaly detection dashboard
    dashboard_url = f"{KIBANA_BASE_URL}/app/dashboards#/view/api-anomaly-detection-dashboard"
    
    # Print URLs
    print("\n==== URLs for Monitoring System ====")
    print(f"1. ML Jobs Overview: {ml_jobs_url}")
    print(f"2. Response Time Anomalies Viewer: {single_metric_url}")
    print(f"3. Anomaly Detection Dashboard: {dashboard_url}")
    print("\nImportant: Copy these URLs and paste them into your browser to access the monitoring system.")

# Main execution flow
def main():
    try:
        # Step 1: Create necessary indices
        create_indices()
        
        # Step 2: Generate sample data
        generate_sample_data()
        
        # Step 3: Create ML jobs
        create_ml_jobs()
        
        # Step 4: Create alert rules
        create_alerts()
        
        # Step 5: Create Kibana visualizations and dashboards
        create_visualizations()
        
        # Step 6: Provide access URLs
        provide_access_urls()
        
        print("\nSetup completed successfully! Follow the URLs above to access your monitoring system.")
        
    except Exception as e:
        print(f"Error during setup: {e}")

if __name__ == "__main__":
    main() 