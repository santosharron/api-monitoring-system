# AI-Powered API Monitoring and Anomaly Detection System

An intelligent monitoring solution for large-scale, distributed multi-API platforms that can detect anomalies, predict potential issues, and provide actionable insights across on-premises, cloud, and multi-cloud environments.

## Features

- **Cross-Environment Monitoring**: Monitor APIs across on-premises, cloud, and multi-cloud infrastructures
- **Anomaly Detection**: Identify response time and error rate anomalies using AI algorithms
- **Predictive Analytics**: Forecast potential issues before they impact users
- **End-to-End Request Tracking**: Follow request journeys across distributed environments
- **Adaptive Alerting**: Smart alerts that reduce noise and provide actionable insights
- **Visualization Dashboards**: Real-time and historical performance visualization
- **Automatic API Discovery**: Automatically detect and monitor new APIs
- **Kibana Integration**: Pre-configured dashboards for Elasticsearch data visualization

## Architecture

The system consists of the following components:

- **Collectors**: Gather logs and metrics from various API sources
- **Storage**: Centralized storage for logs, metrics, and analysis results
- **Analyzers**: AI-powered components for anomaly detection and prediction
- **Alerting**: Intelligent alerting system with customizable rules
- **API**: RESTful API for system configuration and data access
- **Visualization**: Dashboards for monitoring and insights

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- pip

### Setup

1. Clone the repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Configure the environment variables:
```
cp .env.example .env
# Edit .env with your configuration
```
4. Start the required services using Docker Compose:
```
docker-compose up -d
```
5. Run the system:
```
python -m src.main
```

### Manual Setup (Without Docker)

If you prefer to run the application without Docker, follow these steps:

1. Install Python dependencies:
```
pip install -r requirements.txt
```

2. Install and run Elasticsearch (8.7.0):
   - Download from the [Elasticsearch website](https://www.elastic.co/downloads/past-releases/elasticsearch-8-7-0)
   - Extract and run: `bin/elasticsearch` (Linux/Mac) or `bin\elasticsearch.bat` (Windows)
   - Verify it's running at http://localhost:9200

3. Install and run Kibana (8.7.0):
   - Download from the [Kibana website](https://www.elastic.co/downloads/past-releases/kibana-8-7-0)
   - Extract and run: `bin/kibana` (Linux/Mac) or `bin\kibana.bat` (Windows)
   - Access Kibana at http://localhost:5601

4. Install and run MongoDB:
   - Download from the [MongoDB website](https://www.mongodb.com/try/download/community)
   - Install and start the MongoDB service
   - Verify it's running on port 27017

5. Install and run Redis:
   - Download from the [Redis website](https://redis.io/download)
   - Extract and run: `src/redis-server` (Linux/Mac) or use the Windows installer
   - Verify it's running on port 6379

6. Update your `.env` file with the correct connection details:
```
MONGODB_URI=mongodb://localhost:27017/api_monitoring
ELASTICSEARCH_HOSTS=http://localhost:9200
REDIS_HOST=localhost
REDIS_PORT=6379
```

7. Start the application:
```
python -m src.main
```

## Configuration

Configure the system through the `.env` file or environment variables. See `config/settings.py` for available options.

## Kibana Integration

The system automatically integrates with Kibana to provide visualizations for your API metrics.

### Accessing Kibana

After starting the system, Kibana will be available at http://localhost:5601

### Available Dashboards

The system automatically sets up the following dashboards:

1. **API Overview Dashboard**: Shows general API performance metrics
   - Response time by API endpoint
   - Error rates by API endpoint
   - Request volume by API endpoint
   - Environment distribution

2. **Anomaly Detection Dashboard**: Shows detected anomalies
   - Anomalies timeline
   - Anomalies by type
   - Anomalies by environment
   - Anomalies by severity

3. **Cross-Environment Analysis Dashboard**: Shows analysis across environments
   - Environment comparison charts
   - Correlated anomalies across environments
   - Request journey maps
   - Environment-specific metrics

### Accessing Dashboards from API

You can get the URLs for all available dashboards through the API:

```
GET /dashboards
```

### Creating Custom Visualizations

You can create custom visualizations in Kibana using the following index patterns:

- `api-metrics-*`: For API performance metrics
- `api-anomalies-*`: For detected anomalies
- `api-predictions-*`: For system predictions

## Automatic API Discovery

The system automatically discovers and monitors new APIs in your environment:

- **Network Scanning**: Detects APIs by scanning common ports on your network
- **Log Analysis**: Discovers APIs by analyzing log patterns
- **Service Registry Integration**: Connects to service registries (if configured)

You can view discovered APIs through the API:

```
GET /api/v1/sources
```

## Manual API Registration

Use the REST API to manually configure monitoring for your APIs:

```
POST /api/v1/sources
{
  "name": "payment-service",
  "type": "rest",
  "environment": "aws",
  "endpoint": "https://api.example.com/payments"
}
```

## License

MIT 