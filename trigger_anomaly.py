"""
Anomaly Trigger Script

This script injects anomalous data points into the Elasticsearch index 
to trigger the anomaly detection mechanism and test alerts.
"""
import os
import random
import time
from datetime import datetime
from elasticsearch import Elasticsearch

# Get credentials from environment variables if available
ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", 
                                 "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")

print("Connecting to Elasticsearch...")
try:
    # Connect to Elasticsearch
    es = Elasticsearch(
        cloud_id=ELASTICSEARCH_CLOUD_ID,
        basic_auth=(ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
    )
    
    # Test connection
    info = es.info()
    print(f"Successfully connected to Elasticsearch cluster: {info['cluster_name']}")
except Exception as e:
    print(f"Failed to connect to Elasticsearch: {e}")
    print("Please check your credentials and network connection.")
    exit(1)

def inject_response_time_anomaly():
    """Inject unusually high response times to trigger response time anomaly detection"""
    print("\nInjecting response time anomalies...")
    
    # Create 20 data points with very high response times
    for i in range(20):
        doc = {
            "@timestamp": datetime.now().isoformat(),
            "api_id": "user-service",
            "api_endpoint": "/users",
            "environment": "production",
            "service_name": "user-service",
            "response_time_ms": 2500 + random.uniform(0, 500),  # Very high response time
            "status_code": 200,
            "is_error": False,
            "error_count": 0,
            "request_id": f"req-{int(time.time())}-{random.randint(1000, 9999)}"
        }
        
        # Insert the document
        es.index(index="api_metrics", document=doc)
        print(f"Inserted anomalous response time data point {i+1}/20")
        time.sleep(2)  # Space out the insertions

def inject_error_rate_anomaly():
    """Inject high error rates to trigger error rate anomaly detection"""
    print("\nInjecting error rate anomalies...")
    
    # Create 15 data points with errors
    for i in range(15):
        doc = {
            "@timestamp": datetime.now().isoformat(),
            "api_id": "payment-service",
            "api_endpoint": "/payments/process",
            "environment": "production",
            "service_name": "payment-service",
            "response_time_ms": 150 + random.uniform(0, 30),
            "status_code": 500,
            "is_error": True,
            "error_type": "internal_error",
            "error_count": 1,
            "request_id": f"req-{int(time.time())}-{random.randint(1000, 9999)}"
        }
        
        # Insert the document
        es.index(index="api_metrics", document=doc)
        print(f"Inserted anomalous error data point {i+1}/15")
        time.sleep(2)  # Space out the insertions

def main():
    print("=== Anomaly Trigger Tool ===")
    print("This tool will inject anomalous data to trigger ML job alerts")
    print("Choose an anomaly type to inject:")
    print("1. Response Time Anomaly (high response times)")
    print("2. Error Rate Anomaly (high error rates)")
    print("3. Both Anomaly Types")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        inject_response_time_anomaly()
    elif choice == "2":
        inject_error_rate_anomaly()
    elif choice == "3":
        inject_response_time_anomaly()
        inject_error_rate_anomaly()
    else:
        print("Invalid choice. Please run the script again and select 1, 2, or 3.")
        return
    
    print("\nAnomalous data injection completed!")
    print("Notes:")
    print("1. It may take 10-15 minutes for the ML job to process the new data")
    print("2. Check ML results in Kibana: Machine Learning > Anomaly Detection > [Your Job] > View Results")
    print("3. If alerts are configured correctly, they should trigger shortly after the anomaly is detected")

if __name__ == "__main__":
    main() 