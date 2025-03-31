# API Monitoring System Cloud Demonstration Guide

This guide provides step-by-step instructions for demonstrating the API Monitoring System using cloud services at a hackathon.

## 1. Setup & Preparation

### Prerequisites
- MongoDB Atlas account (for cloud database)
- Elasticsearch Cloud account
- AWS/Azure/GCP account(s) for hosting demonstration APIs
- Windows or Linux-based system to run the control components

### Environment Configuration
1. Clone the repository to your local machine:
```bash
git clone https://github.com/yourusername/api-monitoring-system.git
cd api-monitoring-system
```

2. Create a Python virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# Copy the example env file
cp .env.example .env

# Edit the .env file with your cloud credentials:
# - MongoDB Atlas connection string: mongodb+srv://santosharron:bNqSxhz3MJ9koiD4@cluster0.aufgz7y.mongodb.net/api_monitoring?retryWrites=true&w=majority&appName=Cluster0
# - Elasticsearch Cloud ID: My_Observability_project:dXMtZWFzdC0xLmF3cy5lbGFzdGljLmNsb3VkJGYzNDUyYThlZDkwMTRmMWNhMjE3MmQxMDcyNjRmMTAzLmVzJGYzNDUyYThlZDkwMTRmMWNhMjE3MmQxMDcyNjRmMTAz
# - Elasticsearch API Key: eUVzVzY1VUI4Y3dvcnUtT2Y3MWY6bk9xWGNlUTkwZUpDSkFxd2w5UzJCdw==
```

## 2. Launching the System

### Starting the Cloud Services

1. Start the system using the cloud configuration:
```bash
# On Windows
D:\tmp\api-monitoring-system\start_cloud.bat

# On Linux/Mac
./start_cloud.sh
```

This script:
- Loads cloud environment variables from cloud_env.bat/sh
- Verifies MongoDB connection
- Starts the main application

2. Verify the system is running:
```bash
# Access the health check endpoint
curl http://localhost:8000/health
```

### Creating API Sources

1. Create real API monitoring sources:
```bash
python -m src.scripts.create_real_api
```

This script:
- Creates API configurations in MongoDB Atlas
- Sets up monitoring for APIs across different cloud environments (AWS, Azure, GCP)
- Configures appropriate thresholds for each environment

2. Generate test data:
```bash
python -m src.scripts.generate_test_data
```

## 3. Accessing Dashboards and Monitoring Results

### Visualization Access Points

1. **Kibana Dashboard**:
   ```
   http://localhost:5601
   ```
   The main visualization platform with three key dashboards:
   - API Overview Dashboard: Shows response times, error rates, and traffic patterns across all environments
   - Anomaly Detection Dashboard: Displays detected anomalies, their severity, and impact
   - Cross-Environment Analysis Dashboard: Shows correlations between issues across different cloud environments

2. **API Documentation**:
   ```
   http://localhost:8000/docs
   ```
   Interactive Swagger documentation for all API endpoints

3. **Available Dashboards List**:
   ```bash
   curl http://localhost:8000/dashboards
   ```
   Returns the URLs for all available dashboards

4. **System Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```
   Shows the status of all system components (collectors, analyzers, database connections)

### Core API Endpoints for Monitoring

1. **View API Sources**:
   ```bash
   curl http://localhost:8000/api/v1/sources
   ```

2. **View Metrics**:
   ```bash
   # All metrics
   curl http://localhost:8000/api/v1/metrics
   
   # Metrics for a specific API
   curl "http://localhost:8000/api/v1/metrics?api_id=aws-api-1"
   
   # Metrics for a specific environment
   curl "http://localhost:8000/api/v1/metrics?environment=aws"
   ```

3. **View Anomalies**:
   ```bash
   # All anomalies
   curl http://localhost:8000/api/v1/anomalies
   
   # High severity anomalies
   curl "http://localhost:8000/api/v1/anomalies?min_severity=0.7"
   ```

4. **View Predictions**:
   ```bash
   curl http://localhost:8000/api/v1/predictions
   ```

5. **View Alerts**:
   ```bash
   curl http://localhost:8000/api/v1/alerts
   ```

6. **Dashboard Summary**:
   ```bash
   curl http://localhost:8000/api/v1/dashboard/summary
   ```

## 4. Demonstration Script

### A. System Overview (5 minutes)

1. Show the architecture diagram from README.md
2. Access the system dashboard:
```bash
curl http://localhost:8000/dashboards
```

3. Open the Kibana dashboard URL displayed in the output
4. Show the three main dashboards:
   - API Overview
   - Anomaly Detection
   - Cross-Environment Analysis

### B. Normal Operations (5 minutes)

1. Show the API metrics across different cloud environments:
```bash
curl http://localhost:8000/api/v1/metrics
```

2. Explain the visualizations in the API Overview dashboard:
   - Response time across AWS, Azure, and GCP environments
   - Success rates by cloud provider
   - Traffic patterns
   - Environment distribution

3. Demonstrate an end-to-end request journey:
   - Show how a request traverses APIs in different cloud environments
   - Point out the latency differences between cloud providers
   - Explain how the system correlates related APIs

### C. Anomaly Detection Demo (10 minutes)

1. Run the demonstration capabilities script:
```bash
python -m src.scripts.demonstrate_capabilities
```

