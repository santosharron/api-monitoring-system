"""
Analyzer manager for API monitoring system.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from config.settings import Settings
from src.analyzers.base_analyzer import BaseAnalyzer
from src.analyzers.response_time_analyzer import ResponseTimeAnalyzer
from src.analyzers.error_rate_analyzer import ErrorRateAnalyzer
from src.analyzers.pattern_analyzer import PatternAnalyzer
from src.analyzers.cross_environment_analyzer import CrossEnvironmentAnalyzer
from src.storage.database import get_database
from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction

logger = logging.getLogger(__name__)

# Create settings instance
settings = Settings()

class AnalyzerManager:
    """
    Manager for API analyzers.
    """
    def __init__(self):
        """
        Initialize the analyzer manager.
        """
        self.analyzers: Dict[str, List[BaseAnalyzer]] = {}
        self.running = False
        self.db = get_database()
        self.analysis_tasks = []
        self.global_analyzers = []
        
        # Initialize global analyzers (analyzers that work across all APIs)
        self._init_global_analyzers()
    
    def _init_global_analyzers(self):
        """
        Initialize global analyzers.
        """
        # Cross-environment analyzer for detecting anomalies across environments
        cross_env_analyzer = CrossEnvironmentAnalyzer()
        self.global_analyzers.append(cross_env_analyzer)
    
    async def start_analysis(self):
        """
        Start the analysis process.
        """
        logger.info("Starting API metric analysis")
        self.running = True
        
        # Load API sources from database
        await self.load_api_sources()
        
        # Start analysis tasks
        analysis_task = asyncio.create_task(self._analysis_loop())
        self.analysis_tasks.append(analysis_task)
    
    async def stop_analysis(self):
        """
        Stop the analysis process.
        """
        logger.info("Stopping API metric analysis")
        self.running = False
        
        # Cancel all analysis tasks
        for task in self.analysis_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.analysis_tasks:
            await asyncio.gather(*self.analysis_tasks, return_exceptions=True)
        
        self.analysis_tasks = []
    
    async def load_api_sources(self):
        """
        Load API sources from the database and initialize analyzers.
        """
        try:
            api_sources = await self.db.get_api_sources()
            logger.info(f"Loaded {len(api_sources)} API sources for analysis")
            
            for api_source in api_sources:
                await self.add_analyzers(api_source)
        except Exception as e:
            logger.error(f"Error loading API sources for analysis: {str(e)}")
    
    async def add_analyzers(self, api_source: ApiSource):
        """
        Add analyzers for an API source.
        """
        if api_source.id in self.analyzers:
            logger.debug(f"Analyzers for API {api_source.id} already exist, updating")
            for analyzer in self.analyzers[api_source.id]:
                analyzer.update_config(api_source)
            return
        
        # Create analyzers for this API
        api_analyzers = self._create_analyzers(api_source)
        if api_analyzers:
            self.analyzers[api_source.id] = api_analyzers
            logger.info(f"Added {len(api_analyzers)} analyzers for API {api_source.name} ({api_source.id})")
        else:
            logger.warning(f"Could not create analyzers for API {api_source.name}")
    
    def remove_analyzers(self, api_id: str):
        """
        Remove analyzers for an API source.
        """
        if api_id in self.analyzers:
            # Clean up analyzers
            for analyzer in self.analyzers[api_id]:
                analyzer.cleanup()
            del self.analyzers[api_id]
            logger.info(f"Removed analyzers for API {api_id}")
    
    def _create_analyzers(self, api_source: ApiSource) -> List[BaseAnalyzer]:
        """
        Create analyzers for an API source.
        """
        analyzers = []
        
        # Add response time analyzer
        response_time_analyzer = ResponseTimeAnalyzer(api_source)
        analyzers.append(response_time_analyzer)
        
        # Add error rate analyzer
        error_rate_analyzer = ErrorRateAnalyzer(api_source)
        analyzers.append(error_rate_analyzer)
        
        # Add pattern analyzer
        pattern_analyzer = PatternAnalyzer(api_source)
        analyzers.append(pattern_analyzer)
        
        return analyzers
    
    async def _analysis_loop(self):
        """
        Main analysis loop.
        """
        while self.running:
            try:
                # Check for any configuration changes
                await self._check_configuration_changes()
                
                # Gather metrics for analysis
                window_end = datetime.utcnow()
                window_start = window_end - timedelta(seconds=settings.ANOMALY_DETECTION_WINDOW)
                
                # Analyze metrics for each API
                analysis_tasks = []
                for api_id, analyzers in self.analyzers.items():
                    for analyzer in analyzers:
                        task = asyncio.create_task(
                            self._analyze_and_store(api_id, analyzer, window_start, window_end)
                        )
                        analysis_tasks.append(task)
                
                # Run global analyzers that work across all APIs
                for analyzer in self.global_analyzers:
                    task = asyncio.create_task(
                        self._run_global_analyzer(analyzer, window_start, window_end)
                    )
                    analysis_tasks.append(task)
                
                if analysis_tasks:
                    # Wait for all analysis tasks to complete
                    await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Sleep before next analysis cycle
                await asyncio.sleep(settings.ANOMALY_DETECTION_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Analysis loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in analysis loop: {str(e)}")
                await asyncio.sleep(5)  # Sleep a bit before retrying
    
    async def _analyze_and_store(
        self, 
        api_id: str, 
        analyzer: BaseAnalyzer, 
        window_start: datetime, 
        window_end: datetime
    ):
        """
        Analyze metrics and store results.
        """
        try:
            # Get metrics for the API in the time window
            metrics = await self.db.get_metrics(
                api_id=api_id,
                start_time=window_start,
                end_time=window_end
            )
            
            if not metrics:
                logger.debug(f"No metrics found for API {api_id} in the specified time window")
                return
            
            # Detect anomalies
            anomalies = await analyzer.detect_anomalies(metrics)
            if anomalies:
                # Store anomalies in database
                await self.db.store_anomalies(anomalies)
                logger.info(f"Detected and stored {len(anomalies)} anomalies for API {api_id}")
            
            # Make predictions
            predictions = await analyzer.predict_issues(metrics)
            if predictions:
                # Store predictions in database
                await self.db.store_predictions(predictions)
                logger.info(f"Generated and stored {len(predictions)} predictions for API {api_id}")
        except Exception as e:
            logger.error(f"Error analyzing metrics for API {api_id}: {str(e)}")
    
    async def _run_global_analyzer(
        self, 
        analyzer: BaseAnalyzer, 
        window_start: datetime, 
        window_end: datetime
    ):
        """
        Run a global analyzer that works across all APIs.
        """
        try:
            # Get all metrics in the time window
            metrics = await self.db.get_all_metrics(
                start_time=window_start,
                end_time=window_end
            )
            
            if not metrics:
                logger.debug("No metrics found in the specified time window")
                return
            
            # Detect cross-API anomalies
            anomalies = await analyzer.detect_anomalies(metrics)
            if anomalies:
                # Store anomalies in database
                await self.db.store_anomalies(anomalies)
                logger.info(f"Detected and stored {len(anomalies)} cross-API anomalies")
            
            # Make cross-API predictions
            predictions = await analyzer.predict_issues(metrics)
            if predictions:
                # Store predictions in database
                await self.db.store_predictions(predictions)
                logger.info(f"Generated and stored {len(predictions)} cross-API predictions")
        except Exception as e:
            logger.error(f"Error running global analyzer: {str(e)}")
    
    async def _check_configuration_changes(self):
        """
        Check for configuration changes in the database.
        """
        try:
            # Get updated API sources
            api_sources = await self.db.get_api_sources(updated_since=datetime.utcnow())
            
            # Update analyzers with new configuration
            for api_source in api_sources:
                if api_source.id in self.analyzers:
                    for analyzer in self.analyzers[api_source.id]:
                        analyzer.update_config(api_source)
                    logger.debug(f"Updated configuration for API {api_source.id} analyzers")
                else:
                    await self.add_analyzers(api_source)
            
            # Check for deleted API sources
            current_api_ids = set(api_source.id for api_source in api_sources)
            for api_id in list(self.analyzers.keys()):
                if api_id not in current_api_ids:
                    self.remove_analyzers(api_id)
        except Exception as e:
            logger.error(f"Error checking configuration changes for analyzers: {str(e)}") 