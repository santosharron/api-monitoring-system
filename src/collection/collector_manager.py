"""
Collector manager for API monitoring system.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from config.settings import Settings
from src.collectors.rest_collector import RestApiCollector
from src.collectors.graphql_collector import GraphqlCollector
from src.collectors.grpc_collector import GrpcCollector
from src.storage.database import get_database
from src.models.api import ApiSource, ApiMetric, Environment

logger = logging.getLogger(__name__)

# Create settings instance
settings = Settings()

class CollectorManager:
    """
    Manager for data collection from API sources.
    """
    def __init__(self):
        """
        Initialize the collector manager.
        """
        self.running = False
        self.db = get_database()
        self.collection_tasks = []
        self.collectors = {}
        self.collector_classes = {
            'rest': RestApiCollector,
            'graphql': GraphqlCollector,
            'grpc': GrpcCollector
        }
    
    async def start_collection(self):
        """
        Start the data collection process.
        """
        logger.info("Starting API data collection")
        self.running = True
        
        # Load API sources from database
        await self._load_api_sources()
        
        # Start collection task
        collection_task = asyncio.create_task(self._collection_loop())
        self.collection_tasks.append(collection_task)
        
        # Start configuration watch task
        config_task = asyncio.create_task(self._watch_api_config())
        self.collection_tasks.append(config_task)
    
    async def stop_collection(self):
        """
        Stop the data collection process.
        """
        logger.info("Stopping API data collection")
        self.running = False
        
        # Cancel all collection tasks
        for task in self.collection_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.collection_tasks:
            await asyncio.gather(*self.collection_tasks, return_exceptions=True)
        
        self.collection_tasks = []
        
        # Stop all collectors
        for collector in self.collectors.values():
            await collector.stop()
        
        self.collectors = {}
    
    async def _load_api_sources(self):
        """
        Load API sources from the database and initialize collectors.
        """
        try:
            # Get API sources from database
            api_sources = await self.db.get_api_sources(active=True)
            
            if not api_sources:
                logger.warning("No active API sources found in database")
                return
            
            logger.info(f"Loading {len(api_sources)} API sources")
            
            # Initialize collectors for each API source
            for api_source in api_sources:
                await self._add_collector(api_source)
                
        except Exception as e:
            logger.error(f"Error loading API sources: {str(e)}")
    
    async def _add_collector(self, api_source: ApiSource):
        """
        Add a collector for an API source.
        
        Args:
            api_source: The API source to add a collector for.
        """
        try:
            # Skip if collector already exists for this API
            if api_source.id in self.collectors:
                logger.debug(f"Collector already exists for API {api_source.id}")
                return
            
            # Check if we support this API type
            api_type = api_source.type.lower()
            if api_type not in self.collector_classes:
                logger.warning(f"Unsupported API type: {api_type} for API {api_source.id}")
                return
            
            # Create collector instance
            collector_class = self.collector_classes[api_type]
            collector = collector_class(api_source)
            
            # Initialize and add to collectors dict
            await collector.initialize()
            self.collectors[api_source.id] = collector
            
            logger.info(f"Added collector for API {api_source.name} ({api_source.id})")
            
        except Exception as e:
            logger.error(f"Error adding collector for API {api_source.id}: {str(e)}")
    
    async def _remove_collector(self, api_id: str):
        """
        Remove a collector for an API source.
        
        Args:
            api_id: The ID of the API source to remove.
        """
        try:
            # Check if collector exists
            if api_id not in self.collectors:
                logger.debug(f"No collector exists for API {api_id}")
                return
            
            # Stop and remove collector
            collector = self.collectors[api_id]
            await collector.stop()
            del self.collectors[api_id]
            
            logger.info(f"Removed collector for API {api_id}")
            
        except Exception as e:
            logger.error(f"Error removing collector for API {api_id}: {str(e)}")
    
    async def _collection_loop(self):
        """
        Main collection loop.
        """
        while self.running:
            try:
                # Collect metrics from all collectors
                collection_tasks = []
                for api_id, collector in self.collectors.items():
                    task = asyncio.create_task(self._collect_and_store(api_id, collector))
                    collection_tasks.append(task)
                
                # Wait for all collection tasks to complete
                if collection_tasks:
                    await asyncio.gather(*collection_tasks, return_exceptions=True)
                
                # Sleep before next collection cycle
                await asyncio.sleep(settings.COLLECTION_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {str(e)}")
                await asyncio.sleep(5)  # Sleep a bit before retrying
    
    async def _collect_and_store(self, api_id: str, collector: Any):
        """
        Collect metrics from a collector and store them in the database.
        
        Args:
            api_id: The ID of the API source.
            collector: The collector instance.
        """
        try:
            # Collect metrics
            metrics = await collector.collect_metrics()
            
            if not metrics:
                logger.debug(f"No metrics collected for API {api_id}")
                return
            
            # Store metrics in database
            await self.db.store_metrics(metrics)
            
            logger.debug(f"Collected and stored metrics for API {api_id}")
            
        except Exception as e:
            logger.error(f"Error collecting metrics for API {api_id}: {str(e)}")
    
    async def _watch_api_config(self):
        """
        Watch for API configuration changes.
        """
        last_check = datetime.utcnow()
        
        while self.running:
            try:
                # Get updated API sources
                updated_sources = await self.db.get_api_sources_updated_since(last_check)
                last_check = datetime.utcnow()
                
                if updated_sources:
                    logger.info(f"Detected {len(updated_sources)} API configuration changes")
                    
                    # Process each updated source
                    for api_source in updated_sources:
                        if not api_source.is_active and api_source.id in self.collectors:
                            # Remove collector for deactivated API
                            await self._remove_collector(api_source.id)
                        elif api_source.is_active:
                            # Add or update collector for active API
                            if api_source.id in self.collectors:
                                # Update existing collector
                                await self._remove_collector(api_source.id)
                            await self._add_collector(api_source)
                
                # Sleep before checking again
                await asyncio.sleep(30)  # Check for changes every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("API config watch cancelled")
                break
            except Exception as e:
                logger.error(f"Error watching API configuration: {str(e)}")
                await asyncio.sleep(5)  # Sleep a bit before retrying
    
    async def get_collector_status(self) -> Dict[str, Any]:
        """
        Get the status of all collectors.
        
        Returns:
            Dictionary of collector statuses.
        """
        status = {
            "running": self.running,
            "collector_count": len(self.collectors),
            "collectors": {}
        }
        
        for api_id, collector in self.collectors.items():
            status["collectors"][api_id] = {
                "type": collector.api_source.type,
                "name": collector.api_source.name,
                "active": collector.api_source.is_active,
                "status": "running" if collector.is_running() else "stopped",
                "last_collection": collector.last_collection.isoformat() if collector.last_collection else None,
                "metrics_collected": collector.metrics_count
            }
        
        return status 