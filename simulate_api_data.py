"""
API Data Simulator

This script generates both normal and anomalous API data in Elasticsearch
to test machine learning jobs and alert rules.
"""
import os
import random
import time
import json
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import argparse

# Configuration parameters (from environment or defaults)
ELASTICSEARCH_CLOUD_ID = os.getenv("ELASTICSEARCH_CLOUD_ID", 
                                  "ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "KIuc03ZYAf6IqGkE1zEap1DR")

# API service configurations
SERVICES = [
    {
        "api_id": "user-service",
        "endpoints": ["/users", "/users/{id}", "/users/auth", "/users/profile"],
        "base_response_time": {"production": 75, "staging": 95, "development": 120},
        "error_probability": {"production": 0.005, "staging": 0.02, "development": 0.04}
    },
    {
        "api_id": "order-service",
        "endpoints": ["/orders", "/orders/{id}", "/orders/status", "/orders/history"],
        "base_response_time": {"production": 90, "staging": 110, "development": 140},
        "error_probability": {"production": 0.008, "staging": 0.025, "development": 0.05}
    },
    {
        "api_id": "payment-service",
        "endpoints": ["/payments", "/payments/process", "/payments/{id}", "/payments/verify"],
        "base_response_time": {"production": 120, "staging": 150, "development": 180},
        "error_probability": {"production": 0.01, "staging": 0.03, "development": 0.06}
    },
    {
        "api_id": "inventory-service",
        "endpoints": ["/inventory", "/inventory/{id}", "/inventory/status", "/inventory/update"],
        "base_response_time": {"production": 85, "staging": 105, "development": 130},
        "error_probability": {"production": 0.007, "staging": 0.022, "development": 0.045}
    },
    {
        "api_id": "notification-service",
        "endpoints": ["/notifications", "/notifications/send", "/notifications/status", "/notifications/preferences"],
        "base_response_time": {"production": 65, "staging": 85, "development": 110},
        "error_probability": {"production": 0.004, "staging": 0.018, "development": 0.035}
    }
]

ENVIRONMENTS = ["production", "staging", "development"]

ERROR_TYPES = {
    "timeout": [408, "Request timed out"],
    "internal_error": [500, "Internal server error"],
    "bad_gateway": [502, "Bad gateway"],
    "service_unavailable": [503, "Service unavailable"],
    "gateway_timeout": [504, "Gateway timeout"]
}

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

def generate_request_id():
    """Generate a unique request ID"""
    return f"req-{int(time.time())}-{random.randint(1000, 9999)}"

def calculate_response_time(service, endpoint, environment, hour, day_of_week, is_anomaly=False):
    """Calculate a realistic response time for the given parameters"""
    base_response_time = service["base_response_time"][environment]
    
    # Time-based variation (peak hours between 9 AM and 5 PM)
    hour_factor = 1 + (0.5 if 9 <= hour <= 17 else 0)
    
    # Day-based variation (weekends have lower traffic)
    day_factor = 0.7 if day_of_week >= 5 else 1.0
    
    # Endpoint complexity factor
    if "{id}" in endpoint:  # Detail endpoints are slightly slower
        endpoint_factor = 1.1
    elif "auth" in endpoint or "process" in endpoint:  # Auth and processing endpoints are slower
        endpoint_factor = 1.3
    else:
        endpoint_factor = 1.0
        
    # Calculate response time with some randomness
    response_time = base_response_time * hour_factor * day_factor * endpoint_factor * random.uniform(0.8, 1.2)
    
    # If this is an anomaly, increase the response time significantly
    if is_anomaly:
        response_time *= random.uniform(4.0, 8.0)
    
    return response_time

def generate_error_event(service, endpoint, environment, is_anomaly=False):
    """Generate an error event with appropriate status code and error type"""
    error_probability = service["error_probability"][environment]
    
    # If this is an anomaly, dramatically increase error probability
    if is_anomaly:
        error_probability *= 10
    
    is_error = random.random() < error_probability
    
    if is_error:
        error_type = random.choice(list(ERROR_TYPES.keys()))
        status_code = ERROR_TYPES[error_type][0]
        error_count = 1
    else:
        error_type = None
        status_code = 200
        error_count = 0
    
    return is_error, error_type, status_code, error_count

def generate_normal_data(es, start_time, duration_days, data_points_per_service_per_hour=20):
    """Generate normal API data for the specified duration"""
    print(f"Generating normal data for {duration_days} days...")
    
    bulk_data = []
    docs_generated = 0
    
    now = datetime.now()
    end_time = now
    start_time = end_time - timedelta(days=duration_days)
    
    # Generate data for each hour in the time range
    current_time = start_time
    while current_time < end_time:
        hour = current_time.hour
        day_of_week = current_time.weekday()
        
        # For each service and environment
        for service in SERVICES:
            for environment in ENVIRONMENTS:
                # Generate multiple data points per hour
                for _ in range(data_points_per_service_per_hour):
                    # Pick a random endpoint
                    endpoint = random.choice(service["endpoints"])
                    
                    # Calculate response time
                    response_time = calculate_response_time(service, endpoint, environment, hour, day_of_week)
                    
                    # Determine if this is an error
                    is_error, error_type, status_code, error_count = generate_error_event(service, endpoint, environment)
                    
                    # Create document
                    doc = {
                        "_index": "api_metrics",
                        "_source": {
                            "@timestamp": current_time.isoformat(),
                            "api_id": service["api_id"],
                            "api_endpoint": endpoint,
                            "environment": environment,
                            "service_name": service["api_id"],
                            "response_time_ms": response_time,
                            "status_code": status_code,
                            "is_error": is_error,
                            "error_type": error_type,
                            "error_count": error_count,
                            "request_id": generate_request_id()
                        }
                    }
                    
                    bulk_data.append(doc)
                    docs_generated += 1
                    
                    # Index in batches of 1000 documents
                    if len(bulk_data) >= 1000:
                        try:
                            from elasticsearch.helpers import bulk
                            success, failed = bulk(es, bulk_data)
                            print(f"Indexed {success} documents, {len(failed) if failed else 0} failed")
                            bulk_data = []
                        except Exception as e:
                            print(f"Error indexing data: {e}")
        
        # Move to the next hour
        current_time += timedelta(hours=1)
        
        # Print progress every day
        if current_time.hour == 0:
            days_left = (end_time - current_time).days
            print(f"Progress: Generated data up to {current_time}, {days_left} days left")
    
    # Index any remaining documents
    if bulk_data:
        try:
            from elasticsearch.helpers import bulk
            success, failed = bulk(es, bulk_data)
            print(f"Indexed final batch: {success} documents, {len(failed) if failed else 0} failed")
        except Exception as e:
            print(f"Error indexing final batch: {e}")
    
    print(f"Normal data generation complete. Generated {docs_generated} documents.")
    return docs_generated

def inject_response_time_anomaly(es, service_id, environment, duration_minutes=30, data_points=50):
    """Inject a response time anomaly for a specific service and environment"""
    print(f"Injecting response time anomaly for {service_id} in {environment} environment...")
    
    service = next((s for s in SERVICES if s["api_id"] == service_id), None)
    if not service:
        print(f"Service {service_id} not found")
        return 0
    
    # Select a random endpoint or use the first one
    endpoint = random.choice(service["endpoints"]) if service["endpoints"] else service["endpoints"][0]
    
    # Time range for the anomaly (centered around current time)
    now = datetime.now()
    start_time = now - timedelta(minutes=duration_minutes/2)
    end_time = now + timedelta(minutes=duration_minutes/2)
    
    bulk_data = []
    docs_generated = 0
    
    # Generate anomalous data points
    time_interval = duration_minutes * 60 / data_points  # in seconds
    
    for i in range(data_points):
        # Calculate timestamp for this data point
        point_time = start_time + timedelta(seconds=i * time_interval)
        
        # Calculate anomalous response time
        current_hour = point_time.hour
        current_day = point_time.weekday()
        response_time = calculate_response_time(service, endpoint, environment, current_hour, current_day, is_anomaly=True)
        
        # Create document
        doc = {
            "_index": "api_metrics",
            "_source": {
                "@timestamp": point_time.isoformat(),
                "api_id": service["api_id"],
                "api_endpoint": endpoint,
                "environment": environment,
                "service_name": service["api_id"],
                "response_time_ms": response_time,
                "status_code": 200,  # Usually high response times don't result in errors
                "is_error": False,
                "error_count": 0,
                "request_id": generate_request_id()
            }
        }
        
        bulk_data.append(doc)
        docs_generated += 1
    
    # Index the documents
    try:
        from elasticsearch.helpers import bulk
        success, failed = bulk(es, bulk_data)
        print(f"Indexed {success} anomalous response time documents, {len(failed) if failed else 0} failed")
    except Exception as e:
        print(f"Error indexing anomalous response time data: {e}")
    
    print(f"Response time anomaly injection complete. Generated {docs_generated} documents.")
    return docs_generated

def inject_error_rate_anomaly(es, service_id, environment, duration_minutes=30, data_points=40):
    """Inject an error rate anomaly for a specific service and environment"""
    print(f"Injecting error rate anomaly for {service_id} in {environment} environment...")
    
    service = next((s for s in SERVICES if s["api_id"] == service_id), None)
    if not service:
        print(f"Service {service_id} not found")
        return 0
    
    # Select a random endpoint or use the first one
    endpoint = random.choice(service["endpoints"]) if service["endpoints"] else service["endpoints"][0]
    
    # Time range for the anomaly (centered around current time)
    now = datetime.now()
    start_time = now - timedelta(minutes=duration_minutes/2)
    end_time = now + timedelta(minutes=duration_minutes/2)
    
    bulk_data = []
    docs_generated = 0
    
    # Generate anomalous data points
    time_interval = duration_minutes * 60 / data_points  # in seconds
    
    for i in range(data_points):
        # Calculate timestamp for this data point
        point_time = start_time + timedelta(seconds=i * time_interval)
        
        # Calculate normal response time
        current_hour = point_time.hour
        current_day = point_time.weekday()
        response_time = calculate_response_time(service, endpoint, environment, current_hour, current_day)
        
        # Force errors for anomaly
        error_type_key = random.choice(list(ERROR_TYPES.keys()))
        status_code = ERROR_TYPES[error_type_key][0]
        
        # Create document
        doc = {
            "_index": "api_metrics",
            "_source": {
                "@timestamp": point_time.isoformat(),
                "api_id": service["api_id"],
                "api_endpoint": endpoint,
                "environment": environment,
                "service_name": service["api_id"],
                "response_time_ms": response_time,
                "status_code": status_code,
                "is_error": True,
                "error_type": error_type_key,
                "error_count": 1,
                "request_id": generate_request_id()
            }
        }
        
        bulk_data.append(doc)
        docs_generated += 1
    
    # Index the documents
    try:
        from elasticsearch.helpers import bulk
        success, failed = bulk(es, bulk_data)
        print(f"Indexed {success} anomalous error rate documents, {len(failed) if failed else 0} failed")
    except Exception as e:
        print(f"Error indexing anomalous error rate data: {e}")
    
    print(f"Error rate anomaly injection complete. Generated {docs_generated} documents.")
    return docs_generated

def inject_cross_environment_anomaly(es, service_id, duration_minutes=30, data_points_per_env=20):
    """Inject anomalies across multiple environments for the same service"""
    print(f"Injecting cross-environment anomaly for {service_id} across all environments...")
    
    service = next((s for s in SERVICES if s["api_id"] == service_id), None)
    if not service:
        print(f"Service {service_id} not found")
        return 0
    
    docs_generated = 0
    
    # Inject anomalies in each environment with a slight delay between them
    delay_between_envs = 5  # minutes
    
    for i, environment in enumerate(ENVIRONMENTS):
        # Calculate start time with increasing delay for each environment
        env_delay = i * delay_between_envs
        env_duration = duration_minutes - env_delay
        
        if env_duration <= 0:
            continue
        
        # Inject both response time and error anomalies
        docs_generated += inject_response_time_anomaly(
            es, service_id, environment, 
            duration_minutes=env_duration, 
            data_points=data_points_per_env
        )
        
        docs_generated += inject_error_rate_anomaly(
            es, service_id, environment, 
            duration_minutes=env_duration, 
            data_points=data_points_per_env
        )
    
    print(f"Cross-environment anomaly injection complete. Generated {docs_generated} documents.")
    return docs_generated

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description="Generate API metrics data with anomalies")
    
    # General options
    parser.add_argument("--mode", choices=["normal", "anomaly", "both"], default="both",
                       help="Data generation mode: normal data, anomalies, or both")
    
    # Normal data options
    parser.add_argument("--days", type=int, default=7,
                       help="Number of days of normal data to generate")
    parser.add_argument("--data-points", type=int, default=20,
                       help="Data points per service per hour for normal data")
    
    # Anomaly options
    parser.add_argument("--anomaly-type", choices=["response_time", "error_rate", "cross_environment", "all"], 
                       default="all", help="Type of anomaly to inject")
    parser.add_argument("--service", type=str, default="payment-service",
                       help="Service ID to inject anomalies for")
    parser.add_argument("--environment", type=str, default="production",
                       help="Environment to inject anomalies for")
    parser.add_argument("--duration", type=int, default=30,
                       help="Duration of anomaly in minutes")
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    es = connect_to_elasticsearch()
    if not es:
        print("Exiting due to connection issues.")
        return
    
    total_docs = 0
    
    # Generate normal data if requested
    if args.mode in ["normal", "both"]:
        total_docs += generate_normal_data(
            es, 
            datetime.now() - timedelta(days=args.days), 
            args.days, 
            args.data_points
        )
    
    # Inject anomalies if requested
    if args.mode in ["anomaly", "both"]:
        if args.anomaly_type in ["response_time", "all"]:
            total_docs += inject_response_time_anomaly(
                es,
                args.service,
                args.environment,
                args.duration
            )
        
        if args.anomaly_type in ["error_rate", "all"]:
            total_docs += inject_error_rate_anomaly(
                es,
                args.service,
                args.environment,
                args.duration
            )
        
        if args.anomaly_type in ["cross_environment", "all"]:
            total_docs += inject_cross_environment_anomaly(
                es,
                args.service,
                args.duration
            )
    
    print(f"\nData generation complete! Generated {total_docs} documents total.")
    print("\nNext steps:")
    print("1. Wait for ML jobs to process the data (~15-30 minutes)")
    print("2. Check for anomalies in Kibana > Machine Learning > Anomaly Detection")
    print("3. Verify that alerts were triggered for the anomalies")

if __name__ == "__main__":
    main() 