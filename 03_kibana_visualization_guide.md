# API Monitoring Visualization Guide with Kibana

This guide will help you customize and extend the automatically generated dashboards in Kibana created by your API monitoring system.

## Accessing Your Dashboards

Your application has already created several default dashboards:

1. Navigate to Elastic Cloud dashboard: https://cloud.elastic.co
2. Log in with your credentials
3. Select your deployment (ai-agent-monitoring)
4. Click on "Kibana" to open the Kibana interface
5. Go to Dashboard → Open to see your existing dashboards:
   - API Overview Dashboard
   - Anomaly Detection Dashboard
   - Cross-Environment Analysis Dashboard

## Enhancing the API Overview Dashboard

This dashboard shows the general health of your APIs across environments. To enhance it:

1. Open the "API Overview" dashboard
2. Click "Edit" in the top right
3. Add these visualizations:

### Response Time Distribution by Environment

1. Click "Create visualization"
2. Select "Lens"
3. From "api_metrics" index pattern:
   - Add "environment" to breakdown
   - Y-axis metric: Average of "response_time"
   - Configure color range: Below 200ms (green), 200-500ms (yellow), Above 500ms (red)
4. Save as "Response Time by Environment"

### API Health Status Grid

1. Create a new "Gauge" visualization
2. Select "api_metrics" index pattern
3. Configure:
   - Metrics: "Average response_time" and "Max error_rate"
   - Bucket: Split series by "api_id" and "environment"
   - Set thresholds: Green (<200ms), Yellow (200-500ms), Red (>500ms)
4. Save as "API Health Status Grid"

### Top Slowest Endpoints

1. Create a new "Data Table" visualization
2. Configure:
   - Metrics: "Average response_time" (descending sort)
   - Bucket: Split rows by "endpoint" and "environment"
   - Set size to 10 (top 10 slowest endpoints)
3. Save as "Top Slowest Endpoints"

## Customizing the Anomaly Detection Dashboard

The anomaly detection dashboard shows detected anomalies. Enhance it with:

### Anomaly Timeline

1. Create a new "Line" visualization
2. Use "anomalies" index pattern
3. Configure:
   - X-axis: "timestamp" with date histogram
   - Y-axis: Count of anomalies
   - Split series by "anomaly_type" and "environment"
4. Save as "Anomaly Timeline"

### Severity Distribution Chart

1. Create a "Pie Chart" visualization
2. Configure:
   - Metric: Count
   - Bucket: Split slices by "severity" ranges
   - Use ranges: Critical (>80), Major (60-80), Minor (40-60), Warning (<40)
3. Save as "Anomaly Severity Distribution"

### Anomaly Table with Context

1. Create a new "Data Table" visualization
2. Configure:
   - Columns: timestamp, api_id, environment, type, severity, description
   - Sort by: severity (descending)
   - Add filter for high severity: severity > 50
3. Save as "High Severity Anomalies"

## Enhancing Cross-Environment Dashboard

This dashboard correlates data across environments:

### Environment Comparison Chart

1. Create a new "Bar Chart" visualization
2. Configure:
   - X-axis: "environment"
   - Y-axis: Average "response_time"
   - Split series by "api_id"
3. Save as "Environment Response Time Comparison"

### Cross-Environment Request Flow

1. Create a new "Vega" visualization 
2. Use a Sankey diagram to show request flow between environments
3. Configure data source to use "api_metrics" with aggregations by source and destination environments
4. Save as "Cross-Environment Request Flow"

## Setting Up Alerting

1. Go to Stack Management → Rules and Connectors
2. Create new rule:
   - Rule type: "Threshold"
   - Index: "api_metrics"
   - Condition: avg(response_time) > 500 OR max(error_rate) > 0.05
   - Filter by: environment
3. Configure actions:
   - Slack notification
   - Email alert
   - Custom webhook to incident management system

## Creating a Custom Executive Dashboard

Create a high-level dashboard for executives:

1. Create a new dashboard named "Executive Overview"
2. Add:
   - "API Health Status" metric visualization
   - "Response Time Trend" line chart
   - "Error Rate by Environment" pie chart
   - "Recent Anomalies" table
   - "Predictive Health Forecast" visualization

## Organizing Your Dashboards

Create a dashboard hierarchy:

1. Go to Dashboard
2. Use "Organize in spaces" feature
3. Create spaces for:
   - Operations: Technical dashboards with detailed metrics
   - Management: High-level dashboards with business impact
   - Alerting: Dashboards focused on active issues

## Sharing Dashboards

To share dashboards with stakeholders:

1. Open the dashboard you want to share
2. Click "Share" in the top right
3. Options:
   - Generate short URL
   - Embed in iframe (for internal portals)
   - Export as PDF (for reports)
   - Set up scheduled reports via "Reporting" feature

## Dashboard Maintenance

- Review dashboard performance quarterly
- Update API endpoint list as new endpoints are added
- Adjust anomaly thresholds based on operational experience
- Archive historical dashboards as baseline changes 