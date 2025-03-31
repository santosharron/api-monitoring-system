#!/bin/bash
# Cloud environment configuration for API Monitoring System

# Debug and logging settings
export DEBUG=False
export LOG_LEVEL=INFO
export HOST=0.0.0.0
export PORT=8000

# Skip Kibana initialization
export SKIP_KIBANA_INIT=True

# MongoDB configuration - with explicit database name
export MONGODB_URI="mongodb+srv://santosharron:bNqSxhz3MJ9koiD4@cluster0.aufgz7y.mongodb.net/api_monitoring?retryWrites=true&w=majority&appName=Cluster0&connectTimeoutMS=30000&socketTimeoutMS=30000&serverSelectionTimeoutMS=30000&maxIdleTimeMS=45000"

# Elasticsearch configuration
export ELASTICSEARCH_CLOUD_ID="ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg=="
# Using basic authentication instead of API key
export ELASTICSEARCH_USERNAME="elastic"
export ELASTICSEARCH_PASSWORD="KIuc03ZYAf6IqGkE1zEap1DR"
# export ELASTICSEARCH_API_KEY="ZVQ0SjdKVUJkaDl6bzZEMzRCMkE6ckgxc185OEpRV1dzeEwwUEtwLWNLQQ=="
export ELASTICSEARCH_HOSTS=""

# Redis settings (default to localhost since we're focusing on MongoDB and Elasticsearch)
export REDIS_HOST=localhost
export REDIS_PORT=6379

echo "MongoDB URI: ${MONGODB_URI:0:25}...${MONGODB_URI: -10}"
echo "Elasticsearch Cloud ID: ${ELASTICSEARCH_CLOUD_ID:0:20}..."
echo "Environment variables set for cloud operation" 