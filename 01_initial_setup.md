# Initial Setup Commands for API Monitoring System

Before proceeding with Kibana visualizations, run these commands to ensure your monitoring system is properly set up and data is flowing to Elasticsearch.

## 1. Environment Setup

Ensure your `.env` file is properly configured with Elasticsearch credentials:

```bash
# Verify your .env file contains the correct Elasticsearch settings
cat .env | grep ELASTICSEARCH
```

## 2. Start the Monitoring Application

Start the API monitoring application:

```bash
# Navigate to your application directory
cd /path/to/api-monitoring-system

# Start the application
python main.py
```

Verify it's running correctly by checking the logs for successful connection messages.

## 3. Verify Data is Flowing to Elasticsearch

Check that data is being sent to Elasticsearch:

```bash
# Using curl to check the indices (replace with your credentials)
curl -u elastic:KIuc03ZYAf6IqGkE1zEap1DR https://aa16852445a8347347a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:9243/_cat/indices

# Or use the Elasticsearch API to check document count
curl -u elastic:KIuc03ZYAf6IqGkE1zEap1DR https://aa16852445a8347347a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:9243/api_metrics*/_count
```

## 4. Install Required Tools

If not already installed, install necessary tools:

```bash
# Install Elastic CLI (optional, for easier management)
pip install elastic-transport elasticsearch

# Install visualization tools if working locally
pip install matplotlib seaborn pandas
```

## 5. Configure Index Patterns in Kibana

Before creating visualizations, set up index patterns in Kibana:

1. Log in to Kibana
2. Go to Stack Management > Index Patterns
3. Create patterns for:
   - `api_metrics*` - For API performance metrics
   - `api_errors*` - For error tracking
   - `api_transactions*` - For transaction data

## 6. Import Sample Dashboards (Optional)

To jumpstart visualization:

```bash
# Using elasticdump to import dashboards (if you have prepared templates)
npm install elasticdump -g
elasticdump --input=./dashboards/api_monitoring_dashboards.json --output=https://elastic:KIuc03ZYAf6IqGkE1zEap1DR@aa16852445a8347347a1ce1a2e4eae7f50.us-east-2.aws.elastic-cloud.com:9243/.kibana --type=data
```

## 7. Verify Monitoring Components

Ensure all components of your monitoring system are operational:

```bash
# Check collector status
python -c "from app.collectors import status; status.check_all()"

# Verify analyzer components
python -c "from app.analyzers import status; status.check_all()"

# Test alert system connection
python -c "from app.alerting import test; test.connection()"
```

After completing these steps, proceed to the Kibana visualization setup. 