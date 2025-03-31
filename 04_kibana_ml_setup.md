# Setting Up Machine Learning in Kibana for API Monitoring

## Prerequisites

- Ensure your Elastic Stack deployment has ML enabled
- Your user account must have the `machine_learning_admin` role

## Creating Anomaly Detection Jobs

### 1. Response Time Anomaly Detection

1. Navigate to Machine Learning > Anomaly Detection
2. Click "Create job"
3. Select "Multi-metric job"
4. Configure data source:
   - Index pattern: `api_metrics*`
   - Time field: `@timestamp`
5. Configure job settings:
   - Job ID: `api_response_time_anomalies`
   - Job description: "Detects anomalies in API response times across environments"
   - Bucket span: `15m` (adjust based on your API call frequency)
6. Configure analysis:
   - Split data by: `api_name` and `environment`
   - Metric: avg(`response_time`)
   - Add additional metric: max(`response_time`)
7. Set influencers: `api_name`, `environment`, `service_name`
8. Create job and start datafeeds

### 2. Error Rate Anomaly Detection

1. Create a new anomaly detection job
2. Configure data source:
   - Index pattern: `api_errors*`
   - Time field: `@timestamp`
3. Configure job settings:
   - Job ID: `api_error_rate_anomalies`
   - Bucket span: `10m`
4. Configure analysis:
   - Split data by: `api_name` and `environment`
   - Metric: count()
   - Add additional metric: sum(`error_count`)
5. Create job and start datafeeds

### 3. Cross-Environment Correlation

1. Create a new anomaly detection job
2. Configure as a "Population analysis" job type
3. Configure data source:
   - Index pattern: `api_transactions*`
4. Configure job:
   - Split data by: `request_journey_id`
   - Over fields: `environment`
   - Population metric: avg(`response_time`)
5. Create job and start datafeeds

## Creating Custom Machine Learning Models

For more advanced predictive analytics:

1. Navigate to Machine Learning > Data Frame Analytics
2. Click "Create analytics job"
3. Select job type:
   - "Regression" for response time prediction
   - "Outlier detection" for identifying unusual API behavior
4. Configure source index:
   - Use processed API metrics index
5. Configure destination index
6. Select features for training
7. Create and start job

## Incorporating ML Results in Dashboards

1. In Kibana Dashboards, add an "Anomaly Chart" visualization
2. Select the anomaly detection job(s) to display
3. Configure anomaly score thresholds:
   - Critical: 75+
   - Major: 50-75
   - Minor: 25-50
   - Warning: <25
4. Add annotations to highlight detected anomalies on time series charts

## Setting Up Alerts for ML Results

1. Go to Stack Management > Rules and Connectors
2. Create new rule:
   - Type: "Machine Learning"
   - Trigger: "Anomaly detection rule"
   - Select job(s) to monitor
   - Set severity threshold (e.g., 75)
3. Configure actions:
   - Slack notifications
   - Email alerts
   - Webhook to incident management system

## ML Maintenance

- Review ML job performance weekly
- Retrain models monthly or when system behavior changes significantly
- Adjust anomaly thresholds based on false positive/negative rates
- Archive and maintain historical ML results 