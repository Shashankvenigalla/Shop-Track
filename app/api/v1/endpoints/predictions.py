"""
Predictions API endpoints for ML forecasts and predictions.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.rush_predictor import RushPredictor

router = APIRouter()
rush_predictor = RushPredictor()


@router.get("/rush-hours")
async def get_rush_hour_predictions(
    hours_ahead: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get rush hour predictions for the next N hours.
    
    Returns ML-powered predictions of high activity periods to help
    with staff scheduling and resource planning.
    """
    try:
        if hours_ahead > 168:  # Max 1 week ahead
            hours_ahead = 168
        
        predictions = await rush_predictor.predict_rush_hours(hours_ahead)
        
        return {
            "predictions": predictions,
            "hours_ahead": hours_ahead,
            "model_version": rush_predictor.model_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rush hour predictions: {str(e)}")


@router.get("/stored")
async def get_stored_predictions(
    hours_ahead: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get stored predictions from database.
    
    Returns previously generated predictions that are stored in the database.
    """
    try:
        if hours_ahead > 168:  # Max 1 week ahead
            hours_ahead = 168
        
        predictions = await rush_predictor.get_rush_predictions(hours_ahead)
        
        return {
            "predictions": predictions,
            "hours_ahead": hours_ahead
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stored predictions: {str(e)}")


@router.post("/retrain")
async def retrain_model(
    db: Session = Depends(get_db)
):
    """
    Retrain the ML prediction model.
    
    Triggers a retraining of the rush prediction model with latest data.
    """
    try:
        result = await rush_predictor.retrain_model()
        
        if result["status"] == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrain model: {str(e)}")


@router.get("/model-status")
async def get_model_status():
    """
    Get ML model status and information.
    
    Returns information about the current ML model including version,
    training status, and performance metrics.
    """
    try:
        return {
            "model_version": rush_predictor.model_version,
            "model_loaded": rush_predictor.rush_model is not None,
            "scaler_loaded": rush_predictor.scaler is not None,
            "last_trained": "Available" if rush_predictor.rush_model else "Not available"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model status: {str(e)}") 