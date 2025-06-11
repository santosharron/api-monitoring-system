# Cognitive API Monitoring System with Predictive Alerting

This project is a real-time API monitoring and anomaly detection system built to track and analyze API performance across AWS, Azure, and GCP environments. It monitors response times and error rates with environment-specific thresholds and uses historical trends to detect unusual spikes or changes in patterns. It predicts potential failures based on past data, assigns severity levels, and sends alerts through Slack or Email to help teams act before issues impact users. By correlating data across environments and identifying problems early, it helps engineering teams reduce downtime, improve reliability, and maintain consistent performance across cloud platforms—making it a valuable tool for businesses that rely on stable and responsive APIs.


## System Architecture

```
├── Data Collection Layer
│   ├── API Collectors (Real-time metrics)
│   └── Log Aggregators (ELK Stack)
├── Analysis Layer
│   ├── Response Time Analyzer
│   ├── Error Rate Analyzer
│   ├── Pattern Analyzer
│   └── Cross-Environment Analyzer
├── Storage Layer
│   ├── MongoDB (API configurations, metrics)
│   └── Elasticsearch (Logs, time-series data)
└── Presentation Layer
    ├── REST API
    └── Kibana Dashboards
```
![image alt](https://github.com/santosharron/api-monitoring-system/blob/c5bb90b5240bb5c838a5ec578a5830be0cb8074b/system%20architecture.jpeg)

## Features

1. **Multi-Environment Support**
   - AWS, Azure, and GCP integration
   - Cross-environment correlation
   - Environment-specific thresholds

2. **Response Time Monitoring**
   - Real-time response time tracking
   - Spike detection
   - Pattern change detection
   - Historical trend analysis

3. **Error Rate Analysis**
   - Real-time error tracking
   - Error pattern detection
   - Cross-environment error correlation
   - 99th percentile threshold monitoring

4. **Predictive Analytics**
   - Pattern-based prediction
   - Impact forecasting
   - Anomaly score-based prediction
   - Historical trend analysis

5. **Alerting System**
   - Multi-channel notifications (Slack, Email)
   - Severity-based alerting
   - Environment-aware alerts
   - Cross-environment impact alerts

## Getting Started

### Prerequisites

1. Python 3.8+
2. MongoDB Atlas account
3. Elasticsearch Cloud account
4. Docker (optional, for local development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd api-monitoring-system
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Running the System

1. Start the system:
```bash
# On Windows
start_cloud.bat

# On Linux/Mac
./start_cloud.sh
```

2. The system will:
   - Connect to MongoDB Atlas
   - Set up Elasticsearch indices
   - Create API sources
   - Generate test data
   - Start monitoring
   - Run demonstration

## Monitoring and Testing

### 1. API Endpoints

Access the API documentation at http://localhost:8000/docs

Key endpoints:
- `GET /api/v1/apis` - List monitored APIs
- `GET /api/v1/metrics` - Get API metrics
- `GET /api/v1/anomalies` - Get detected anomalies
- `GET /api/v1/predictions` - Get predictions
- `GET /api/v1/alerts` - Get active alerts

### 2. Kibana Dashboard

Access Kibana at http://localhost:5601

Available dashboards:
1. **API Health Overview**
   - Response time trends
   - Error rates
   - Success rates
   - Environment distribution
     
![overview](https://github.com/user-attachments/assets/48b48222-1364-4f5e-8a41-f23decef0ce9)

2. **Anomaly Detection**
   - Detected anomalies
   - Severity distribution
   - Pattern changes
   - Impact analysis
     
![error rate](https://github.com/user-attachments/assets/44c4984a-35cf-4884-a650-9d5f58bc5b7c)

3. **Cross-Environment Analysis**
   - Environment correlation
   - Impact scores
   - Issue propagation
   
![cross env](https://github.com/user-attachments/assets/ae075655-bf13-44ed-b08e-38157848063b)

### 3. Logs and Monitoring

Logs are available in multiple locations:

1. **Application Logs**
   - Console output
   - Log files in `logs/` directory
   - Log levels: INFO, WARNING, ERROR

2. **Elasticsearch Logs**
   - Access via Kibana
   - Search and filter capabilities
   - Time-series visualization

3. **MongoDB Logs**
   - Database operations
   - Connection status
   - Performance metrics

### 4. Testing Scenarios

1. **Response Time Testing**
```bash
# Monitor response time for specific API
curl "http://localhost:8000/api/v1/metrics?api_id=prod-api-1&metric_type=response_time"
```

2. **Error Rate Testing**
```bash
# Check error rates across environments
curl "http://localhost:8000/api/v1/metrics?metric_type=error_rate"
```

3. **Anomaly Detection**
```bash
# Get detected anomalies
curl "http://localhost:8000/api/v1/anomalies"
```

4. **Cross-Environment Analysis**
```bash
# Get cross-environment analysis
curl "http://localhost:8000/api/v1/cross_environment_analysis"

```
## Flowchart
![image alt](https://github.com/santosharron/api-monitoring-system/blob/c5bb90b5240bb5c838a5ec578a5830be0cb8074b/flowchart.jpg)

## Troubleshooting

### Common Issues

1. **MongoDB Connection Issues**
   - Check MongoDB Atlas connection string
   - Verify network access
   - Check credentials

2. **Elasticsearch Connection Issues**
   - Verify Cloud ID
   - Check API key
   - Confirm network access

3. **No Active API Sources**
   - Run `python -m src.scripts.create_real_api`
   - Check API source configuration
   - Verify database connection

4. **Missing Metrics**
   - Run `python -m src.scripts.generate_test_data`
   - Check collector status
   - Verify API endpoints

### Log Analysis

1. **Application Logs**
   - Check `logs/app.log`
   - Look for ERROR level messages
   - Monitor connection status

2. **Database Logs**
   - Check MongoDB logs
   - Monitor Elasticsearch status
   - Verify data ingestion

## System Requirements

- CPU: 2+ cores
- RAM: 4GB+
- Storage: 20GB+
- Network: Stable internet connection

## Contributors

[Santosh Arron](https://github.com/santosharron), [Riddima Benjamin](https://github.com/riddima15benjamin), [Shivi Gupta](https://github.com/Shivi-013), [Dheeraj Konakalla](https://github.com/DheerajKonakalla4)

## License

Apache-2.0 License - See LICENSE file for details
