from elasticsearch import Elasticsearch
import json
import urllib.parse
import os

# Elasticsearch connection information from .env file
cloud_id = "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg=="
username = "elastic"
password = "KIuc03ZYAf6IqGkE1zEap1DR"

print("Connecting to Elasticsearch...")
try:
    # Connect to Elasticsearch
    es = Elasticsearch(
        cloud_id=cloud_id,
        basic_auth=(username, password)
    )
    
    # Test connection
    info = es.info()
    print(f"Successfully connected to Elasticsearch cluster: {info['cluster_name']}")
except Exception as e:
    print(f"Failed to connect to Elasticsearch: {e}")
    print("Please check your credentials and network connection.")
    print("\nEven if we can't connect to Elasticsearch, here's the URL to view the visualization:")
    base_url = "https://ai-agent-monitoring.kb.us-east-2.aws.elastic-cloud.com/app/ml"
    job_id = urllib.parse.quote("api_response_time_anomalies")
    time_range = "from:1584975600000,to:1587513540000"  # Similar to the screenshot (Mar-Apr 2020)
    single_metric_url = f"{base_url}#/timeseriesexplorer?_g=(ml:(jobIds:!('{job_id}')),time:({time_range}))&_a=(mlTimeSeriesExplorer:(detectorIndex:0,entities:(),zoom:(from:'2020-04-13T07:00:00.000Z',to:'2020-04-15T07:00:00.000Z')))"
    print(f"\n{single_metric_url}\n")
    exit(1)

# Create directory for job configs if it doesn't exist
os.makedirs("jobs", exist_ok=True)

# Create job config files if they don't exist
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
      "time_field": "@timestamp",
      "time_format": "epoch_ms"
    },
    "model_plot_config": {
      "enabled": True,
      "annotations_enabled": True
    },
    "custom_settings": {
      "custom_urls": [
        {
          "url_name": "API Dashboard",
          "url_value": "kibana#/dashboard/api-monitoring-overview"
        }
      ]
    }
}

error_rate_job = {
    "job_id": "api_error_rate_analysis",
    "description": "Monitors API error rates across environments",
    "analysis_config": {
      "bucket_span": "10m",
      "detectors": [
        {
          "function": "high_non_zero_count",
          "field_name": "is_error",
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
      "time_field": "@timestamp",
      "time_format": "epoch_ms"
    }
}

# Save job configs as files
with open('jobs/api_response_time.json', 'w') as f:
    json.dump(response_time_job, f, indent=2)

with open('jobs/api_error_rate_analysis.json', 'w') as f:
    json.dump(error_rate_job, f, indent=2)

try:
    # Create the jobs using the ML API
    print("Creating ML jobs...")
    try:
        # Try to create first job
        es.ml.put_job(job_id=response_time_job["job_id"], body=response_time_job)
        print(f"Created job: {response_time_job['job_id']}")
    except Exception as e:
        print(f"Error creating response time job: {e}")
    
    try:
        # Try to create second job
        es.ml.put_job(job_id=error_rate_job["job_id"], body=error_rate_job)
        print(f"Created job: {error_rate_job['job_id']}")
    except Exception as e:
        print(f"Error creating error rate job: {e}")

    # Generate direct link to the Single Metric Viewer for the job
    base_url = "https://ai-agent-monitoring.kb.us-east-2.aws.elastic-cloud.com/app/ml"
    job_id = urllib.parse.quote(response_time_job["job_id"])
    time_range = "from:1584975600000,to:1587513540000"  # Similar to the screenshot (Mar-Apr 2020)

    # Direct link to Single Metric Viewer
    single_metric_url = f"{base_url}#/timeseriesexplorer?_g=(ml:(jobIds:!('{job_id}')),time:({time_range}))&_a=(mlTimeSeriesExplorer:(detectorIndex:0,entities:(),zoom:(from:'2020-04-13T07:00:00.000Z',to:'2020-04-15T07:00:00.000Z')))"

    print("\n==== URL for Visualization ====")
    print(f"Access the visualization at the following URL:")
    print(f"\n{single_metric_url}\n")
    print("Copy this URL and paste it into your browser to view the visualization.")
    
except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure your Elasticsearch credentials are correct and you have the required permissions.") 