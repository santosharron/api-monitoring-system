"""
Database access layer for API monitoring system.
"""
import logging
import asyncio
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from elasticsearch import AsyncElasticsearch
import pymongo
import json

from config.settings import Settings
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Alert, Environment

logger = logging.getLogger(__name__)

# Create settings instance
settings = Settings()

class Database:
    """
    Database access layer that handles interactions with MongoDB and Elasticsearch.
    """
    def __init__(self):
        """
        Initialize the database connections.
        """
        self.mongo_client = None
        self.es_client = None
        self.initialized = False
        self.es_available = False
        self.mongo_available = False
    
    async def connect(self):
        """
        Connect to the databases.
        """
        if self.initialized:
            return
        
        try:
            # Connect to MongoDB
            try:
                # Get MongoDB URI directly from environment if available, otherwise use settings
                mongodb_uri = os.environ.get("MONGODB_URI") or settings.MONGODB_URI
                
                # Debug log for MongoDB connection
                logger.info(f"Connecting to MongoDB with URI: {mongodb_uri[:20]}...{mongodb_uri[-20:] if len(mongodb_uri) > 40 else ''}")
                
                # Configure more explicit timeout parameters
                connection_params = {
                    "serverSelectionTimeoutMS": 30000,  # Increase from 5000 to 30000
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "maxIdleTimeMS": 45000,
                }
                
                self.mongo_client = AsyncIOMotorClient(
                    mongodb_uri, 
                    **connection_params
                )
                
                # Test connection
                logger.info("Testing MongoDB connection...")
                await self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client.get_database()
                self.mongo_available = True
                logger.info(f"MongoDB connection established to database: {self.mongo_db.name}")
                
                # Setup MongoDB indexes if available
                if self.mongo_available:
                    await self._setup_mongodb_indexes()
            except Exception as mongo_err:
                logger.warning(f"MongoDB connection failed: {str(mongo_err)}. Running with limited functionality.")
                self.mongo_available = False
            
            # Connect to Elasticsearch
            try:
                es_kwargs = {}
                if settings.ELASTICSEARCH_CLOUD_ID:
                    logger.info(f"Using Elasticsearch Cloud ID: {settings.ELASTICSEARCH_CLOUD_ID[:10]}...")
                    es_kwargs['cloud_id'] = settings.ELASTICSEARCH_CLOUD_ID
                    # When using Cloud ID, we don't need to specify hosts
                    hosts = None
                else:
                    hosts = settings.ELASTICSEARCH_HOSTS
                    logger.info(f"Using Elasticsearch hosts: {hosts}")
                
                if settings.ELASTICSEARCH_API_KEY:
                    logger.info("Using Elasticsearch API key authentication")
                    es_kwargs['api_key'] = settings.ELASTICSEARCH_API_KEY
                elif settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                    logger.info(f"Using Elasticsearch basic auth with username: {settings.ELASTICSEARCH_USERNAME}")
                    es_kwargs['basic_auth'] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
                else:
                    # Hardcoded credentials for testing
                    logger.info("Using hardcoded Elasticsearch basic auth credentials")
                    es_kwargs['basic_auth'] = ("elastic", "KIuc03ZYAf6IqGkE1zEap1DR")
                
                # Only pass hosts if we're not using cloud_id
                if 'cloud_id' in es_kwargs:
                    self.es_client = AsyncElasticsearch(
                        request_timeout=10,  # Increase timeout to 10 seconds
                        **es_kwargs
                    )
                else:
                    self.es_client = AsyncElasticsearch(
                        hosts,
                        request_timeout=10,  # Increase timeout to 10 seconds
                        **es_kwargs
                    )
                
                # Test connection
                logger.info("Testing Elasticsearch connection...")
                await self.es_client.info()
                self.es_available = True
                logger.info("Elasticsearch connection established")
                
                # Setup Elasticsearch indices if available
                if self.es_available:
                    await self._setup_elasticsearch_indices()
            except Exception as es_err:
                logger.warning(f"Elasticsearch connection failed: {str(es_err)}. Running with limited functionality.")
                self.es_available = False
                if self.es_client:
                    await self.es_client.close()
                    self.es_client = None
            
            self.initialized = True
            
            if not self.mongo_available and not self.es_available:
                logger.warning("No database connections available. Running in memory-only mode with limited functionality.")
            
        except Exception as e:
            logger.error(f"Error initializing database connections: {str(e)}")
            # Don't raise the exception, allow the application to start with limited functionality
    
    async def disconnect(self):
        """
        Disconnect from the databases.
        """
        if self.es_client:
            await self.es_client.close()
            self.es_client = None
            self.es_available = False
        
        if self.mongo_client:
            self.mongo_client.close()
            self.mongo_client = None
            self.mongo_available = False
        
        self.initialized = False
        logger.info("Database connections closed")
    
    async def _setup_elasticsearch_indices(self):
        """Set up required Elasticsearch indices."""
        try:
            # Create indices with serverless-compatible settings
            indices = {
                'api_metrics': {
                    'mappings': {
                        'properties': {
                            'id': {'type': 'keyword'},
                            'timestamp': {'type': 'date'},
                            'api_id': {'type': 'keyword'},
                            'response_time': {'type': 'float'},
                            'status_code': {'type': 'integer'},
                            'success': {'type': 'boolean'},
                            'error_message': {'type': 'text'},
                            'environment': {'type': 'keyword'},
                            'endpoint': {'type': 'keyword'},
                            'method': {'type': 'keyword'}
                        }
                    }
                },
                'anomalies': {
                    'mappings': {
                        'properties': {
                            'timestamp': {'type': 'date'},
                            'api_id': {'type': 'keyword'},
                            'type': {'type': 'keyword'},
                            'severity': {'type': 'float'},
                            'description': {'type': 'text'},
                            'environment': {'type': 'keyword'},
                            'context': {'type': 'object'}
                        }
                    }
                }
            }
            
            for index_name, settings in indices.items():
                if not await self.es_client.indices.exists(index=index_name):
                    await self.es_client.indices.create(index=index_name, body=settings)
                    logger.info(f"Created Elasticsearch index: {index_name}")
        except Exception as e:
            logger.warning(f"Error setting up Elasticsearch indices: {str(e)}")
            self.es_available = False
    
    async def _setup_mongodb_indexes(self):
        """
        Set up MongoDB collections and indexes.
        """
        if not self.mongo_available or not self.mongo_client:
            return
            
        try:
            # Create indexes for API sources collection
            await self.mongo_db.api_sources.create_index([("name", pymongo.ASCENDING)], unique=True)
            await self.mongo_db.api_sources.create_index([("environment", pymongo.ASCENDING)])
            await self.mongo_db.api_sources.create_index([("updated_at", pymongo.DESCENDING)])
            
            # Create indexes for anomalies collection
            await self.mongo_db.anomalies.create_index([("api_id", pymongo.ASCENDING)])
            await self.mongo_db.anomalies.create_index([("timestamp", pymongo.DESCENDING)])
            await self.mongo_db.anomalies.create_index([("type", pymongo.ASCENDING)])
            await self.mongo_db.anomalies.create_index([("environment", pymongo.ASCENDING)])
            await self.mongo_db.anomalies.create_index([("processed", pymongo.ASCENDING)])
            
            # Create indexes for predictions collection
            await self.mongo_db.predictions.create_index([("api_id", pymongo.ASCENDING)])
            await self.mongo_db.predictions.create_index([("timestamp", pymongo.DESCENDING)])
            await self.mongo_db.predictions.create_index([("predicted_for", pymongo.ASCENDING)])
            await self.mongo_db.predictions.create_index([("type", pymongo.ASCENDING)])
            await self.mongo_db.predictions.create_index([("environment", pymongo.ASCENDING)])
            
            # Create indexes for alerts collection
            await self.mongo_db.alerts.create_index([("created_at", pymongo.DESCENDING)])
            await self.mongo_db.alerts.create_index([("status", pymongo.ASCENDING)])
            await self.mongo_db.alerts.create_index([("severity", pymongo.ASCENDING)])
            await self.mongo_db.alerts.create_index([("api_id", pymongo.ASCENDING)])
            await self.mongo_db.alerts.create_index([("environment", pymongo.ASCENDING)])
            
            logger.info("MongoDB indexes created")
        except Exception as e:
            logger.warning(f"Error setting up MongoDB indexes: {str(e)}")
            self.mongo_available = False
    
    # API Source methods
    
    async def store_api_source(self, api_source: ApiSource) -> str:
        """
        Store an API source in the database.
        
        Args:
            api_source: The API source to store.
            
        Returns:
            The ID of the stored API source.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot store API source: MongoDB not available")
            return api_source.id
        
        # Convert Pydantic model to dict
        api_dict = api_source.dict()
        
        # Set created_at and updated_at timestamps
        now = datetime.utcnow()
        if not api_dict.get("created_at"):
            api_dict["created_at"] = now
        api_dict["updated_at"] = now
        
        # Generate ID if not provided
        if not api_dict.get("id"):
            from uuid import uuid4
            api_dict["id"] = str(uuid4())
        
        # Store in MongoDB
        await self.mongo_db.api_sources.update_one(
            {"id": api_dict["id"]},
            {"$set": api_dict},
            upsert=True
        )
        
        logger.debug(f"Stored API source: {api_dict['id']}")
        return api_dict["id"]
    
    async def get_api_sources(self, active: Optional[bool] = None, updated_since: Optional[datetime] = None) -> List[ApiSource]:
        """
        Get API sources from the database.
        
        Args:
            active: If provided, filter by active status.
            updated_since: If provided, only return sources updated since this time.
            
        Returns:
            List of API sources.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot get API sources: MongoDB not available")
            return []
        
        # Build query
        query = {}
        if active is not None:
            query["is_active"] = active
        if updated_since:
            query["updated_at"] = {"$gte": updated_since}
        
        # Query MongoDB
        cursor = self.mongo_db.api_sources.find(query)
        
        # Convert to Pydantic models
        api_sources = []
        async for doc in cursor:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            api_sources.append(ApiSource(**doc))
        
        return api_sources
    
    async def get_api_sources_updated_since(self, timestamp: datetime) -> List[ApiSource]:
        """
        Get API sources updated since a given timestamp.
        
        Args:
            timestamp: The timestamp to check against.
            
        Returns:
            List of updated API sources.
        """
        return await self.get_api_sources(updated_since=timestamp)
    
    async def get_api_source(self, api_id: str) -> Optional[ApiSource]:
        """
        Get an API source by ID.
        
        Args:
            api_id: The ID of the API source.
            
        Returns:
            The API source, or None if not found.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot get API source: MongoDB not available")
            return None
        
        # Query MongoDB
        doc = await self.mongo_db.api_sources.find_one({"id": api_id})
        
        if doc:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            return ApiSource(**doc)
        
        return None
    
    async def delete_api_source(self, api_id: str) -> bool:
        """
        Delete an API source.
        
        Args:
            api_id: The ID of the API source.
            
        Returns:
            True if deleted, False if not found.
        """
        await self._ensure_connection()
        
        # Delete from MongoDB
        result = await self.mongo_db.api_sources.delete_one({"id": api_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted API source: {api_id}")
            return True
        
        return False
    
    # Metrics methods
    
    async def store_metrics(self, metrics: List[ApiMetric]) -> int:
        """
        Store API metrics in the database.
        
        Args:
            metrics: List of API metrics to store.
            
        Returns:
            Number of metrics stored.
        """
        await self._ensure_connection()
        
        if not metrics:
            logger.debug("No metrics to store")
            return 0
        
        stored_count = 0
        
        try:
            # Convert Pydantic models to dicts
            metric_dicts = [metric.dict() for metric in metrics]
            
            # Store in MongoDB if available
            if self.mongo_available:
                try:
                    result = await self.mongo_db.api_metrics.insert_many(metric_dicts)
                    stored_count = len(result.inserted_ids)
                    logger.debug(f"Stored {stored_count} metrics in MongoDB")
                except Exception as mongo_err:
                    logger.warning(f"Error storing metrics in MongoDB: {str(mongo_err)}. Continuing with Elasticsearch.")
            
            # Store in Elasticsearch if available
            if self.es_available:
                try:
                    bulk_operations = []
                    for metric in metrics:
                        # First line is the action/metadata
                        bulk_operations.append({"index": {"_index": "api_metrics"}})
                        # Second line is the document data
                        bulk_operations.append({
                            'id': metric.id,
                            'timestamp': metric.timestamp.isoformat(),
                            'api_id': metric.api_id,
                            'response_time': metric.response_time,
                            'status_code': metric.status_code,
                            'success': metric.success,
                            'error_message': metric.error_message,
                            'environment': metric.environment.value if hasattr(metric.environment, 'value') else metric.environment,
                            'endpoint': metric.endpoint,
                            'method': metric.method
                        })
                    
                    if bulk_operations:
                        await self.es_client.bulk(operations=bulk_operations)
                        if not self.mongo_available:
                            stored_count = len(metrics)
                        logger.debug(f"Stored {len(metrics)} metrics in Elasticsearch")
                except Exception as es_err:
                    logger.warning(f"Error storing metrics in Elasticsearch: {str(es_err)}")
            
            return stored_count
        except Exception as e:
            logger.error(f"Error storing metrics: {str(e)}")
            return 0
    
    async def get_metrics(
        self,
        api_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        environment: Optional[Environment] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        limit: int = 1000
    ) -> List[ApiMetric]:
        """
        Get API metrics from Elasticsearch.
        
        Args:
            api_id: If provided, filter by API ID.
            start_time: If provided, only return metrics after this time.
            end_time: If provided, only return metrics before this time.
            environment: If provided, filter by environment.
            endpoint: If provided, filter by endpoint.
            method: If provided, filter by HTTP method.
            limit: Maximum number of metrics to return.
            
        Returns:
            List of API metrics.
        """
        await self._ensure_connection()
        
        if not self.es_available or not self.es_client:
            logger.warning("Cannot get metrics: Elasticsearch not available")
            return []

        try:
            # Build query
            query = {"bool": {"must": []}}
            
            if api_id:
                query["bool"]["must"].append({"term": {"api_id": api_id}})
            
            if start_time or end_time:
                range_query = {"range": {"timestamp": {}}}
                if start_time:
                    range_query["range"]["timestamp"]["gte"] = start_time.isoformat()
                if end_time:
                    range_query["range"]["timestamp"]["lte"] = end_time.isoformat()
                query["bool"]["must"].append(range_query)
            
            if environment:
                query["bool"]["must"].append({"term": {"environment": environment.value}})
            
            if endpoint:
                query["bool"]["must"].append({"term": {"endpoint": endpoint}})
            
            if method:
                query["bool"]["must"].append({"term": {"method": method}})
            
            # Execute query
            response = await self.es_client.search(
                index="api_metrics",
                body={
                    "query": query,
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "size": limit
                }
            )
            
            # Convert results to Pydantic models
            metrics = []
            
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                
                # Convert ISO timestamp back to datetime
                if isinstance(source["timestamp"], str):
                    source["timestamp"] = datetime.fromisoformat(source["timestamp"].replace('Z', '+00:00'))
                
                # Convert environment string to enum
                if isinstance(source["environment"], str):
                    try:
                        source["environment"] = Environment(source["environment"])
                    except ValueError:
                        # Default to OTHER if environment is invalid
                        source["environment"] = Environment.OTHER
                
                # Generate ID if missing
                if "id" not in source:
                    from uuid import uuid4
                    source["id"] = str(uuid4())
                
                metrics.append(ApiMetric(**source))
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting metrics from Elasticsearch: {str(e)}")
            return []
    
    async def get_all_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ApiMetric]:
        """
        Get all API metrics across all APIs.
        
        Args:
            start_time: If provided, only return metrics after this time.
            end_time: If provided, only return metrics before this time.
            limit: Maximum number of metrics to return.
            
        Returns:
            List of API metrics.
        """
        await self._ensure_connection()
        
        # Check if Elasticsearch is available
        if not self.es_available or not self.es_client:
            logger.warning("Cannot get metrics: Elasticsearch not available")
            return []
            
        return await self.get_metrics(
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    # Anomaly methods
    
    async def store_anomalies(self, anomalies: List[Anomaly]) -> int:
        """
        Store anomalies in MongoDB.
        
        Args:
            anomalies: List of anomalies to store.
            
        Returns:
            Number of anomalies stored.
        """
        await self._ensure_connection()
        
        if not anomalies:
            return 0
        
        # Prepare bulk operation
        operations = []
        
        for anomaly in anomalies:
            # Convert Pydantic model to dict
            anomaly_dict = anomaly.dict()
            
            # Add processed flag (for alerting)
            anomaly_dict["processed"] = False
            
            # Store in MongoDB
            operations.append(pymongo.InsertOne(anomaly_dict))
        
        if operations:
            # Execute bulk operation
            result = await self.mongo_db.anomalies.bulk_write(operations)
            
            logger.debug(f"Stored {len(anomalies)} anomalies")
            return result.inserted_count
        
        return 0
    
    async def get_anomalies(
        self,
        api_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        anomaly_type: Optional[str] = None,
        environment: Optional[Environment] = None,
        min_severity: Optional[float] = None,
        limit: int = 100
    ) -> List[Anomaly]:
        """
        Get anomalies from MongoDB.
        
        Args:
            api_id: If provided, filter by API ID.
            start_time: If provided, only return anomalies after this time.
            end_time: If provided, only return anomalies before this time.
            anomaly_type: If provided, filter by anomaly type.
            environment: If provided, filter by environment.
            min_severity: If provided, only return anomalies with at least this severity.
            limit: Maximum number of anomalies to return.
            
        Returns:
            List of anomalies.
        """
        await self._ensure_connection()
        
        # Build query
        query = {}
        
        if api_id:
            query["api_id"] = api_id
        
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        if anomaly_type:
            query["type"] = anomaly_type
        
        if environment:
            query["environment"] = environment.value
        
        if min_severity is not None:
            query["severity"] = {"$gte": min_severity}
        
        # Execute query
        cursor = self.mongo_db.anomalies.find(query).sort("timestamp", -1).limit(limit)
        
        # Convert results to Pydantic models
        anomalies = []
        
        async for doc in cursor:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            # Remove processed flag
            if "processed" in doc:
                del doc["processed"]
            
            # Convert environment string to enum if needed
            if isinstance(doc.get("environment"), str):
                try:
                    doc["environment"] = Environment(doc["environment"])
                except ValueError:
                    # Default to OTHER if environment is invalid
                    doc["environment"] = Environment.OTHER
            
            anomalies.append(Anomaly(**doc))
        
        return anomalies
    
    async def get_unprocessed_anomalies(self) -> List[Anomaly]:
        """
        Get unprocessed anomalies from MongoDB.
        
        Returns:
            List of unprocessed anomalies.
        """
        await self._ensure_connection()
        
        # Query for unprocessed anomalies
        cursor = self.mongo_db.anomalies.find({"processed": False}).sort("timestamp", -1)
        
        # Convert results to Pydantic models
        anomalies = []
        
        async for doc in cursor:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            # Remove processed flag
            if "processed" in doc:
                del doc["processed"]
            
            # Convert environment string to enum if needed
            if isinstance(doc.get("environment"), str):
                try:
                    doc["environment"] = Environment(doc["environment"])
                except ValueError:
                    # Default to OTHER if environment is invalid
                    doc["environment"] = Environment.OTHER
            
            anomalies.append(Anomaly(**doc))
        
        return anomalies
    
    async def mark_anomalies_processed(self, anomaly_ids: List[str]) -> int:
        """
        Mark anomalies as processed.
        
        Args:
            anomaly_ids: List of anomaly IDs to mark as processed.
            
        Returns:
            Number of anomalies marked as processed.
        """
        await self._ensure_connection()
        
        if not anomaly_ids:
            return 0
        
        # Update anomalies
        result = await self.mongo_db.anomalies.update_many(
            {"id": {"$in": anomaly_ids}},
            {"$set": {"processed": True}}
        )
        
        return result.modified_count
    
    # Prediction methods
    
    async def store_predictions(self, predictions: List[Prediction]) -> int:
        """
        Store predictions in MongoDB.
        
        Args:
            predictions: List of predictions to store.
            
        Returns:
            Number of predictions stored.
        """
        await self._ensure_connection()
        
        if not predictions:
            return 0
        
        # Prepare bulk operation
        operations = []
        
        for prediction in predictions:
            # Convert Pydantic model to dict
            prediction_dict = prediction.dict()
            
            # Store in MongoDB
            operations.append(pymongo.InsertOne(prediction_dict))
        
        if operations:
            # Execute bulk operation
            result = await self.mongo_db.predictions.bulk_write(operations)
            
            logger.debug(f"Stored {len(predictions)} predictions")
            return result.inserted_count
        
        return 0
    
    async def get_predictions(
        self,
        api_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        prediction_type: Optional[str] = None,
        environment: Optional[Environment] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100
    ) -> List[Prediction]:
        """
        Get predictions from MongoDB.
        
        Args:
            api_id: If provided, filter by API ID.
            start_time: If provided, only return predictions after this time.
            end_time: If provided, only return predictions before this time.
            prediction_type: If provided, filter by prediction type.
            environment: If provided, filter by environment.
            min_confidence: If provided, only return predictions with at least this confidence.
            limit: Maximum number of predictions to return.
            
        Returns:
            List of predictions.
        """
        await self._ensure_connection()
        
        # Build query
        query = {}
        
        if api_id:
            query["api_id"] = api_id
        
        if start_time or end_time:
            query["predicted_for"] = {}
            if start_time:
                query["predicted_for"]["$gte"] = start_time
            if end_time:
                query["predicted_for"]["$lte"] = end_time
        
        if prediction_type:
            query["type"] = prediction_type
        
        if environment:
            query["environment"] = environment.value
        
        if min_confidence is not None:
            query["confidence"] = {"$gte": min_confidence}
        
        # Execute query
        cursor = self.mongo_db.predictions.find(query).sort("predicted_for", 1).limit(limit)
        
        # Convert results to Pydantic models
        predictions = []
        
        async for doc in cursor:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            # Convert environment string to enum if needed
            if isinstance(doc.get("environment"), str):
                try:
                    doc["environment"] = Environment(doc["environment"])
                except ValueError:
                    # Default to OTHER if environment is invalid
                    doc["environment"] = Environment.OTHER
            
            predictions.append(Prediction(**doc))
        
        return predictions
    
    # Alert methods
    
    async def store_alerts(self, alerts: List[Alert]) -> int:
        """
        Store alerts in MongoDB.
        
        Args:
            alerts: List of alerts to store.
            
        Returns:
            Number of alerts stored.
        """
        await self._ensure_connection()
        
        if not alerts:
            return 0
        
        # Prepare bulk operation
        operations = []
        
        for alert in alerts:
            # Convert Pydantic model to dict
            alert_dict = alert.dict()
            
            # Store in MongoDB
            operations.append(pymongo.InsertOne(alert_dict))
        
        if operations:
            # Execute bulk operation
            result = await self.mongo_db.alerts.bulk_write(operations)
            
            logger.debug(f"Stored {len(alerts)} alerts")
            return result.inserted_count
        
        return 0
    
    async def get_alerts(
        self,
        api_id: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        severity: Optional[str] = None,
        environment: Optional[Environment] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get alerts from MongoDB.
        
        Args:
            api_id: If provided, filter by API ID.
            statuses: If provided, filter by alert statuses.
            severity: If provided, filter by severity.
            environment: If provided, filter by environment.
            limit: Maximum number of alerts to return.
            
        Returns:
            List of alerts.
        """
        await self._ensure_connection()
        
        # Build query
        query = {}
        
        if api_id:
            query["apis"] = api_id
        
        if statuses:
            query["status"] = {"$in": statuses}
        
        if severity:
            query["severity"] = severity
        
        if environment:
            query["environments"] = environment.value
        
        # Execute query
        cursor = self.mongo_db.alerts.find(query).sort("created_at", -1).limit(limit)
        
        # Convert results to Pydantic models
        alerts = []
        
        async for doc in cursor:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            # Convert environment strings to enums if needed
            if doc.get("environments"):
                try:
                    doc["environments"] = [
                        Environment(env) if isinstance(env, str) else env
                        for env in doc["environments"]
                    ]
                except ValueError:
                    # Skip invalid environments
                    pass
            
            alerts.append(Alert(**doc))
        
        return alerts
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: The ID of the alert.
            
        Returns:
            The alert, or None if not found.
        """
        await self._ensure_connection()
        
        # Query MongoDB
        doc = await self.mongo_db.alerts.find_one({"id": alert_id})
        
        if doc:
            # Remove MongoDB _id field
            if "_id" in doc:
                del doc["_id"]
            
            # Convert environment strings to enums if needed
            if doc.get("environments"):
                try:
                    doc["environments"] = [
                        Environment(env) if isinstance(env, str) else env
                        for env in doc["environments"]
                    ]
                except ValueError:
                    # Skip invalid environments
                    pass
            
            return Alert(**doc)
        
        return None
    
    async def update_alert_status(self, alert_id: str, status: str, updated_by: str, updated_at: datetime) -> bool:
        """
        Update an alert's status.
        
        Args:
            alert_id: The ID of the alert.
            status: The new status.
            updated_by: The user who updated the status.
            updated_at: The time of the update.
            
        Returns:
            True if updated, False if not found.
        """
        await self._ensure_connection()
        
        # Update alert
        result = await self.mongo_db.alerts.update_one(
            {"id": alert_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": updated_at,
                    "updated_by": updated_by
                }
            }
        )
        
        return result.modified_count > 0
    
    async def update_alert(self, alert_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an alert.
        
        Args:
            alert_id: The ID of the alert.
            updates: Dictionary of updates to apply.
            
        Returns:
            True if updated, False if not found.
        """
        await self._ensure_connection()
        
        # Update alert
        result = await self.mongo_db.alerts.update_one(
            {"id": alert_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def store_anomaly(self, anomaly: Anomaly) -> str:
        """
        Store an anomaly in the database.
        
        Args:
            anomaly: The anomaly to store.
            
        Returns:
            The ID of the stored anomaly.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot store anomaly: MongoDB not available")
            return anomaly.id
        
        # Convert Pydantic model to dict
        anomaly_dict = anomaly.dict()
        
        # Generate ID if not provided
        if not anomaly_dict.get("id"):
            from uuid import uuid4
            anomaly_dict["id"] = str(uuid4())
        
        # Store in MongoDB
        await self.mongo_db.anomalies.update_one(
            {"id": anomaly_dict["id"]},
            {"$set": anomaly_dict},
            upsert=True
        )
        
        # Store in Elasticsearch if available
        if self.es_available:
            try:
                await self.es_client.index(
                    index="anomalies",
                    id=anomaly_dict["id"],
                    document=anomaly_dict
                )
            except Exception as e:
                logger.warning(f"Failed to store anomaly in Elasticsearch: {str(e)}")
        
        logger.debug(f"Stored anomaly: {anomaly_dict['id']}")
        return anomaly_dict["id"]
    
    async def store_alert(self, alert: Alert) -> str:
        """
        Store an alert in the database.
        
        Args:
            alert: The alert to store.
            
        Returns:
            The ID of the stored alert.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot store alert: MongoDB not available")
            return alert.id
        
        # Convert Pydantic model to dict
        alert_dict = alert.dict()
        
        # Generate ID if not provided
        if not alert_dict.get("id"):
            from uuid import uuid4
            alert_dict["id"] = str(uuid4())
        
        # Store in MongoDB
        await self.mongo_db.alerts.update_one(
            {"id": alert_dict["id"]},
            {"$set": alert_dict},
            upsert=True
        )
        
        logger.debug(f"Stored alert: {alert_dict['id']}")
        return alert_dict["id"]
    
    async def store_prediction(self, prediction: Prediction) -> str:
        """
        Store a prediction in the database.
        
        Args:
            prediction: The prediction to store.
            
        Returns:
            The ID of the stored prediction.
        """
        await self._ensure_connection()
        
        if not self.mongo_available:
            logger.warning("Cannot store prediction: MongoDB not available")
            return prediction.id
        
        # Convert Pydantic model to dict
        prediction_dict = prediction.dict()
        
        # Generate ID if not provided
        if not prediction_dict.get("id"):
            from uuid import uuid4
            prediction_dict["id"] = str(uuid4())
        
        # Store in MongoDB
        await self.mongo_db.predictions.update_one(
            {"id": prediction_dict["id"]},
            {"$set": prediction_dict},
            upsert=True
        )
        
        logger.debug(f"Stored prediction: {prediction_dict['id']}")
        return prediction_dict["id"]
    
    async def _ensure_connection(self):
        """
        Ensure that database connections are established.
        """
        if not self.initialized:
            await self.connect()
            
    async def update_api_metrics_with_missing_id(self):
        """
        Update existing API metrics in Elasticsearch that don't have an ID field.
        This is a maintenance function to handle older records created before ID was added to schema.
        """
        await self._ensure_connection()
        
        if not self.es_available or not self.es_client:
            logger.warning("Cannot update metrics: Elasticsearch not available")
            return 0
            
        try:
            # Search for all documents
            response = await self.es_client.search(
                index="api_metrics",
                body={
                    "query": {"match_all": {}},
                    "size": 1000
                }
            )
            
            updated_count = 0
            bulk_operations = []
            
            for hit in response["hits"]["hits"]:
                doc_id = hit["_id"]
                source = hit["_source"]
                
                # If document doesn't have an ID field, add one
                if "id" not in source:
                    from uuid import uuid4
                    source["id"] = str(uuid4())
                    
                    # Add update operations to bulk request
                    bulk_operations.append({"update": {"_index": "api_metrics", "_id": doc_id}})
                    bulk_operations.append({"doc": {"id": source["id"]}})
                    updated_count += 1
            
            # Execute bulk update if there are operations
            if bulk_operations:
                await self.es_client.bulk(operations=bulk_operations)
                logger.info(f"Updated {updated_count} API metrics with missing ID field")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating API metrics with missing ID: {str(e)}")
            return 0

# Singleton instance
_db_instance = None

def get_database() -> Database:
    """
    Get the database instance.
    
    Returns:
        Database instance.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance 