# Setting Up Machine Learning in Kibana for API Monitoring

This guide explains how to enhance your API monitoring system with Kibana's machine learning capabilities, building on the automated setup already provided by your application.

## Prerequisites

- Your API monitoring application is running with Elasticsearch Cloud connection
- You have verified data is flowing to the `api_metrics` and `anomalies` indices
- Your Elastic Cloud account has ML capabilities enabled
- You have the `machine_learning_admin` role

## Accessing Machine Learning Jobs

The API monitoring system automatically creates basic ML jobs. To access them:

1. In Kibana, navigate to Machine Learning > Anomaly Detection
2. You should see the following jobs already created:
   - `api_response_time_anomalies` - Detects unusual response times
   - `api_error_rate_anomalies` - Identifies error rate spikes

If these jobs aren't visible, follow the instructions below to create them.

## Enhancing the Response Time Anomaly Detection Job

1. Navigate to Machine Learning > Anomaly Detection
2. Find `api_response_time_anomalies` and click "Edit"
3. Click "Advanced" to customize settings:
   - Increase model memory limit if needed
   - Adjust anomaly score threshold (default: 75)
   - Fine-tune influencer weights to emphasize environment or API name
4. Click "Save" to update the job

## Creating Advanced Multi-Metric Analysis

Create a more sophisticated analysis job for response patterns:

1. Navigate to Machine Learning > Anomaly Detection
2. Click "Create job" > "Multi-metric"
3. Configure data source:
   - Index pattern: `api_metrics*`
   - Time field: `@timestamp`
4. Configure analysis:
   - Split data by: `api_id` and `environment`
   - Primary metric: avg(`response_time`)
   - Add metrics: 
     - max(`response_time`)
     - min(`response_time`)
     - count() 
     - sum(`error_count`)
5. Set influencers: `api_id`, `environment`, `endpoint`
6. Job settings:
   - Job ID: `api_advanced_metrics_anomalies`
   - Description: "Comprehensive API performance analysis"
   - Bucket span: `5m` (adjust based on your traffic volume)
7. Create and start the job

## Setting Up Cross-Environment Correlation

Create a population analysis job to detect environment-specific issues:

1. Create a new anomaly detection job
2. Select "Population analysis" job type
3. Configure data source:
   - Index pattern: `api_metrics*`
4. Configure population:
   - Field: `api_id` (this creates populations of the same API across environments)
   - By: `environment` (this compares the same API across different environments)
   - Metric: avg(`response_time`)
5. Job settings:
   - Job ID: `cross_environment_api_analysis`
   - Bucket span: `15m`
6. Create and start the job

## Creating Predictive Models with Data Frame Analytics

For forecasting future API performance:

1. Navigate to Machine Learning > Data Frame Analytics
2. Click "Create analytics job"
3. Select "Regression" analysis
4. Configure source:
   - Index pattern: `api_metrics*`
   - Query filter: Use a specific time range for training data
5. Feature selection:
   - Training features: response_time, status_code, timestamp (as feature), environment, endpoint
   - Dependent variable: response_time
6. Job settings:
   - Job ID: `api_response_time_prediction`
   - Description: "Predict future API response times"
7. Create and start the job

## Setting Up Anomaly Detection Rules

Create rules that trigger when ML jobs detect anomalies:

1. Go to Stack Management > Rules and Connectors
2. Create new rule:
   - Type: "Machine Learning"
   - Jobs: Select your ML jobs
   - Severity threshold: 75 (adjust based on sensitivity needs)
3. Configure actions:
   - Slack notification with anomaly details
   - Email with a link to the anomaly explorer
   - Custom webhook to your incident management system

## Creating ML Results Dashboards

Build dashboards to visualize ML job results:

1. Create a new dashboard: "ML Insights Dashboard"
2. Add these visualizations:
   - Anomaly heatmap by API and environment
   - Anomaly timeline with severity indicated by color
   - Top anomalous APIs table
   - Anomaly count by influencer

### Adding ML Annotations to Existing Charts

1. Edit your API Response Time visualization
2. Add annotations from ML results:
   - Click "Options" > "Annotations"
   - Select your ML job as the source
   - Choose severe anomalies (score > 75)

## Customizing ML Detectors

If you need to adjust specific detectors within jobs:

1. Go to Machine Learning > Anomaly Detection
2. Select your job and click "Edit"
3. Go to "Detectors" tab
4. Click "Edit" next to a detector
5. Adjust detector settings:
   - Function: Change the function (e.g., mean to median)
   - Field: Select different metrics to analyze
   - Description: Update to reflect changes

## Maintaining ML Jobs

To maintain optimal ML performance:

1. Monitor memory usage in ML Jobs list
2. Calibrate anomaly thresholds based on false positives/negatives
3. Periodically close and reopen jobs to incorporate new patterns
4. Create calendar events for expected anomalies (e.g., maintenance windows)

For advanced needs:
- Use custom rules for multi-condition alerting
- Set up forecasting to predict future anomalies
- Create dashboard links between regular metrics and ML insights 