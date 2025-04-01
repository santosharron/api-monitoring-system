# Initial Setup Commands for API Monitoring System

Before proceeding with Kibana visualizations, follow these steps to ensure your monitoring system is properly set up and sending data to Elasticsearch.

## 1. Environment Configuration

Your `.env` file is already configured with proper Elasticsearch and MongoDB credentials:

```bash
# Verify Elasticsearch credentials
cat .env | grep ELASTICSEARCH
```

Make sure these settings match your Elastic Cloud deployment:
- `ELASTICSEARCH_CLOUD_ID`: Your Elastic Cloud deployment ID
- `ELASTICSEARCH_USERNAME`: Set to "elastic"  
- `ELASTICSEARCH_PASSWORD`: Your Elastic Cloud password

## 2. Start the Monitoring Application

Navigate to your application directory and start the system:

```bash
# Start the application
python src/main.py
```

Verify it's running correctly by checking the console output. You should see:
- "API Monitoring System started successfully"
- "Elasticsearch connection established"
- "Initializing Kibana dashboards..." 

## 3. Verify Data Flow

After starting the application, verify data is flowing to Elasticsearch:

```bash
# Check if indices are being created
curl -u elastic:KIuc03ZYAf6IqGkE1zEap1DR https://aa16852445a8347347a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:9243/_cat/indices

# Check document count in api metrics index
curl -u elastic:KIuc03ZYAf6IqGkE1zEap1DR https://aa16852445a8347347a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:9243/api_metrics/_count
```

You should see at least these indices:
- `api_metrics` - Contains API performance data
- `anomalies` - Contains detected anomalies

## 4. Check Application Health

Use the application's built-in health endpoint:

```bash
# Check application health
curl http://localhost:8000/health
```

This should return a JSON response showing all components running:
- `collector_manager`: "running"
- `analyzer_manager`: "running" 
- `alert_manager`: "running"
- `kibana_dashboards`: "initialized"
- `database`: Both Elasticsearch and MongoDB should show "available"

## 5. Check Dashboard Availability

The application automatically initializes default dashboards in Kibana. Verify they're available:

```bash
# Check available dashboards
curl http://localhost:8000/dashboards
```

This should return a list of available dashboards including:
- "API Overview"
- "Anomaly Detection"
- "Cross-Environment Analysis"

## 6. Access Kibana

Now you can access Kibana directly to view your dashboards:

1. Navigate to Elastic Cloud dashboard: https://cloud.elastic.co
2. Log in with your Elastic credentials
3. Select your deployment (ai-agent-monitoring)
4. Click on "Kibana" 

## 7. Verify Index Patterns

Before proceeding, verify that Kibana has the necessary index patterns:

1. In Kibana, go to Stack Management > Index Patterns
2. You should see these patterns created by the application:
   - `api_metrics*`
   - `api-anomalies*` 
   - `api-predictions*`

If any are missing, you can manually create them with the following settings:
- Pattern: The name of the missing pattern
- Time field: "timestamp"

Once all these steps are completed successfully, proceed to the Kibana visualization guide. 