"""
API routes for the API Monitoring System.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query

from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Alert, Environment
from src.storage.database import get_database, Database
from src.alerting.alert_manager import AlertManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create alert manager instance
alert_manager = AlertManager()

# Database dependency
async def get_db():
    """
    Get database instance.
    """
    db = get_database()
    await db.connect()
    try:
        yield db
    finally:
        pass  # Connection is maintained for the application lifetime


# API Source routes

@router.post("/sources", response_model=ApiSource)
async def create_source(api_source: ApiSource, db: Database = Depends(get_db)):
    """
    Create a new API source.
    """
    try:
        api_id = await db.store_api_source(api_source)
        return await db.get_api_source(api_id)
    except Exception as e:
        logger.error(f"Error creating API source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources", response_model=List[ApiSource])
async def get_sources(db: Database = Depends(get_db)):
    """
    Get all API sources.
    """
    try:
        return await db.get_api_sources()
    except Exception as e:
        logger.error(f"Error getting API sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/{api_id}", response_model=ApiSource)
async def get_source(api_id: str, db: Database = Depends(get_db)):
    """
    Get an API source by ID.
    """
    try:
        api_source = await db.get_api_source(api_id)
        if not api_source:
            raise HTTPException(status_code=404, detail="API source not found")
        return api_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sources/{api_id}", response_model=ApiSource)
async def update_source(api_id: str, api_source: ApiSource, db: Database = Depends(get_db)):
    """
    Update an API source.
    """
    try:
        # Ensure the API source exists
        existing = await db.get_api_source(api_id)
        if not existing:
            raise HTTPException(status_code=404, detail="API source not found")
        
        # Update the ID to match the path parameter
        api_source.id = api_id
        
        # Store the updated API source
        await db.store_api_source(api_source)
        return await db.get_api_source(api_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sources/{api_id}")
async def delete_source(api_id: str, db: Database = Depends(get_db)):
    """
    Delete an API source.
    """
    try:
        deleted = await db.delete_api_source(api_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="API source not found")
        return {"message": f"API source {api_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics routes

@router.get("/metrics", response_model=List[ApiMetric])
async def get_metrics(
    api_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    environment: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    limit: int = Query(default=1000, le=10000),
    db: Database = Depends(get_db)
):
    """
    Get API metrics.
    """
    try:
        # Convert environment string to enum if provided
        env = None
        if environment:
            try:
                env = Environment(environment)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {environment}")
        
        # Default time range to last hour if not specified
        if not start_time and not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
        
        return await db.get_metrics(
            api_id=api_id,
            start_time=start_time,
            end_time=end_time,
            environment=env,
            endpoint=endpoint,
            method=method,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Anomaly routes

@router.get("/anomalies", response_model=List[Anomaly])
async def get_anomalies(
    api_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    anomaly_type: Optional[str] = None,
    environment: Optional[str] = None,
    min_severity: Optional[float] = None,
    limit: int = Query(default=100, le=1000),
    db: Database = Depends(get_db)
):
    """
    Get anomalies.
    """
    try:
        # Convert environment string to enum if provided
        env = None
        if environment:
            try:
                env = Environment(environment)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {environment}")
        
        # Default time range to last 24 hours if not specified
        if not start_time and not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
        
        return await db.get_anomalies(
            api_id=api_id,
            start_time=start_time,
            end_time=end_time,
            anomaly_type=anomaly_type,
            environment=env,
            min_severity=min_severity,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Prediction routes

@router.get("/predictions", response_model=List[Prediction])
async def get_predictions(
    api_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    prediction_type: Optional[str] = None,
    environment: Optional[str] = None,
    min_confidence: Optional[float] = None,
    limit: int = Query(default=100, le=1000),
    db: Database = Depends(get_db)
):
    """
    Get predictions.
    """
    try:
        # Convert environment string to enum if provided
        env = None
        if environment:
            try:
                env = Environment(environment)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {environment}")
        
        # Default time range to next 24 hours if not specified
        if not start_time and not end_time:
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(hours=24)
        
        return await db.get_predictions(
            api_id=api_id,
            start_time=start_time,
            end_time=end_time,
            prediction_type=prediction_type,
            environment=env,
            min_confidence=min_confidence,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert routes

@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    api_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    environment: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    db: Database = Depends(get_db)
):
    """
    Get alerts.
    """
    try:
        # Convert environment string to enum if provided
        env = None
        if environment:
            try:
                env = Environment(environment)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {environment}")
        
        # Convert status to list if provided
        statuses = None
        if status:
            statuses = [s.strip() for s in status.split(",")]
        
        return await db.get_alerts(
            api_id=api_id,
            statuses=statuses,
            severity=severity,
            environment=env,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str, db: Database = Depends(get_db)):
    """
    Get an alert by ID.
    """
    try:
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: str, db: Database = Depends(get_db)):
    """
    Acknowledge an alert.
    """
    try:
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await alert_manager.acknowledge_alert(alert_id, user)
        return {"message": f"Alert {alert_id} acknowledged by {user}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: str, db: Database = Depends(get_db)):
    """
    Resolve an alert.
    """
    try:
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await alert_manager.resolve_alert(alert_id, user)
        return {"message": f"Alert {alert_id} resolved by {user}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/snooze")
async def snooze_alert(alert_id: str, duration_minutes: int, user: str, db: Database = Depends(get_db)):
    """
    Snooze an alert for a specified duration.
    """
    try:
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="Duration must be positive")
        
        await alert_manager.snooze_alert(alert_id, duration_minutes, user)
        return {"message": f"Alert {alert_id} snoozed for {duration_minutes} minutes by {user}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error snoozing alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard data routes

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    api_id: Optional[str] = None,
    environment: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """
    Get summary data for dashboard.
    """
    try:
        # Convert environment string to enum if provided
        env = None
        if environment:
            try:
                env = Environment(environment)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid environment: {environment}")
        
        # Set time ranges
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Get active alerts
        active_alerts = await alert_manager.get_active_alerts(api_id, env)
        
        # Get recent anomalies
        recent_anomalies = await db.get_anomalies(
            api_id=api_id,
            start_time=one_hour_ago,
            environment=env,
            limit=100
        )
        
        # Get predictions for the next day
        predictions = await db.get_predictions(
            api_id=api_id,
            start_time=now,
            end_time=now + timedelta(days=1),
            environment=env,
            min_confidence=0.7,
            limit=100
        )
        
        # Count metrics in the last hour
        # This is a rough approximation without actually counting all metrics
        recent_metrics = await db.get_metrics(
            api_id=api_id,
            start_time=one_hour_ago,
            environment=env,
            limit=1
        )
        metrics_count = len(recent_metrics)
        
        # Prepare summary data
        summary = {
            "active_alerts_count": len(active_alerts),
            "critical_alerts_count": sum(1 for a in active_alerts if a.severity == "critical"),
            "high_alerts_count": sum(1 for a in active_alerts if a.severity == "high"),
            "recent_anomalies_count": len(recent_anomalies),
            "predictions_count": len(predictions),
            "metrics_in_last_hour": metrics_count,
            "environments": list(set(a.environment.value for a in active_alerts if a.environment)) if active_alerts else [],
            "top_affected_apis": [
                {"api_id": api_id, "count": count}
                for api_id, count in _count_apis(active_alerts).items()
            ][:5],
            "timestamp": now.isoformat()
        }
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _count_apis(alerts: List[Alert]) -> dict:
    """
    Count occurrences of each API in alerts.
    
    Args:
        alerts: List of alerts.
        
    Returns:
        Dictionary mapping API IDs to counts.
    """
    api_counts = {}
    
    for alert in alerts:
        for api_id in alert.apis:
            if api_id not in api_counts:
                api_counts[api_id] = 0
            api_counts[api_id] += 1
    
    # Sort by count (descending)
    return dict(sorted(api_counts.items(), key=lambda x: x[1], reverse=True)) 