2. As the script runs, explain:
   - How the system displays all monitored APIs across cloud environments
   - The metrics being collected
   - Any anomalies detected
   - Current predictions
   - Active alerts
   - Cross-environment analysis results

3. In the Kibana Anomaly Detection dashboard:
   - Show detected anomalies (response time spikes, error rate increases)
   - Explain the severity scoring mechanism
   - Demonstrate how the system correlates anomalies across cloud environments
   - Point out the environment-specific thresholds

### D. Predictive Analytics Demo (5 minutes)

1. Access the predictions endpoint:
```bash
curl http://localhost:8000/api/v1/predictions
```

2. In the Kibana dashboard:
   - Show the prediction graphs
   - Explain how the system uses historical patterns from cloud environments
   - Demonstrate predicted impact scores
   - Show the confidence levels for each prediction

### E. Interactive Demo (10 minutes)

Use the trigger_demo_anomaly script to demonstrate different types of anomalies:

1. Response Time Degradation:
```bash
python -m src.scripts.trigger_demo_anomaly --type response_time --env aws --severity medium --duration 5
```

2. Error Rate Spike:
```bash
python -m src.scripts.trigger_demo_anomaly --type error_rate --env azure --severity high --duration 5
```

3. Cross-Environment Failure:
```bash
python -m src.scripts.trigger_demo_anomaly --type cross_environment --envs aws gcp --severity critical --duration 5
```

4. After triggering anomalies, show:
   - Real-time detection in Kibana dashboard (refresh the page to see updates)
   - Alerts generated via `curl http://localhost:8000/api/v1/alerts`
   - Updated predictions via `curl http://localhost:8000/api/v1/predictions`
   - Cross-environment impact analysis via `curl http://localhost:8000/api/v1/dashboard/summary`

## 5. Solution Explanation

### A. Solving the Problem Statement (5 minutes)

Explain how the system addresses the key challenges from the problem statement:

1. **Multi-Environment Monitoring**
   - Show how the system tracks APIs across AWS, Azure, and GCP
   - Explain the environment-specific thresholds and analysis

2. **Anomaly Detection**
   - Demonstrate the ML algorithms used for anomaly detection
   - Show how the system handles different types of anomalies

3. **Cross-Environment Analysis**
   - Explain how the system correlates events across cloud environments
   - Show the impact scoring mechanism

4. **Predictive Capabilities**
   - Demonstrate the predictive models
   - Show how the system forecasts potential issues

### B. Architecture and Implementation (5 minutes)

1. Explain the layered architecture:
   - Data Collection Layer
   - Analysis Layer
   - Storage Layer
   - Presentation Layer

2. Highlight key implementation details:
   - Use of MongoDB Atlas for configuration and metrics
   - Elasticsearch Cloud for time-series data and logs
   - AWS/Azure/GCP integration methods
   - ML models for anomaly detection and prediction

## 6. Monitoring the Results

### Viewing Triggered Anomalies

After triggering anomalies, you can monitor them in several ways:

1. **Kibana Dashboard**:
   - Go to http://localhost:5601
   - Navigate to the "Anomaly Detection" dashboard
   - Refresh to see newly triggered anomalies

2. **API Endpoints**:
   ```bash
   # Check for new anomalies
   curl http://localhost:8000/api/v1/anomalies
   
   # Check for new alerts
   curl http://localhost:8000/api/v1/alerts
   
   # Check for updated predictions
   curl http://localhost:8000/api/v1/predictions
   ```

3. **Dashboard Summary**:
   ```bash
   curl http://localhost:8000/api/v1/dashboard/summary
   ```
   This shows a real-time overview of system status including:
   - Active alerts count
   - Anomaly count
   - Cross-environment correlated issues
   - Overall impact score

### Real-time Notification Monitoring

1. Check Slack alerts (if configured with a webhook URL)
2. Check email alerts (if configured with SMTP settings)
3. View the log files in the logs/ directory

## 7. Troubleshooting

If you encounter issues during the demonstration:

1. **MongoDB Connection Issues**
   - Check your MongoDB Atlas connection string in .env
   - Verify network connectivity
   - Run `python -m src.scripts.verify_mongodb.py` directly to check connection

2. **Elasticsearch Issues**
   - Verify Elasticsearch cloud credentials
   - Check Kibana access rights

3. **API Endpoints Not Responding**
   - Check the application logs
   - Verify the service is running: `curl http://localhost:8000/health`
   - Restart the application using start_cloud.bat/sh

4. **No Data in Dashboards**
   - Run `python -m src.scripts.generate_test_data` again
   - Check Elasticsearch indices

5. **Demo Anomalies Not Triggering**
   - Verify trigger endpoint is responding
   - Check application logs for errors
   - Try different anomaly types or severity levels

## 8. Reference: API Monitoring System Data Flow

1. **Data Collection**:
   - API metrics are collected from AWS, Azure, and GCP
   - Metrics are stored in MongoDB and Elasticsearch

2. **Analysis**:
   - Response time analyzer detects anomalies in API response times
   - Error rate analyzer identifies unusual error patterns
   - Cross-environment analyzer correlates issues across cloud environments

3. **Alerting**:
   - Alerts are generated based on severity and impact
   - Notifications are sent via configured channels

4. **Prediction**:
   - ML models predict potential future issues
   - Confidence scores indicate prediction reliability

5. **Visualization**:
   - Kibana dashboards show real-time system status
   - Custom API endpoints provide data for integration with other systems 