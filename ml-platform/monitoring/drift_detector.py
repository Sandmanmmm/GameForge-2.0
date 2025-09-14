#!/usr/bin/env python3
"""
GameForge ML Monitoring and Drift Detection

Monitors model performance, data drift, and concept drift in production.
Includes automated alerting and remediation workflows.
"""

import os
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import hashlib
import scipy.stats as stats
from sklearn.metrics import accuracy_score, precision_score, recall_score
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
import sqlite3
import boto3
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart


@dataclass
class DriftDetectionResult:
    """Results from drift detection analysis"""
    metric_name: str
    drift_detected: bool
    drift_score: float
    threshold: float
    severity: str  # low, medium, high, critical
    timestamp: datetime
    details: Dict[str, Any]
    recommended_actions: List[str]


@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics over time"""
    model_id: str
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    latency_p50: float
    latency_p95: float
    throughput: float
    error_rate: float
    memory_usage: float
    cpu_usage: float
    custom_metrics: Dict[str, float]


@dataclass
class DataDriftMetrics:
    """Data drift metrics for input features"""
    feature_name: str
    timestamp: datetime
    kl_divergence: float
    js_divergence: float
    psi_score: float  # Population Stability Index
    drift_magnitude: float
    distribution_shift: Dict[str, Any]


class MLMonitor:
    """
    ML Monitoring and Drift Detection System
    
    Monitors:
    - Model performance degradation
    - Data drift (feature distribution changes)
    - Concept drift (target distribution changes)
    - Infrastructure metrics (latency, throughput, etc.)
    """
    
    def __init__(self, config_path: str = None):
        """Initialize ML monitoring system"""
        
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "monitoring-config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize storage and database
        self._init_storage()
        self._init_database()
        
        # Initialize alerting
        self._init_alerting()
        
        self.logger.info("✅ ML Monitor initialized")
    
    
    def _setup_logging(self):
        """Setup monitoring logging"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "ml_monitor.log"),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    
    def _init_storage(self):
        """Initialize S3 storage for monitoring data"""
        self.s3_client = boto3.client('s3')
        self.monitoring_bucket = self.config['storage']['bucket']
        self.monitoring_prefix = self.config['storage']['prefix']
    
    
    def _init_database(self):
        """Initialize monitoring database"""
        db_path = Path(__file__).parent / "monitoring.db"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_monitoring_tables()
    
    
    def _init_alerting(self):
        """Initialize alerting configuration"""
        self.alert_channels = self.config.get('alerting', {}).get('channels', [])
        self.alert_thresholds = self.config.get('alerting', {}).get('thresholds', {})
    
    
    def _create_monitoring_tables(self):
        """Create database tables for monitoring data"""
        
        # Model performance metrics
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                accuracy REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                latency_p50 REAL,
                latency_p95 REAL,
                throughput REAL,
                error_rate REAL,
                memory_usage REAL,
                cpu_usage REAL,
                custom_metrics TEXT
            )
        ''')
        
        # Data drift detection results
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS drift_detection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                drift_detected BOOLEAN NOT NULL,
                drift_score REAL NOT NULL,
                threshold_value REAL NOT NULL,
                severity TEXT NOT NULL,
                kl_divergence REAL,
                js_divergence REAL,
                psi_score REAL,
                details TEXT,
                actions_taken TEXT
            )
        ''')
        
        # Alert history
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                resolution_notes TEXT
            )
        ''')
        
        # Baseline data distributions
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS baseline_distributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                distribution_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        self.conn.commit()
    
    
    def establish_baseline(self, 
                          model_id: str,
                          baseline_data: pd.DataFrame,
                          target_column: str = None) -> bool:
        """
        Establish baseline distributions for drift detection
        
        Args:
            model_id: Model identifier
            baseline_data: Historical data for baseline
            target_column: Target variable column name
            
        Returns:
            bool: Whether baseline was successfully established
        """
        
        try:
            self.logger.info(f"Establishing baseline for model {model_id}")
            
            # Analyze feature distributions
            for column in baseline_data.columns:
                if column == target_column:
                    continue
                
                feature_data = baseline_data[column].dropna()
                
                if len(feature_data) == 0:
                    continue
                
                # Determine distribution type and parameters
                if pd.api.types.is_numeric_dtype(feature_data):
                    # Fit normal distribution
                    mean = float(feature_data.mean())
                    std = float(feature_data.std())
                    
                    distribution_params = {
                        'type': 'normal',
                        'mean': mean,
                        'std': std,
                        'min': float(feature_data.min()),
                        'max': float(feature_data.max()),
                        'percentiles': {
                            '25': float(feature_data.quantile(0.25)),
                            '50': float(feature_data.quantile(0.50)),
                            '75': float(feature_data.quantile(0.75)),
                            '95': float(feature_data.quantile(0.95)),
                            '99': float(feature_data.quantile(0.99))
                        }
                    }
                    
                else:
                    # Categorical distribution
                    value_counts = feature_data.value_counts()
                    total_count = len(feature_data)
                    
                    distribution_params = {
                        'type': 'categorical',
                        'categories': value_counts.index.tolist(),
                        'probabilities': (value_counts / total_count).tolist(),
                        'unique_count': len(value_counts),
                        'top_categories': value_counts.head(10).to_dict()
                    }
                
                # Store baseline distribution
                self._store_baseline_distribution(
                    model_id, column, distribution_params
                )
            
            self.logger.info(f"✅ Baseline established for {len(baseline_data.columns)} features")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to establish baseline: {e}")
            return False
    
    
    def _store_baseline_distribution(self, 
                                   model_id: str, 
                                   feature_name: str, 
                                   distribution_params: Dict):
        """Store baseline distribution parameters"""
        
        now = datetime.utcnow()
        
        self.conn.execute('''
            INSERT OR REPLACE INTO baseline_distributions
            (model_id, feature_name, distribution_type, parameters, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            model_id,
            feature_name,
            distribution_params['type'],
            json.dumps(distribution_params),
            now,
            now
        ))
        
        self.conn.commit()
    
    
    def detect_data_drift(self, 
                         model_id: str,
                         current_data: pd.DataFrame,
                         reference_window_days: int = 30) -> List[DriftDetectionResult]:
        """
        Detect data drift in input features
        
        Args:
            model_id: Model identifier
            current_data: Recent data to check for drift
            reference_window_days: Days of historical data for reference
            
        Returns:
            List of drift detection results
        """
        
        drift_results = []
        
        try:
            self.logger.info(f"Detecting data drift for model {model_id}")
            
            # Get baseline distributions
            baseline_distributions = self._get_baseline_distributions(model_id)
            
            if not baseline_distributions:
                self.logger.warning(f"No baseline found for model {model_id}")
                return drift_results
            
            for feature_name, baseline_params in baseline_distributions.items():
                if feature_name not in current_data.columns:
                    continue
                
                current_feature_data = current_data[feature_name].dropna()
                
                if len(current_feature_data) == 0:
                    continue
                
                # Calculate drift metrics based on data type
                if baseline_params['type'] == 'normal':
                    drift_result = self._detect_numerical_drift(
                        feature_name, baseline_params, current_feature_data
                    )
                else:
                    drift_result = self._detect_categorical_drift(
                        feature_name, baseline_params, current_feature_data
                    )
                
                if drift_result:
                    drift_results.append(drift_result)
                    
                    # Store drift detection result
                    self._store_drift_result(model_id, drift_result)
            
            self.logger.info(f"Drift detection completed: {len(drift_results)} issues found")
            
            # Send alerts if necessary
            self._process_drift_alerts(model_id, drift_results)
            
            return drift_results
            
        except Exception as e:
            self.logger.error(f"❌ Drift detection failed: {e}")
            return drift_results
    
    
    def _get_baseline_distributions(self, model_id: str) -> Dict[str, Dict]:
        """Get baseline distributions for a model"""
        
        cursor = self.conn.execute('''
            SELECT feature_name, parameters 
            FROM baseline_distributions 
            WHERE model_id = ?
        ''', (model_id,))
        
        distributions = {}
        for row in cursor.fetchall():
            feature_name = row[0]
            parameters = json.loads(row[1])
            distributions[feature_name] = parameters
        
        return distributions
    
    
    def _detect_numerical_drift(self, 
                               feature_name: str, 
                               baseline_params: Dict, 
                               current_data: pd.Series) -> Optional[DriftDetectionResult]:
        """Detect drift in numerical features"""
        
        # Calculate KL divergence
        baseline_mean = baseline_params['mean']
        baseline_std = baseline_params['std']
        
        current_mean = float(current_data.mean())
        current_std = float(current_data.std())
        
        # KL divergence between two normal distributions
        kl_div = np.log(current_std / baseline_std) + \
                (baseline_std**2 + (baseline_mean - current_mean)**2) / (2 * current_std**2) - 0.5
        
        # Population Stability Index (PSI)
        psi_score = self._calculate_psi(baseline_params, current_data)
        
        # Determine drift severity
        drift_score = max(kl_div, psi_score)
        drift_detected = False
        severity = "low"
        
        thresholds = self.config.get('drift_thresholds', {})
        
        if drift_score > thresholds.get('critical', 0.5):
            drift_detected = True
            severity = "critical"
        elif drift_score > thresholds.get('high', 0.3):
            drift_detected = True
            severity = "high"
        elif drift_score > thresholds.get('medium', 0.2):
            drift_detected = True
            severity = "medium"
        elif drift_score > thresholds.get('low', 0.1):
            drift_detected = True
            severity = "low"
        
        # Generate recommendations
        recommendations = []
        if drift_detected:
            if severity in ['high', 'critical']:
                recommendations.extend([
                    "Retrain model with recent data",
                    "Update feature engineering pipeline",
                    "Investigate data source changes"
                ])
            else:
                recommendations.extend([
                    "Monitor closely",
                    "Schedule model evaluation"
                ])
        
        return DriftDetectionResult(
            metric_name=feature_name,
            drift_detected=drift_detected,
            drift_score=drift_score,
            threshold=thresholds.get('medium', 0.2),
            severity=severity,
            timestamp=datetime.utcnow(),
            details={
                'kl_divergence': kl_div,
                'psi_score': psi_score,
                'baseline_mean': baseline_mean,
                'baseline_std': baseline_std,
                'current_mean': current_mean,
                'current_std': current_std
            },
            recommended_actions=recommendations
        )
    
    
    def _detect_categorical_drift(self, 
                                 feature_name: str, 
                                 baseline_params: Dict, 
                                 current_data: pd.Series) -> Optional[DriftDetectionResult]:
        """Detect drift in categorical features"""
        
        baseline_categories = baseline_params['categories']
        baseline_probs = baseline_params['probabilities']
        
        # Current distribution
        current_counts = current_data.value_counts()
        current_total = len(current_data)
        
        # Calculate Jensen-Shannon divergence
        js_div = self._calculate_js_divergence(
            baseline_categories, baseline_probs, 
            current_counts, current_total
        )
        
        # Calculate PSI for categorical data
        psi_score = self._calculate_categorical_psi(
            baseline_categories, baseline_probs,
            current_counts, current_total
        )
        
        drift_score = max(js_div, psi_score)
        drift_detected = False
        severity = "low"
        
        thresholds = self.config.get('drift_thresholds', {})
        
        if drift_score > thresholds.get('critical', 0.5):
            drift_detected = True
            severity = "critical"
        elif drift_score > thresholds.get('high', 0.3):
            drift_detected = True
            severity = "high"
        elif drift_score > thresholds.get('medium', 0.2):
            drift_detected = True
            severity = "medium"
        elif drift_score > thresholds.get('low', 0.1):
            drift_detected = True
            severity = "low"
        
        recommendations = []
        if drift_detected:
            recommendations.extend([
                "Analyze new category distributions",
                "Update data validation rules",
                "Consider model retraining"
            ])
        
        return DriftDetectionResult(
            metric_name=feature_name,
            drift_detected=drift_detected,
            drift_score=drift_score,
            threshold=thresholds.get('medium', 0.2),
            severity=severity,
            timestamp=datetime.utcnow(),
            details={
                'js_divergence': js_div,
                'psi_score': psi_score,
                'new_categories': list(set(current_counts.index) - set(baseline_categories)),
                'missing_categories': list(set(baseline_categories) - set(current_counts.index))
            },
            recommended_actions=recommendations
        )
    
    
    def _calculate_psi(self, baseline_params: Dict, current_data: pd.Series) -> float:
        """Calculate Population Stability Index"""
        
        # Create bins based on baseline percentiles
        percentiles = baseline_params['percentiles']
        bins = [
            baseline_params['min'],
            percentiles['25'],
            percentiles['50'],
            percentiles['75'],
            percentiles['95'],
            baseline_params['max']
        ]
        
        # Add some buffer for outliers
        bins[0] = bins[0] - abs(bins[0]) * 0.1
        bins[-1] = bins[-1] + abs(bins[-1]) * 0.1
        
        # Calculate expected frequencies (uniform for simplicity)
        expected_freq = 1.0 / len(bins)
        
        # Calculate actual frequencies
        binned_data = pd.cut(current_data, bins=bins, include_lowest=True)
        actual_freq = binned_data.value_counts(normalize=True, sort=False)
        
        # Calculate PSI
        psi = 0.0
        for i, freq in enumerate(actual_freq):
            if freq > 0:
                psi += (freq - expected_freq) * np.log(freq / expected_freq)
        
        return psi
    
    
    def _calculate_js_divergence(self, baseline_categories, baseline_probs, 
                                current_counts, current_total) -> float:
        """Calculate Jensen-Shannon divergence for categorical data"""
        
        # Align distributions
        all_categories = list(set(baseline_categories) | set(current_counts.index))
        
        baseline_dist = np.zeros(len(all_categories))
        current_dist = np.zeros(len(all_categories))
        
        for i, cat in enumerate(all_categories):
            if cat in baseline_categories:
                idx = baseline_categories.index(cat)
                baseline_dist[i] = baseline_probs[idx]
            
            if cat in current_counts.index:
                current_dist[i] = current_counts[cat] / current_total
        
        # Add small epsilon to avoid log(0)
        epsilon = 1e-8
        baseline_dist += epsilon
        current_dist += epsilon
        
        # Normalize
        baseline_dist /= baseline_dist.sum()
        current_dist /= current_dist.sum()
        
        # Calculate JS divergence
        m = 0.5 * (baseline_dist + current_dist)
        js_div = 0.5 * stats.entropy(baseline_dist, m) + 0.5 * stats.entropy(current_dist, m)
        
        return js_div
    
    
    def _calculate_categorical_psi(self, baseline_categories, baseline_probs,
                                  current_counts, current_total) -> float:
        """Calculate PSI for categorical data"""
        
        psi = 0.0
        
        for i, cat in enumerate(baseline_categories):
            expected_freq = baseline_probs[i]
            
            if cat in current_counts.index:
                actual_freq = current_counts[cat] / current_total
            else:
                actual_freq = 1e-8  # Small value for missing categories
            
            if actual_freq > 0 and expected_freq > 0:
                psi += (actual_freq - expected_freq) * np.log(actual_freq / expected_freq)
        
        return psi
    
    
    def _store_drift_result(self, model_id: str, drift_result: DriftDetectionResult):
        """Store drift detection result in database"""
        
        self.conn.execute('''
            INSERT INTO drift_detection
            (model_id, feature_name, timestamp, drift_detected, drift_score, 
             threshold_value, severity, kl_divergence, js_divergence, psi_score, 
             details, actions_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_id,
            drift_result.metric_name,
            drift_result.timestamp,
            drift_result.drift_detected,
            drift_result.drift_score,
            drift_result.threshold,
            drift_result.severity,
            drift_result.details.get('kl_divergence'),
            drift_result.details.get('js_divergence'),
            drift_result.details.get('psi_score'),
            json.dumps(drift_result.details),
            json.dumps(drift_result.recommended_actions)
        ))
        
        self.conn.commit()
    
    
    def track_model_performance(self, 
                               model_id: str,
                               predictions: np.ndarray,
                               ground_truth: np.ndarray = None,
                               inference_times: List[float] = None,
                               custom_metrics: Dict[str, float] = None) -> ModelPerformanceMetrics:
        """
        Track model performance metrics
        
        Args:
            model_id: Model identifier
            predictions: Model predictions
            ground_truth: True labels (if available)
            inference_times: List of inference times
            custom_metrics: Additional custom metrics
            
        Returns:
            ModelPerformanceMetrics object
        """
        
        metrics = ModelPerformanceMetrics(
            model_id=model_id,
            timestamp=datetime.utcnow(),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            latency_p50=0.0,
            latency_p95=0.0,
            throughput=0.0,
            error_rate=0.0,
            memory_usage=0.0,
            cpu_usage=0.0,
            custom_metrics=custom_metrics or {}
        )
        
        # Calculate performance metrics if ground truth available
        if ground_truth is not None and len(ground_truth) > 0:
            try:
                metrics.accuracy = float(accuracy_score(ground_truth, predictions))
                metrics.precision = float(precision_score(ground_truth, predictions, average='weighted'))
                metrics.recall = float(recall_score(ground_truth, predictions, average='weighted'))
                
                # F1 score
                if metrics.precision + metrics.recall > 0:
                    metrics.f1_score = 2 * (metrics.precision * metrics.recall) / (metrics.precision + metrics.recall)
                
            except Exception as e:
                self.logger.warning(f"Could not calculate performance metrics: {e}")
        
        # Calculate latency metrics
        if inference_times:
            metrics.latency_p50 = float(np.percentile(inference_times, 50))
            metrics.latency_p95 = float(np.percentile(inference_times, 95))
            metrics.throughput = 1.0 / metrics.latency_p50 if metrics.latency_p50 > 0 else 0.0
        
        # Store metrics
        self._store_performance_metrics(metrics)
        
        # Check for performance degradation
        self._check_performance_degradation(model_id, metrics)
        
        return metrics
    
    
    def _store_performance_metrics(self, metrics: ModelPerformanceMetrics):
        """Store performance metrics in database"""
        
        self.conn.execute('''
            INSERT INTO model_performance
            (model_id, timestamp, accuracy, precision_score, recall_score, f1_score,
             latency_p50, latency_p95, throughput, error_rate, memory_usage, 
             cpu_usage, custom_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.model_id,
            metrics.timestamp,
            metrics.accuracy,
            metrics.precision,
            metrics.recall,
            metrics.f1_score,
            metrics.latency_p50,
            metrics.latency_p95,
            metrics.throughput,
            metrics.error_rate,
            metrics.memory_usage,
            metrics.cpu_usage,
            json.dumps(metrics.custom_metrics)
        ))
        
        self.conn.commit()
    
    
    def _check_performance_degradation(self, model_id: str, current_metrics: ModelPerformanceMetrics):
        """Check for performance degradation"""
        
        # Get historical performance baseline
        cursor = self.conn.execute('''
            SELECT AVG(accuracy), AVG(latency_p95), AVG(f1_score)
            FROM model_performance 
            WHERE model_id = ? AND timestamp > datetime('now', '-30 days')
        ''', (model_id,))
        
        row = cursor.fetchone()
        if not row or row[0] is None:
            return  # No historical data
        
        baseline_accuracy, baseline_latency, baseline_f1 = row
        
        # Check for degradation
        degradation_alerts = []
        
        thresholds = self.config.get('performance_thresholds', {})
        
        # Accuracy degradation
        if current_metrics.accuracy > 0:
            accuracy_drop = (baseline_accuracy - current_metrics.accuracy) / baseline_accuracy
            if accuracy_drop > thresholds.get('accuracy_degradation', 0.1):
                degradation_alerts.append({
                    'type': 'accuracy_degradation',
                    'severity': 'high',
                    'message': f"Accuracy dropped by {accuracy_drop:.1%} from baseline"
                })
        
        # Latency increase
        if current_metrics.latency_p95 > 0 and baseline_latency > 0:
            latency_increase = (current_metrics.latency_p95 - baseline_latency) / baseline_latency
            if latency_increase > thresholds.get('latency_increase', 0.5):
                degradation_alerts.append({
                    'type': 'latency_increase',
                    'severity': 'medium',
                    'message': f"Latency increased by {latency_increase:.1%} from baseline"
                })
        
        # Send alerts
        for alert in degradation_alerts:
            self._send_alert(model_id, alert['type'], alert['severity'], alert['message'])
    
    
    def _process_drift_alerts(self, model_id: str, drift_results: List[DriftDetectionResult]):
        """Process and send drift alerts"""
        
        high_severity_drifts = [d for d in drift_results if d.severity in ['high', 'critical']]
        
        if high_severity_drifts:
            severity = 'critical' if any(d.severity == 'critical' for d in high_severity_drifts) else 'high'
            
            message = f"Data drift detected in {len(high_severity_drifts)} features: "
            message += ", ".join([d.metric_name for d in high_severity_drifts])
            
            self._send_alert(model_id, 'data_drift', severity, message)
    
    
    def _send_alert(self, model_id: str, alert_type: str, severity: str, message: str):
        """Send alert through configured channels"""
        
        # Store alert in database
        self.conn.execute('''
            INSERT INTO alert_history
            (model_id, alert_type, severity, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (model_id, alert_type, severity, message, datetime.utcnow()))
        
        self.conn.commit()
        
        # Send notifications
        self.logger.warning(f"🚨 ALERT [{severity.upper()}]: {message}")
        
        # Email notifications (if configured)
        if 'email' in self.alert_channels:
            self._send_email_alert(model_id, alert_type, severity, message)
        
        # Slack notifications (if configured)
        if 'slack' in self.alert_channels:
            self._send_slack_alert(model_id, alert_type, severity, message)
    
    
    def _send_email_alert(self, model_id: str, alert_type: str, severity: str, message: str):
        """Send email alert"""
        
        try:
            email_config = self.config.get('alerting', {}).get('email', {})
            
            if not email_config:
                return
            
            msg = MimeMultipart()
            msg['From'] = email_config['from']
            msg['To'] = ', '.join(email_config['to'])
            msg['Subject'] = f"[{severity.upper()}] ML Alert: {alert_type}"
            
            body = f"""
Model ID: {model_id}
Alert Type: {alert_type}
Severity: {severity}
Message: {message}
Timestamp: {datetime.utcnow().isoformat()}

Please investigate and take appropriate action.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config.get('port', 587))
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"📧 Email alert sent for {alert_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    
    def _send_slack_alert(self, model_id: str, alert_type: str, severity: str, message: str):
        """Send Slack alert"""
        
        try:
            import requests
            
            slack_config = self.config.get('alerting', {}).get('slack', {})
            
            if not slack_config or 'webhook_url' not in slack_config:
                return
            
            color_map = {
                'low': '#36a64f',      # green
                'medium': '#ff9500',   # orange
                'high': '#ff4444',     # red
                'critical': '#8b0000'  # dark red
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(severity, '#ff4444'),
                    'title': f"{alert_type.replace('_', ' ').title()} Alert",
                    'fields': [
                        {'title': 'Model ID', 'value': model_id, 'short': True},
                        {'title': 'Severity', 'value': severity.upper(), 'short': True},
                        {'title': 'Message', 'value': message, 'short': False}
                    ],
                    'footer': 'GameForge ML Monitor',
                    'ts': int(datetime.utcnow().timestamp())
                }]
            }
            
            response = requests.post(slack_config['webhook_url'], json=payload)
            response.raise_for_status()
            
            self.logger.info(f"📱 Slack alert sent for {alert_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    
    def generate_monitoring_report(self, model_id: str, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        report = {
            'model_id': model_id,
            'report_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'generated_at': end_date.isoformat(),
            'summary': {},
            'performance_trends': {},
            'drift_summary': {},
            'alerts_summary': {},
            'recommendations': []
        }
        
        # Performance trends
        cursor = self.conn.execute('''
            SELECT timestamp, accuracy, latency_p95, f1_score
            FROM model_performance
            WHERE model_id = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (model_id, start_date))
        
        performance_data = cursor.fetchall()
        
        if performance_data:
            df = pd.DataFrame(performance_data, columns=['timestamp', 'accuracy', 'latency_p95', 'f1_score'])
            
            report['performance_trends'] = {
                'avg_accuracy': float(df['accuracy'].mean()),
                'avg_latency_p95': float(df['latency_p95'].mean()),
                'avg_f1_score': float(df['f1_score'].mean()),
                'accuracy_trend': 'improving' if df['accuracy'].iloc[-1] > df['accuracy'].iloc[0] else 'degrading',
                'data_points': len(performance_data)
            }
        
        # Drift summary
        cursor = self.conn.execute('''
            SELECT feature_name, COUNT(*) as drift_count, MAX(drift_score) as max_score
            FROM drift_detection
            WHERE model_id = ? AND timestamp > ? AND drift_detected = 1
            GROUP BY feature_name
        ''', (model_id, start_date))
        
        drift_data = cursor.fetchall()
        
        report['drift_summary'] = {
            'features_with_drift': len(drift_data),
            'total_drift_events': sum(row[1] for row in drift_data),
            'features': [{'name': row[0], 'drift_count': row[1], 'max_score': row[2]} for row in drift_data]
        }
        
        # Alerts summary
        cursor = self.conn.execute('''
            SELECT alert_type, severity, COUNT(*) as count
            FROM alert_history
            WHERE model_id = ? AND timestamp > ?
            GROUP BY alert_type, severity
        ''', (model_id, start_date))
        
        alert_data = cursor.fetchall()
        
        report['alerts_summary'] = {
            'total_alerts': sum(row[2] for row in alert_data),
            'by_type_severity': [{'type': row[0], 'severity': row[1], 'count': row[2]} for row in alert_data]
        }
        
        # Generate recommendations
        if report['drift_summary']['features_with_drift'] > 0:
            report['recommendations'].append("Consider retraining model due to detected data drift")
        
        if report['alerts_summary']['total_alerts'] > 10:
            report['recommendations'].append("High alert volume - review monitoring thresholds")
        
        if report['performance_trends'].get('accuracy_trend') == 'degrading':
            report['recommendations'].append("Model performance degrading - investigate and retrain")
        
        return report


