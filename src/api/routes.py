"""
API routes for the API Monitoring System.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query

from src.models.api import ApiSource, ApiMetric, Anomaly, Prediction, Alert, Environment, AnomalyTriggerRequest
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

# Demo Routes
@router.post("/demo/trigger-anomaly")
async def trigger_demo_anomaly(
    anomaly_data: AnomalyTriggerRequest,
    db: Database = Depends(get_db)
):
    """
    Trigger a demo anomaly for demonstration purposes.
    
    This endpoint is used for simulating different types of anomalies
    in the system, which will be detected by the anomaly detection system.
    """
    try:
        anomaly_type = anomaly_data.type
        environment = anomaly_data.environment
        environments = anomaly_data.environments or []
        severity = anomaly_data.severity
        duration_minutes = anomaly_data.duration_minutes
        
        logger.info(f"Triggering demo anomaly: {anomaly_type} in environment(s): {environment or environments}")
        
        # Map severity string to float value
        severity_map = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 1.0
        }
        severity_value = severity_map.get(severity, 0.6)
        
        # Create a demo anomaly record
        if anomaly_type == "response_time":
            # Create response time anomaly
            anomaly = Anomaly(
                id=f"anomaly-{datetime.utcnow().timestamp()}",
                api_id=f"{environment}-api-1",
                type="response_time_spike",
                severity=severity_value,
                description=f"Unusual response time increase in {environment} API",
                environment=Environment(environment),
                timestamp=datetime.utcnow(),
                metric_value=800.0,
                expected_value=200.0,
                threshold=400.0,
                context={
                    "expected_response_time": 200,
                    "actual_response_time": 800,
                    "duration_minutes": duration_minutes
                }
            )
            await db.store_anomaly(anomaly)
            
            # Also create an alert
            alert = Alert(
                id=f"alert-{datetime.utcnow().timestamp()}",
                title=f"Response Time Anomaly in {environment.upper()}",
                description=f"Response time has increased significantly in {environment} API",
                severity=severity_value,
                status="active",
                api_id=f"{environment}-api-1",
                environment=Environment(environment),
                environments=[Environment(environment)],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                anomalies=[anomaly.id],
                apis=[f"{environment}-api-1"],
                tags=["response_time", "demo"],
                metadata={"demo": True}
            )
            await db.store_alert(alert)
            
        elif anomaly_type == "error_rate":
            # Create error rate anomaly
            anomaly = Anomaly(
                id=f"anomaly-{datetime.utcnow().timestamp()}",
                api_id=f"{environment}-api-1",
                type="error_rate_spike",
                severity=severity_value,
                description=f"Unusual error rate increase in {environment} API",
                environment=Environment(environment),
                timestamp=datetime.utcnow(),
                metric_value=0.15,
                expected_value=0.01,
                threshold=0.05,
                context={
                    "expected_error_rate": 0.01,
                    "actual_error_rate": 0.15,
                    "duration_minutes": duration_minutes
                }
            )
            await db.store_anomaly(anomaly)
            
            # Also create an alert
            alert = Alert(
                id=f"alert-{datetime.utcnow().timestamp()}",
                title=f"Error Rate Spike in {environment.upper()}",
                description=f"Error rate has increased significantly in {environment} API",
                severity=severity_value,
                status="active",
                api_id=f"{environment}-api-1",
                environment=Environment(environment),
                environments=[Environment(environment)],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                anomalies=[anomaly.id],
                apis=[f"{environment}-api-1"],
                tags=["error_rate", "demo"],
                metadata={"demo": True}
            )
            await db.store_alert(alert)
            
        elif anomaly_type == "cross_environment":
            anomalies = []  # Store all created anomalies
            # Create anomalies for each environment
            for env in environments:
                anomaly = Anomaly(
                    id=f"anomaly-{env}-{datetime.utcnow().timestamp()}",
                    api_id=f"{env}-api-1",
                    type="cross_environment_failure",
                    severity=severity_value,
                    description=f"Cross-environment failure affecting {env}",
                    environment=Environment(env),
                    timestamp=datetime.utcnow(),
                    metric_value=1.0,
                    expected_value=0.0,
                    threshold=0.5,
                    context={
                        "affected_environments": environments,
                        "root_cause_environment": environments[0],
                        "duration_minutes": duration_minutes
                    }
                )
                await db.store_anomaly(anomaly)
                anomalies.append(anomaly)
                
            # Create a single alert for the cross-environment issue
            alert = Alert(
                id=f"alert-cross-env-{datetime.utcnow().timestamp()}",
                title=f"Cross-Environment Failure",
                description=f"Cascading failure detected across {', '.join(environments)} environments",
                severity=severity_value,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                environments=[Environment(env) for env in environments],
                anomalies=[a.id for a in anomalies],
                apis=[f"{env}-api-1" for env in environments],
                tags=["cross_environment", "demo"],
                metadata={"demo": True}
            )
            await db.store_alert(alert)
        
        # Create a prediction based on the anomaly
        prediction = Prediction(
            id=f"prediction-{datetime.utcnow().timestamp()}",
            api_id=f"{environment}-api-1" if environment else f"{environments[0]}-api-1",
            predicted_issues=[f"{anomaly_type}_will_continue"],
            confidence=0.85,
            timestamp=datetime.utcnow(),
            predicted_for=datetime.utcnow() + timedelta(minutes=30),
            environment=Environment(environment) if environment else Environment(environments[0]),
            context={
                "based_on_anomaly": anomaly_type,
                "severity": severity
            }
        )
        await db.store_prediction(prediction)
        
        return {
            "message": f"Successfully triggered {anomaly_type} anomaly",
            "status": "success",
            "anomaly_id": anomaly.id if anomaly_type != "cross_environment" else [f"anomaly-{env}" for env in environments],
            "alert_id": alert.id,
            "prediction_id": prediction.id
        }
    except Exception as e:
        logger.error(f"Error triggering demo anomaly: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard summary route
@router.get("/dashboard/summary")
async def get_dashboard_summary(db: Database = Depends(get_db)):
    """
    Get a summary of the system status for the dashboard.
    """
    try:
        # Get environments
        api_sources = await db.get_api_sources()
        environments = set()
        for source in api_sources:
            environments.add(source.environment)
        
        # Get active anomalies
        anomalies = await db.get_anomalies(
            start_time=datetime.utcnow() - timedelta(hours=24)
        )
        
        # Get active alerts
        alerts = await db.get_alerts(
            status="active"
        )
        
        # Calculate correlated issues
        correlated_issues = []
        env_issues = {}
        
        for anomaly in anomalies:
            env = anomaly.environment.value
            if env not in env_issues:
                env_issues[env] = []
            env_issues[env].append(anomaly)
        
        # Find anomalies that appear in multiple environments within a short time
        for env1, issues1 in env_issues.items():
            for env2, issues2 in env_issues.items():
                if env1 != env2:
                    for issue1 in issues1:
                        for issue2 in issues2:
                            if abs((issue1.timestamp - issue2.timestamp).total_seconds()) < 300:  # 5 minutes
                                correlated_issues.append({
                                    "id": f"corr-{issue1.id}-{issue2.id}",
                                    "environments": [env1, env2],
                                    "types": [issue1.type, issue2.type],
                                    "severity": max(issue1.severity, issue2.severity),
                                    "timestamp": max(issue1.timestamp, issue2.timestamp)
                                })
        
        # Calculate impact score
        impact_score = 0
        if anomalies:
            impact_score = sum(a.severity for a in anomalies) / len(anomalies)
            # Scale to 0-100
            impact_score = min(round(impact_score * 100), 100)
        
        return {
            "environments": [e.value for e in environments],
            "active_anomalies": len(anomalies),
            "active_alerts": len(alerts),
            "correlated_issues": correlated_issues,
            "impact_score": impact_score
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 