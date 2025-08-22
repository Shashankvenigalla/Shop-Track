"""
Rush Predictor service using ML to forecast peak checkout times and high activity periods.
"""
import asyncio
import logging
import pickle
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score
import joblib

from app.core.database import get_db_context
from app.core.redis_client import cache_manager
from app.models.sales import Sale, SaleItem
from app.models.predictions import Prediction, PredictionType, PredictionStatus
from app.models.alerts import Alert, AlertType, AlertSeverity
from app.services.alert_dispatcher import AlertDispatcher

logger = logging.getLogger(__name__)


class RushPredictor:
    """Service for predicting rush hours and high activity periods using ML."""
    
    def __init__(self):
        self.alert_dispatcher = AlertDispatcher()
        self.rush_model = None
        self.scaler = None
        self.label_encoder = None
        self.model_version = "1.0"
        self._load_or_train_model()
    
    def _load_or_train_model(self) -> None:
        """Load existing model or train a new one."""
        try:
            # Try to load existing model
            model_path = "models/rush_predictor.pkl"
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.rush_model = model_data['model']
                self.scaler = model_data['scaler']
                self.label_encoder = model_data['label_encoder']
                self.model_version = model_data.get('version', '1.0')
            logger.info("Loaded existing rush prediction model")
        except (FileNotFoundError, Exception) as e:
            logger.info(f"Training new rush prediction model: {e}")
            self._train_model()
    
    async def _train_model(self) -> None:
        """Train the rush prediction model."""
        try:
            # Get historical sales data
            sales_data = await self._get_historical_sales_data()
            
            if len(sales_data) < 100:  # Need minimum data points
                logger.warning("Insufficient data for training rush prediction model")
                return
            
            # Prepare features
            features, targets = self._prepare_training_data(sales_data)
            
            if len(features) == 0:
                logger.warning("No valid features for training")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.rush_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.rush_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.rush_model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            logger.info(f"Rush prediction model trained. MAE: {mae:.2f}")
            
            # Save model
            self._save_model()
            
        except Exception as e:
            logger.error(f"Failed to train rush prediction model: {e}")
    
    async def _get_historical_sales_data(self) -> List[Dict[str, Any]]:
        """Get historical sales data for training."""
        with get_db_context() as db:
            # Get sales from the last 90 days
            start_date = datetime.utcnow() - timedelta(days=90)
            
            sales = db.query(Sale).filter(
                Sale.created_at >= start_date,
                Sale.status == "completed"
            ).order_by(Sale.created_at).all()
            
            return [
                {
                    "created_at": sale.created_at,
                    "total_amount": sale.total_amount,
                    "items_count": len(sale.items),
                    "payment_method": sale.payment_method.value
                }
                for sale in sales
            ]
    
    def _prepare_training_data(self, sales_data: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[float]]:
        """Prepare features and targets for training."""
        features = []
        targets = []
        
        # Group sales by hour
        hourly_sales = {}
        for sale in sales_data:
            hour_key = sale['created_at'].replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_sales:
                hourly_sales[hour_key] = {
                    'total_amount': 0,
                    'transaction_count': 0,
                    'items_count': 0
                }
            hourly_sales[hour_key]['total_amount'] += sale['total_amount']
            hourly_sales[hour_key]['transaction_count'] += 1
            hourly_sales[hour_key]['items_count'] += sale['items_count']
        
        # Create features for each hour
        for hour, data in hourly_sales.items():
            # Time-based features
            hour_of_day = hour.hour
            day_of_week = hour.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            is_business_hour = 1 if 9 <= hour_of_day <= 17 else 0
            
            # Sales features
            total_amount = data['total_amount']
            transaction_count = data['transaction_count']
            items_count = data['items_count']
            avg_transaction_value = total_amount / transaction_count if transaction_count > 0 else 0
            
            # Create feature vector
            feature_vector = [
                hour_of_day,
                day_of_week,
                is_weekend,
                is_business_hour,
                total_amount,
                transaction_count,
                items_count,
                avg_transaction_value
            ]
            
            features.append(feature_vector)
            targets.append(transaction_count)  # Predict transaction count
        
        return features, targets
    
    def _save_model(self) -> None:
        """Save the trained model."""
        try:
            import os
            os.makedirs("models", exist_ok=True)
            
            model_data = {
                'model': self.rush_model,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'version': self.model_version,
                'trained_at': datetime.utcnow().isoformat()
            }
            
            with open("models/rush_predictor.pkl", 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info("Rush prediction model saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save rush prediction model: {e}")
    
    async def predict_rush_hours(self, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Predict rush hours for the next N hours."""
        if not self.rush_model:
            logger.warning("Rush prediction model not available")
            return []
        
        try:
            predictions = []
            current_time = datetime.utcnow()
            
            for i in range(hours_ahead):
                prediction_time = current_time + timedelta(hours=i)
                
                # Create features for prediction
                features = self._create_prediction_features(prediction_time)
                
                if not features:
                    continue
                
                # Scale features
                features_scaled = self.scaler.transform([features])
                
                # Make prediction
                predicted_transactions = self.rush_model.predict(features_scaled)[0]
                confidence = self._calculate_confidence(features_scaled[0])
                
                # Determine if this is a rush hour
                is_rush_hour = predicted_transactions > self._get_rush_threshold()
                
                prediction_data = {
                    "hour": prediction_time,
                    "predicted_transactions": max(0, predicted_transactions),
                    "confidence": confidence,
                    "is_rush_hour": is_rush_hour,
                    "rush_probability": self._calculate_rush_probability(predicted_transactions)
                }
                
                predictions.append(prediction_data)
                
                # Store prediction in database
                await self._store_prediction(prediction_data)
                
                # Create alert for high rush probability
                if prediction_data["rush_probability"] > 0.8:
                    await self._create_rush_alert(prediction_data)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict rush hours: {e}")
            return []
    
    def _create_prediction_features(self, prediction_time: datetime) -> List[float]:
        """Create feature vector for prediction."""
        try:
            # Time-based features
            hour_of_day = prediction_time.hour
            day_of_week = prediction_time.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            is_business_hour = 1 if 9 <= hour_of_day <= 17 else 0
            
            # Get recent sales data for context
            recent_sales = self._get_recent_sales_context(prediction_time)
            
            # Create feature vector
            features = [
                hour_of_day,
                day_of_week,
                is_weekend,
                is_business_hour,
                recent_sales.get('avg_amount', 0),
                recent_sales.get('avg_transactions', 0),
                recent_sales.get('avg_items', 0),
                recent_sales.get('avg_transaction_value', 0)
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to create prediction features: {e}")
            return []
    
    def _get_recent_sales_context(self, prediction_time: datetime) -> Dict[str, float]:
        """Get recent sales context for prediction."""
        try:
            # Get sales from similar time periods in recent history
            similar_hours = []
            current_time = datetime.utcnow()
            
            # Look back 4 weeks for similar hours
            for week in range(1, 5):
                for day in range(7):
                    similar_time = current_time - timedelta(weeks=week, days=day)
                    similar_time = similar_time.replace(
                        hour=prediction_time.hour,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    
                    # Get sales for this hour
                    with get_db_context() as db:
                        hour_sales = db.query(Sale).filter(
                            Sale.created_at >= similar_time,
                            Sale.created_at < similar_time + timedelta(hours=1),
                            Sale.status == "completed"
                        ).all()
                        
                        if hour_sales:
                            total_amount = sum(sale.total_amount for sale in hour_sales)
                            total_transactions = len(hour_sales)
                            total_items = sum(len(sale.items) for sale in hour_sales)
                            
                            similar_hours.append({
                                'total_amount': total_amount,
                                'transaction_count': total_transactions,
                                'items_count': total_items
                            })
            
            if not similar_hours:
                return {
                    'avg_amount': 0,
                    'avg_transactions': 0,
                    'avg_items': 0,
                    'avg_transaction_value': 0
                }
            
            # Calculate averages
            avg_amount = sum(h['total_amount'] for h in similar_hours) / len(similar_hours)
            avg_transactions = sum(h['transaction_count'] for h in similar_hours) / len(similar_hours)
            avg_items = sum(h['items_count'] for h in similar_hours) / len(similar_hours)
            avg_transaction_value = avg_amount / avg_transactions if avg_transactions > 0 else 0
            
            return {
                'avg_amount': avg_amount,
                'avg_transactions': avg_transactions,
                'avg_items': avg_items,
                'avg_transaction_value': avg_transaction_value
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent sales context: {e}")
            return {
                'avg_amount': 0,
                'avg_transactions': 0,
                'avg_items': 0,
                'avg_transaction_value': 0
            }
    
    def _calculate_confidence(self, features: List[float]) -> float:
        """Calculate prediction confidence."""
        try:
            # Use model's feature importances and prediction variance
            if hasattr(self.rush_model, 'estimators_'):
                predictions = []
                for estimator in self.rush_model.estimators_:
                    pred = estimator.predict([features])[0]
                    predictions.append(pred)
                
                # Calculate confidence based on prediction variance
                mean_pred = np.mean(predictions)
                std_pred = np.std(predictions)
                confidence = max(0, 1 - (std_pred / (mean_pred + 1e-6)))
                return min(1.0, confidence)
            
            return 0.7  # Default confidence
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5
    
    def _get_rush_threshold(self) -> float:
        """Get threshold for determining rush hours."""
        # This could be configurable or learned from data
        return 5.0  # More than 5 transactions per hour
    
    def _calculate_rush_probability(self, predicted_transactions: float) -> float:
        """Calculate probability that this hour will be a rush hour."""
        threshold = self._get_rush_threshold()
        # Simple sigmoid-like function
        probability = 1 / (1 + np.exp(-(predicted_transactions - threshold)))
        return min(1.0, probability)
    
    async def _store_prediction(self, prediction_data: Dict[str, Any]) -> None:
        """Store prediction in database."""
        try:
            with get_db_context() as db:
                prediction = Prediction(
                    prediction_type=PredictionType.RUSH_HOUR,
                    predicted_value=prediction_data["predicted_transactions"],
                    confidence_score=prediction_data["confidence"],
                    prediction_horizon=1,  # 1 hour ahead
                    prediction_for=prediction_data["hour"],
                    model_version=self.model_version,
                    model_parameters={
                        "model_type": "RandomForestRegressor",
                        "n_estimators": 100,
                        "max_depth": 10
                    },
                    output_details={
                        "is_rush_hour": prediction_data["is_rush_hour"],
                        "rush_probability": prediction_data["rush_probability"]
                    }
                )
                
                db.add(prediction)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to store prediction: {e}")
    
    async def _create_rush_alert(self, prediction_data: Dict[str, Any]) -> None:
        """Create alert for predicted rush hour."""
        try:
            with get_db_context() as db:
                await self.alert_dispatcher.create_alert(
                    db=db,
                    alert_type=AlertType.RUSH_HOUR,
                    severity=AlertSeverity.MEDIUM,
                    title=f"Rush Hour Predicted: {prediction_data['hour'].strftime('%Y-%m-%d %H:00')}",
                    message=f"High activity predicted with {prediction_data['predicted_transactions']:.1f} transactions and {prediction_data['rush_probability']:.1%} rush probability.",
                    details={
                        "predicted_transactions": prediction_data["predicted_transactions"],
                        "rush_probability": prediction_data["rush_probability"],
                        "confidence": prediction_data["confidence"]
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to create rush alert: {e}")
    
    async def get_rush_predictions(self, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get stored rush predictions."""
        try:
            with get_db_context() as db:
                predictions = db.query(Prediction).filter(
                    and_(
                        Prediction.prediction_type == PredictionType.RUSH_HOUR,
                        Prediction.prediction_for >= datetime.utcnow(),
                        Prediction.prediction_for <= datetime.utcnow() + timedelta(hours=hours_ahead),
                        Prediction.status == PredictionStatus.ACTIVE
                    )
                ).order_by(Prediction.prediction_for).all()
                
                return [
                    {
                        "hour": pred.prediction_for.isoformat(),
                        "predicted_transactions": pred.predicted_value,
                        "confidence": pred.confidence_score,
                        "is_rush_hour": pred.output_details.get("is_rush_hour", False),
                        "rush_probability": pred.output_details.get("rush_probability", 0.0)
                    }
                    for pred in predictions
                ]
                
        except Exception as e:
            logger.error(f"Failed to get rush predictions: {e}")
            return []
    
    async def retrain_model(self) -> Dict[str, Any]:
        """Retrain the rush prediction model."""
        try:
            logger.info("Starting model retraining...")
            await self._train_model()
            
            return {
                "status": "success",
                "message": "Model retrained successfully",
                "model_version": self.model_version,
                "trained_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to retrain model: {e}")
            return {
                "status": "error",
                "message": str(e)
            } 