@echo off
rem Cloud environment configuration for API Monitoring System

rem Debug and logging settings
set DEBUG=False
set LOG_LEVEL=INFO
set HOST=0.0.0.0
set PORT=8000

rem Skip Kibana initialization
set SKIP_KIBANA_INIT=True

rem MongoDB configuration - add explicit database name 'api_monitoring'
set MONGODB_URI=mongodb+srv://santosharron:bNqSxhz3MJ9koiD4@cluster0.aufgz7y.mongodb.net/api_monitoring?retryWrites=true^&w=majority^&appName=Cluster0^&connectTimeoutMS=30000^&socketTimeoutMS=30000^&serverSelectionTimeoutMS=30000^&maxIdleTimeMS=45000

rem Elasticsearch configuration - update with the correct credentials
set ELASTICSEARCH_CLOUD_ID=ai-agent-monitoring:dXMtZWFzdC0yLmF3cy5lbGFzdGljLWNsb3VkLmNvbSRhYTE2ODUyNDVhODM0NzM3YTFjZTFhMmU0ZWFlN2Y1MCQyYmU1YWExYzQxOTg0NDFhOTI1YzQ2MDMxZjI0Nzc0Mg==
rem Using basic authentication instead of API key
set ELASTICSEARCH_USERNAME=elastic
set ELASTICSEARCH_PASSWORD=KIuc03ZYAf6IqGkE1zEap1DR
rem set ELASTICSEARCH_API_KEY=ZVQ0SjdKVUJkaDl6bzZEMzRCMkE6ckgxc185OEpRV1dzeEwwUEtwLWNLQQ==
set ELASTICSEARCH_HOSTS=

rem Redis settings (default to localhost since we're focusing on MongoDB and Elasticsearch)
set REDIS_HOST=localhost
set REDIS_PORT=6379

echo MongoDB URI: %MONGODB_URI:~0,25%...%MONGODB_URI:~-10%
echo Elasticsearch Cloud ID: %ELASTICSEARCH_CLOUD_ID:~0,20%...
echo Environment variables set for cloud operation 