def main():
    """CLI interface for ML monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge ML Monitoring')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Establish baseline
    baseline_parser = subparsers.add_parser('baseline', help='Establish monitoring baseline')
    baseline_parser.add_argument('--model-id', required=True, help='Model ID')
    baseline_parser.add_argument('--data-file', required=True, help='Baseline data CSV file')
    baseline_parser.add_argument('--target-column', help='Target column name')
    
    # Detect drift
    drift_parser = subparsers.add_parser('drift', help='Detect data drift')
    drift_parser.add_argument('--model-id', required=True, help='Model ID')
    drift_parser.add_argument('--data-file', required=True, help='Current data CSV file')
    
    # Generate report
    report_parser = subparsers.add_parser('report', help='Generate monitoring report')
    report_parser.add_argument('--model-id', required=True, help='Model ID')
    report_parser.add_argument('--days', type=int, default=7, help='Report period in days')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize monitor
    monitor = MLMonitor()
    
    try:
        if args.command == 'baseline':
            data = pd.read_csv(args.data_file)
            success = monitor.establish_baseline(
                model_id=args.model_id,
                baseline_data=data,
                target_column=args.target_column
            )
            
            if success:
                print(f"✅ Baseline established for model {args.model_id}")
            else:
                print(f"❌ Failed to establish baseline")
        
        elif args.command == 'drift':
            data = pd.read_csv(args.data_file)
            drift_results = monitor.detect_data_drift(
                model_id=args.model_id,
                current_data=data
            )
            
            print(f"\n🔍 Drift Detection Results:")
            print(f"   Checked {len(data.columns)} features")
            print(f"   Found {len(drift_results)} issues")
            
            for result in drift_results:
                print(f"   {result.metric_name}: {result.severity} drift (score: {result.drift_score:.3f})")
        
        elif args.command == 'report':
            report = monitor.generate_monitoring_report(
                model_id=args.model_id,
                days=args.days
            )
            
            print(f"\n📊 Monitoring Report for {args.model_id}")
            print(f"   Period: {report['report_period']}")
            print(f"   Performance: {report['performance_trends']}")
            print(f"   Drift: {report['drift_summary']}")
            print(f"   Alerts: {report['alerts_summary']}")
            print(f"   Recommendations: {report['recommendations']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())