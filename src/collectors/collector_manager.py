"""
Collector manager for API monitoring system.
"""
import asyncio
import logging
import socket
import re
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import uuid

from config.settings import settings
from src.collectors.base_collector import BaseCollector
from src.collectors.rest_collector import RestApiCollector
from src.collectors.graphql_collector import GraphQLCollector
from src.collectors.grpc_collector import GrpcCollector
from src.storage.database import get_database
from src.models.api import ApiSource, ApiType, Environment

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
        self.discovery_tasks = []
        self.known_endpoints: Set[str] = set()
        self.environments = settings.ENVIRONMENTS
    
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
        
        # Start API discovery tasks
        discovery_task = asyncio.create_task(self._discovery_loop())
        self.discovery_tasks.append(discovery_task)
    
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
        
        # Cancel all discovery tasks
        for task in self.discovery_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.collection_tasks:
            await asyncio.gather(*self.collection_tasks, return_exceptions=True)
        
        if self.discovery_tasks:
            await asyncio.gather(*self.discovery_tasks, return_exceptions=True)
        
        self.collection_tasks = []
        self.discovery_tasks = []
    
    async def load_api_sources(self):
        """
        Load API sources from the database.
        """
        try:
            api_sources = await self.db.get_api_sources()
            logger.info(f"Loaded {len(api_sources)} API sources from database")
            
            # Track known endpoints
            for api_source in api_sources:
                if api_source.endpoint:
                    self.known_endpoints.add(api_source.endpoint)
                
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
    
    # API Discovery methods
    
    async def _discovery_loop(self):
        """
        Main API discovery loop.
        """
        # Wait a bit before starting discovery to let the system initialize
        await asyncio.sleep(30)
        
        while self.running:
            try:
                logger.info("Running API discovery cycle")
                
                # Discover new API sources
                discovered_apis = await self.discover_new_api_sources()
                
                if discovered_apis:
                    logger.info(f"Discovered {len(discovered_apis)} new API sources")
                    
                    # Register each discovered API
                    for api_source in discovered_apis:
                        await self.register_api_source(api_source)
                
                # Sleep before next discovery cycle (longer interval than collection)
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                logger.info("Discovery loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {str(e)}")
                await asyncio.sleep(60)  # Sleep a bit before retrying
    
    async def discover_new_api_sources(self) -> List[ApiSource]:
        """
        Discover new API sources automatically.
        
        Returns:
            List of discovered API sources.
        """
        discovered_apis = []
        
        try:
            # Network scan discovery
            network_apis = await self._discover_from_network_scan()
            discovered_apis.extend(network_apis)
            
            # Log analysis discovery
            log_apis = await self._discover_from_logs()
            discovered_apis.extend(log_apis)
            
            # Filter out already known endpoints
            discovered_apis = [
                api for api in discovered_apis 
                if api.endpoint not in self.known_endpoints
            ]
            
            # Update known endpoints
            for api in discovered_apis:
                if api.endpoint:
                    self.known_endpoints.add(api.endpoint)
        except Exception as e:
            logger.error(f"Error discovering API sources: {str(e)}")
        
        return discovered_apis
    
    async def _discover_from_network_scan(self) -> List[ApiSource]:
        """
        Discover API sources by scanning the network.
        
        Returns:
            List of discovered API sources.
        """
        discovered_apis = []
        
        # This is a simplified implementation
        # In a real-world scenario, you'd use service discovery mechanisms 
        # like Consul, Eureka, or Kubernetes API
        
        # Example: Scan common ports on localhost
        common_ports = [8080, 8081, 8082, 8083, 3000, 4000, 5000]
        
        for port in common_ports:
            try:
                # Try to connect to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    # Port is open, try to identify API
                    endpoint = f"http://localhost:{port}"
                    
                    # Skip if already known
                    if endpoint in self.known_endpoints:
                        continue
                    
                    # Create API source
                    api_source = ApiSource(
                        id=str(uuid.uuid4()),
                        name=f"Discovered API on port {port}",
                        type=ApiType.REST,  # Assume REST by default
                        endpoint=endpoint,
                        environment=Environment.ON_PREMISES,  # Assume on-premises
                        active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    discovered_apis.append(api_source)
            except Exception as e:
                logger.debug(f"Error scanning port {port}: {str(e)}")
        
        return discovered_apis
    
    async def _discover_from_logs(self) -> List[ApiSource]:
        """
        Discover API sources by analyzing logs.
        
        Returns:
            List of discovered API sources.
        """
        discovered_apis = []
        
        # This is a simplified implementation
        # In a real-world scenario, you'd analyze log files or log streams
        
        # Example: Placeholder for log analysis logic
        # Here you would:
        # 1. Parse logs to find API calls
        # 2. Extract endpoints and API details
        # 3. Create ApiSource instances
        
        return discovered_apis
    
    async def register_api_source(self, api_source: ApiSource) -> bool:
        """
        Register a discovered API source.
        
        Args:
            api_source: The API source to register.
            
        Returns:
            True if registered successfully, False otherwise.
        """
        try:
            # Store in database
            api_id = await self.db.store_api_source(api_source)
            
            # Add collector
            await self.add_collector(api_source)
            
            logger.info(f"Registered new API source: {api_source.name} ({api_id})")
            return True
        except Exception as e:
            logger.error(f"Error registering API source: {str(e)}")
            return False 