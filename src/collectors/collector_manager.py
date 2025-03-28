"""
Collector manager for API monitoring system.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import settings
from src.collectors.base_collector import BaseCollector
from src.collectors.rest_collector import RestApiCollector
from src.collectors.graphql_collector import GraphQLCollector
from src.collectors.grpc_collector import GrpcCollector
from src.storage.database import get_database
from src.models.api import ApiSource, ApiType

logger = logging.getLogger(__name__)

class CollectorManager:
    """
    Manager for API collectors.
    """
    def __init__(self):
        """
        Initialize the collector manager.
        """
        self.collectors: Dict[str, BaseCollector] = {}
        self.running = False
        self.db = get_database()
        self.collection_tasks = []
    
    async def start_collection(self):
        """
        Start the collection process.
        """
        logger.info("Starting API metric collection")
        self.running = True
        
        # Load API sources from database
        await self.load_api_sources()
        
        # Start collection tasks
        collection_task = asyncio.create_task(self._collection_loop())
        self.collection_tasks.append(collection_task)
    
    async def stop_collection(self):
        """
        Stop the collection process.
        """
        logger.info("Stopping API metric collection")
        self.running = False
        
        # Cancel all collection tasks
        for task in self.collection_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.collection_tasks:
            await asyncio.gather(*self.collection_tasks, return_exceptions=True)
        
        self.collection_tasks = []
    
    async def load_api_sources(self):
        """
        Load API sources from the database.
        """
        try:
            api_sources = await self.db.get_api_sources()
            logger.info(f"Loaded {len(api_sources)} API sources from database")
            
            for api_source in api_sources:
                await self.add_collector(api_source)
        except Exception as e:
            logger.error(f"Error loading API sources: {str(e)}")
    
    async def add_collector(self, api_source: ApiSource):
        """
        Add a new collector for an API source.
        """
        if api_source.id in self.collectors:
            logger.debug(f"Collector for API {api_source.id} already exists, updating")
            self.collectors[api_source.id].update_config(api_source)
            return
        
        # Create collector based on API type
        collector = self._create_collector(api_source)
        if collector:
            self.collectors[api_source.id] = collector
            logger.info(f"Added collector for API {api_source.name} ({api_source.id})")
        else:
            logger.warning(f"Could not create collector for API {api_source.name} with type {api_source.type}")
    
    def remove_collector(self, api_id: str):
        """
        Remove a collector for an API source.
        """
        if api_id in self.collectors:
            # Clean up collector
            self.collectors[api_id].cleanup()
            del self.collectors[api_id]
            logger.info(f"Removed collector for API {api_id}")
    
    def _create_collector(self, api_source: ApiSource) -> Optional[BaseCollector]:
        """
        Create a collector based on API type.
        """
        if api_source.type == ApiType.REST:
            return RestApiCollector(api_source)
        elif api_source.type == ApiType.GRAPHQL:
            return GraphQLCollector(api_source)
        elif api_source.type == ApiType.GRPC:
            return GrpcCollector(api_source)
        # Add other collector types as needed
        return None
    
    async def _collection_loop(self):
        """
        Main collection loop.
        """
        while self.running:
            try:
                # Check for any configuration changes
                await self._check_configuration_changes()
                
                # Collect metrics from all collectors
                collection_tasks = []
                for api_id, collector in self.collectors.items():
                    if collector.should_collect():
                        task = asyncio.create_task(self._collect_and_store(api_id, collector))
                        collection_tasks.append(task)
                
                if collection_tasks:
                    # Wait for all collection tasks to complete
                    await asyncio.gather(*collection_tasks, return_exceptions=True)
                
                # Sleep before next collection cycle
                await asyncio.sleep(settings.ANOMALY_DETECTION_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {str(e)}")
                await asyncio.sleep(5)  # Sleep a bit before retrying
    
    async def _collect_and_store(self, api_id: str, collector: BaseCollector):
        """
        Collect metrics from a collector and store them.
        """
        try:
            metrics = await collector.collect_metrics()
            if metrics:
                # Store metrics in database
                await self.db.store_metrics(metrics)
                logger.debug(f"Collected and stored {len(metrics)} metrics for API {api_id}")
        except Exception as e:
            logger.error(f"Error collecting metrics for API {api_id}: {str(e)}")
    
    async def _check_configuration_changes(self):
        """
        Check for configuration changes in the database.
        """
        try:
            # Get updated API sources
            api_sources = await self.db.get_api_sources(updated_since=datetime.utcnow())
            
            # Update collectors with new configuration
            for api_source in api_sources:
                if api_source.id in self.collectors:
                    self.collectors[api_source.id].update_config(api_source)
                    logger.debug(f"Updated configuration for API {api_source.id}")
                else:
                    await self.add_collector(api_source)
            
            # Check for deleted API sources
            current_api_ids = set(api_source.id for api_source in api_sources)
            for api_id in list(self.collectors.keys()):
                if api_id not in current_api_ids:
                    self.remove_collector(api_id)
        except Exception as e:
            logger.error(f"Error checking configuration changes: {str(e)}") 