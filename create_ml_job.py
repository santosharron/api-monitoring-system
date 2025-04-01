"""
Machine Learning Job Creator for API Monitoring

This script creates an ML job in Elasticsearch for API anomaly detection.
It focuses specifically on setting up the ML job correctly.
"""
import os
import json
import time
from elasticsearch import Elasticsearch

# Configuration parameters (from environment or defaults)
ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", 
                                  "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")

def connect_to_elasticsearch():
    """Connect to Elasticsearch and verify connection"""
    print("Connecting to Elasticsearch...")
    try:
        es = Elasticsearch(
            cloud_id=ELASTICSEARCH_CLOUD_ID,
            basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
        )
        
        # Test connection
        info = es.info()
        print(f"Successfully connected to Elasticsearch cluster: {info['cluster_name']}")
        return es
    except Exception as e:
        print(f"Failed to connect to Elasticsearch: {e}")
        return None

def create_response_time_job(es, job_id="api_response_time_anomalies"):
    """Create a job to detect response time anomalies"""
    # Generate unique job ID to avoid conflicts with existing jobs
    timestamp = int(time.time())
    unique_job_id = f"{job_id}-{timestamp}"
    
    print(f"Creating response time anomaly detection job: {unique_job_id}")
    
    job_config = {
        "description": "Detects anomalies in API response times across environments",
        "analysis_config": {
          "bucket_span": "15m",
          "detectors": [
            {
              "detector_description": "High mean response time by endpoint and environment",
              "function": "mean",
              "field_name": "response_time_ms",
              "over_field_name": "api_endpoint",
              "partition_field_name": "environment"
            },
            {
              "detector_description": "Spike in mean response time by endpoint",
              "function": "mean",
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
    
    try:
        # Create the job with a unique ID
        response = es.ml.put_job(job_id=unique_job_id, body=job_config)
        print(f"Job created successfully: {response['job_id']}")
        
        # Create a datafeed
        datafeed_id = f"{unique_job_id}-datafeed"
        datafeed_config = {
            "job_id": unique_job_id,
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Datafeed created: {datafeed_id}")
        
        return unique_job_id
    except Exception as e:
        print(f"Error creating response time job: {e}")
        return None

def create_error_rate_job(es, job_id="api_error_rate_anomalies"):
    """Create a job to detect error rate anomalies"""
    # Generate unique job ID to avoid conflicts with existing jobs
    timestamp = int(time.time())
    unique_job_id = f"{job_id}-{timestamp}"
    
    print(f"Creating error rate anomaly detection job: {unique_job_id}")
    
    job_config = {
        "description": "Monitors API error rates across environments",
        "analysis_config": {
          "bucket_span": "10m",
          "detectors": [
            {
              "detector_description": "High count of errors by endpoint and environment",
              "function": "count",
              "by_field_name": "api_endpoint",
              "partition_field_name": "environment"
            },
            {
              "detector_description": "Time of day error patterns",
              "function": "count"
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
    
    try:
        # Create the job with a unique ID
        response = es.ml.put_job(job_id=unique_job_id, body=job_config)
        print(f"Job created successfully: {response['job_id']}")
        
        # Create a datafeed
        datafeed_id = f"{unique_job_id}-datafeed"
        datafeed_config = {
            "job_id": unique_job_id,
            "indices": ["api_metrics*"],
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "is_error": True } }  # Filter for error events in the datafeed instead
                    ]
                }
            }
        }
        
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Datafeed created: {datafeed_id}")
        
        return unique_job_id
    except Exception as e:
        print(f"Error creating error rate job: {e}")
        return None

def create_cross_environment_job(es, job_id="cross_environment_anomalies"):
    """Create a job to correlate patterns across environments"""
    # Generate unique job ID to avoid conflicts with existing jobs
    timestamp = int(time.time())
    unique_job_id = f"{job_id}-{timestamp}"
    
    print(f"Creating cross-environment correlation job: {unique_job_id}")
    
    job_config = {
        "description": "Correlates patterns across environments to detect cross-environment issues",
        "analysis_config": {
          "bucket_span": "30m",
          "detectors": [
            {
              "detector_description": "Mean response time by API across environments",
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
    
    try:
        # Create the job with the unique ID
        response = es.ml.put_job(job_id=unique_job_id, body=job_config)
        print(f"Job created successfully: {response['job_id']}")
        
        # Create a datafeed
        datafeed_id = f"{unique_job_id}-datafeed"
        datafeed_config = {
            "job_id": unique_job_id,
            "indices": ["api_metrics*"],
            "query": {"match_all": {}}
        }
        
        es.ml.put_datafeed(datafeed_id=datafeed_id, body=datafeed_config)
        print(f"Datafeed created: {datafeed_id}")
        
        return unique_job_id
    except Exception as e:
        print(f"Error creating cross-environment job: {e}")
        return None

def start_job_datafeed(es, job_id):
    """Start the datafeed for a job"""
    datafeed_id = f"{job_id}-datafeed"
    
    try:
        # First open the job (fix for the closed job issue)
        es.ml.open_job(job_id=job_id)
        print(f"Opened job: {job_id}")
        
        # Start the datafeed
        es.ml.start_datafeed(datafeed_id=datafeed_id, start="now-7d")
        print(f"Started datafeed: {datafeed_id}")
        return True
    except Exception as e:
        print(f"Error starting datafeed: {e}")
        return False

def main():
    print("=== Machine Learning Job Creator for API Monitoring ===\n")
    
    # Connect to Elasticsearch
    es = connect_to_elasticsearch()
    if not es:
        print("Exiting due to connection issues.")
        return
    
    # Create directories for storing job configurations
    os.makedirs("jobs", exist_ok=True)
    
    print("\nSelect ML job type to create:")
    print("1. Response Time Anomaly Detection")
    print("2. Error Rate Anomaly Detection")
    print("3. Cross-Environment Correlation")
    print("4. Create All Jobs (recommended for full monitoring)")
    
    choice = input("\nEnter your choice (1-4): ")
    
    created_jobs = []
    
    if choice == "1" or choice == "4":
        job_id = create_response_time_job(es)
        if job_id:
            created_jobs.append(job_id)
            start_job_datafeed(es, job_id)
    
    if choice == "2" or choice == "4":
        job_id = create_error_rate_job(es)
        if job_id:
            created_jobs.append(job_id)
            start_job_datafeed(es, job_id)
    
    if choice == "3" or choice == "4":
        job_id = create_cross_environment_job(es)
        if job_id:
            created_jobs.append(job_id)
            start_job_datafeed(es, job_id)
    
    if created_jobs:
        print("\n=== Created Jobs Summary ===")
        for idx, job_id in enumerate(created_jobs, 1):
            print(f"{idx}. {job_id}")
        
        print("\n=== Next Steps ===")
        print("1. Wait for the ML jobs to gather data (at least 20 minutes)")
        print("2. View the ML jobs in Kibana:")
        print("   Machine Learning > Anomaly Detection")
        print("3. To create alerts for these jobs, run create_kibana_objects.py")
        print("4. To test the jobs, run trigger_anomaly.py")
    else:
        print("\nNo jobs were created. Please check the logs above for errors.")

if __name__ == "__main__":
    main() 