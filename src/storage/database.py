"""
Database access layer for API monitoring system.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from elasticsearch import AsyncElasticsearch
import pymongo
import json

from config.settings import Settings
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Alert, Environment, ApiMetrics

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
                self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
                # Test connection
                await self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client.get_database()
                self.mongo_available = True
                logger.info("MongoDB connection established")
                
                # Setup MongoDB indexes if available
                if self.mongo_available:
                    await self._setup_mongodb_indexes()
            except Exception as mongo_err:
                logger.warning(f"MongoDB connection failed: {str(mongo_err)}. Running with limited functionality.")
                self.mongo_available = False
            
            # Connect to Elasticsearch
            try:
                es_kwargs = {}
                if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                    es_kwargs['basic_auth'] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
                
                self.es_client = AsyncElasticsearch(
                    settings.ELASTICSEARCH_HOSTS,
                    request_timeout=5,  # 5 second timeout
                    **es_kwargs
                )
                
                # Test connection
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
        """
        Set up Elasticsearch indices and mappings.
        """
        if not self.es_available or not self.es_client:
            return
            
        try:
            # Define metrics index
            metrics_index = "api_metrics"
            metrics_mapping = {
                "mappings": {
                    "properties": {
                        "api_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "response_time": {"type": "float"},
                        "status_code": {"type": "integer"},
                        "error": {"type": "boolean"},
                        "error_message": {"type": "text"},
                        "endpoint": {"type": "keyword"},
                        "method": {"type": "keyword"},
                        "environment": {"type": "keyword"},
                        "request_id": {"type": "keyword"},
                        "trace_id": {"type": "keyword"},
                        "span_id": {"type": "keyword"},
                        "payload_size": {"type": "integer"},
                        "response_size": {"type": "integer"},
                        "metadata": {"type": "object", "enabled": True}
                    }
                },
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1
                }
            }
            
            # Create indices if they don't exist
            if not await self.es_client.indices.exists(index=metrics_index):
                await self.es_client.indices.create(index=metrics_index, body=metrics_mapping)
                logger.info(f"Created Elasticsearch index: {metrics_index}")
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
            query["active"] = active
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
    
    async def store_metrics(self, metrics: Union[List[ApiMetric], List[ApiMetrics]]) -> int:
        """
        Store API metrics in the database.
        
        Args:
            metrics: List of API metrics to store.
            
        Returns:
            Number of metrics stored.
        """
        await self._ensure_connection()
        
        if not metrics:
            return 0
            
        if not self.es_available:
            logger.warning("Cannot store metrics: Elasticsearch not available")
            return 0
        
        # Prepare bulk operation
        operations = []
        
        for metric in metrics:
            # Convert Pydantic model to dict
            metric_dict = metric.dict()
            
            # Elasticsearch bulk operation
            operations.append({"index": {"_index": "api_metrics"}})
            operations.append(metric_dict)
        
        if operations:
            try:
                # Execute bulk operation
                response = await self.es_client.bulk(operations=operations, refresh=True)
                logger.debug(f"Stored {len(metrics)} metrics in Elasticsearch")
                return len(metrics)
            except Exception as e:
                logger.error(f"Error storing metrics in Elasticsearch: {str(e)}")
                return 0
        
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
    
    async def _ensure_connection(self):
        """
        Ensure that database connections are established.
        """
        if not self.initialized:
            await self.connect()

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