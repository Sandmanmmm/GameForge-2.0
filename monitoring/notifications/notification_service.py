#!/usr/bin/env python3
"""
GameForge Notification Service
Handles alert notifications to various channels (Slack, Email, PagerDuty, etc.)
"""

import asyncio
import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional

import aiohttp
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import uvicorn

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

# Prometheus metrics
notification_counter = Counter('notifications_sent_total', 'Total notifications sent', ['channel', 'status'])
notification_duration = Histogram('notification_duration_seconds', 'Time spent sending notifications', ['channel'])

class Alert(BaseModel):
    """Alert model from AlertManager"""
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: str

class AlertManagerWebhook(BaseModel):
    """AlertManager webhook payload"""
    receiver: str
    status: str
    alerts: List[Alert]
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    version: str
    groupKey: str
    truncatedAlerts: int = 0

class NotificationService:
    """Main notification service class"""
    
    def __init__(self):
        self.app = FastAPI(title="GameForge Notification Service", version="1.0.0")
        self.setup_routes()
        
        # Configuration
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
        self.pagerduty_key = os.getenv('PAGERDUTY_ROUTING_KEY')
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM')
        
        # Service configuration
        self.notification_timeout = int(os.getenv('NOTIFICATION_TIMEOUT', '30'))
        self.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
        
        logger.info("GameForge Notification Service initialized")

    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "service": "gameforge-notification-service"}
        
        @self.app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint"""
            return generate_latest()
        
        @self.app.post("/webhook/alertmanager")
        async def alertmanager_webhook(payload: AlertManagerWebhook, background_tasks: BackgroundTasks):
            """Receive alerts from AlertManager"""
            try:
                logger.info("Received AlertManager webhook", alerts_count=len(payload.alerts))
                
                # Process alerts in background
                background_tasks.add_task(self.process_alerts, payload)
                
                return {"status": "accepted", "alerts_received": len(payload.alerts)}
            
            except Exception as e:
                logger.error("Error processing AlertManager webhook", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/test/{channel}")
        async def test_notification(channel: str, background_tasks: BackgroundTasks):
            """Test notification channels"""
            test_alert = Alert(
                status="firing",
                labels={"alertname": "TestAlert", "severity": "info", "service": "test"},
                annotations={"summary": "Test notification", "description": "This is a test notification"},
                startsAt=datetime.utcnow().isoformat(),
                fingerprint="test-fingerprint"
            )
            
            test_payload = AlertManagerWebhook(
                receiver="test",
                status="firing",
                alerts=[test_alert],
                groupLabels={"alertname": "TestAlert"},
                commonLabels={"service": "test"},
                commonAnnotations={"summary": "Test notification"},
                externalURL="http://alertmanager:9093",
                version="4",
                groupKey="test-group"
            )
            
            if channel == "slack":
                background_tasks.add_task(self.send_slack_notification, test_payload)
            elif channel == "email":
                background_tasks.add_task(self.send_email_notification, test_payload)
            elif channel == "pagerduty":
                background_tasks.add_task(self.send_pagerduty_notification, test_payload)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
            
            return {"status": "test_sent", "channel": channel}

    async def process_alerts(self, payload: AlertManagerWebhook):
        """Process alerts and route to appropriate channels"""
        try:
            logger.info("Processing alerts", receiver=payload.receiver, alert_count=len(payload.alerts))
            
            # Determine notification channels based on receiver and severity
            channels = self.determine_channels(payload)
            
            # Send notifications to all determined channels
            tasks = []
            for channel in channels:
                if channel == "slack":
                    tasks.append(self.send_slack_notification(payload))
                elif channel == "email":
                    tasks.append(self.send_email_notification(payload))
                elif channel == "pagerduty":
                    tasks.append(self.send_pagerduty_notification(payload))
                elif channel == "discord":
                    tasks.append(self.send_discord_notification(payload))
                elif channel == "teams":
                    tasks.append(self.send_teams_notification(payload))
            
            # Execute all notifications concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error("Error processing alerts", error=str(e))

    def determine_channels(self, payload: AlertManagerWebhook) -> List[str]:
        """Determine which notification channels to use based on alert content"""
        channels = []
        
        # Check severity
        severity = payload.commonLabels.get('severity', 'info')
        service = payload.commonLabels.get('service', '')
        
        # Always send to Slack for GameForge alerts
        if self.slack_webhook:
            channels.append("slack")
        
        # Critical alerts also go to PagerDuty
        if severity == "critical" and self.pagerduty_key:
            channels.append("pagerduty")
        
        # High severity or infrastructure alerts go to email
        if severity in ["critical", "warning"] and self.smtp_host:
            channels.append("email")
        
        # GPU/ML alerts go to specialized channels
        if "gpu" in service.lower() or "mlflow" in service.lower():
            if self.discord_webhook:
                channels.append("discord")
        
        return channels

    async def send_slack_notification(self, payload: AlertManagerWebhook):
        """Send notification to Slack"""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured")
            return
        
        with notification_duration.labels(channel="slack").time():
            try:
                # Format Slack message
                message = self.format_slack_message(payload)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.slack_webhook,
                        json=message,
                        timeout=aiohttp.ClientTimeout(total=self.notification_timeout)
                    ) as response:
                        if response.status == 200:
                            notification_counter.labels(channel="slack", status="success").inc()
                            logger.info("Slack notification sent successfully")
                        else:
                            notification_counter.labels(channel="slack", status="error").inc()
                            logger.error("Failed to send Slack notification", status=response.status)
            
            except Exception as e:
                notification_counter.labels(channel="slack", status="error").inc()
                logger.error("Error sending Slack notification", error=str(e))

    async def send_email_notification(self, payload: AlertManagerWebhook):
        """Send notification via email"""
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.email_from]):
            logger.warning("Email configuration incomplete")
            return
        
        with notification_duration.labels(channel="email").time():
            try:
                # Format email message
                subject, body = self.format_email_message(payload)
                
                # Determine recipients based on alert severity
                recipients = self.get_email_recipients(payload)
                
                # Send email
                msg = MimeMultipart()
                msg['From'] = self.email_from
                msg['To'] = ", ".join(recipients)
                msg['Subject'] = subject
                msg.attach(MimeText(body, 'plain'))
                
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                
                notification_counter.labels(channel="email", status="success").inc()
                logger.info("Email notification sent successfully", recipients=recipients)
            
            except Exception as e:
                notification_counter.labels(channel="email", status="error").inc()
                logger.error("Error sending email notification", error=str(e))

    async def send_pagerduty_notification(self, payload: AlertManagerWebhook):
        """Send notification to PagerDuty"""
        if not self.pagerduty_key:
            logger.warning("PagerDuty routing key not configured")
            return
        
        with notification_duration.labels(channel="pagerduty").time():
            try:
                # Format PagerDuty event
                event = self.format_pagerduty_event(payload)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://events.pagerduty.com/v2/enqueue",
                        json=event,
                        timeout=aiohttp.ClientTimeout(total=self.notification_timeout)
                    ) as response:
                        if response.status == 202:
                            notification_counter.labels(channel="pagerduty", status="success").inc()
                            logger.info("PagerDuty notification sent successfully")
                        else:
                            notification_counter.labels(channel="pagerduty", status="error").inc()
                            logger.error("Failed to send PagerDuty notification", status=response.status)
            
            except Exception as e:
                notification_counter.labels(channel="pagerduty", status="error").inc()
                logger.error("Error sending PagerDuty notification", error=str(e))

    async def send_discord_notification(self, payload: AlertManagerWebhook):
        """Send notification to Discord"""
        if not self.discord_webhook:
            logger.warning("Discord webhook not configured")
            return
        
        with notification_duration.labels(channel="discord").time():
            try:
                # Format Discord message
                message = self.format_discord_message(payload)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.discord_webhook,
                        json=message,
                        timeout=aiohttp.ClientTimeout(total=self.notification_timeout)
                    ) as response:
                        if response.status in [200, 204]:
                            notification_counter.labels(channel="discord", status="success").inc()
                            logger.info("Discord notification sent successfully")
                        else:
                            notification_counter.labels(channel="discord", status="error").inc()
                            logger.error("Failed to send Discord notification", status=response.status)
            
            except Exception as e:
                notification_counter.labels(channel="discord", status="error").inc()
                logger.error("Error sending Discord notification", error=str(e))

    async def send_teams_notification(self, payload: AlertManagerWebhook):
        """Send notification to Microsoft Teams"""
        if not self.teams_webhook:
            logger.warning("Teams webhook not configured")
            return
        
        with notification_duration.labels(channel="teams").time():
            try:
                # Format Teams message
                message = self.format_teams_message(payload)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.teams_webhook,
                        json=message,
                        timeout=aiohttp.ClientTimeout(total=self.notification_timeout)
                    ) as response:
                        if response.status == 200:
                            notification_counter.labels(channel="teams", status="success").inc()
                            logger.info("Teams notification sent successfully")
                        else:
                            notification_counter.labels(channel="teams", status="error").inc()
                            logger.error("Failed to send Teams notification", status=response.status)
            
            except Exception as e:
                notification_counter.labels(channel="teams", status="error").inc()
                logger.error("Error sending Teams notification", error=str(e))

    def format_slack_message(self, payload: AlertManagerWebhook) -> Dict:
        """Format message for Slack"""
        color = "danger" if payload.status == "firing" else "good"
        emoji = "🚨" if payload.status == "firing" else "✅"
        
        fields = []
        for alert in payload.alerts[:5]:  # Limit to 5 alerts
            fields.append({
                "title": alert.labels.get('alertname', 'Unknown Alert'),
                "value": f"*Service:* {alert.labels.get('service', 'N/A')}\n"
                        f"*Summary:* {alert.annotations.get('summary', 'N/A')}\n"
                        f"*Severity:* {alert.labels.get('severity', 'N/A')}",
                "short": False
            })
        
        return {
            "attachments": [{
                "color": color,
                "title": f"{emoji} GameForge Alert: {payload.groupLabels.get('alertname', 'Unknown')}",
                "text": f"Status: {payload.status.upper()}",
                "fields": fields,
                "footer": "GameForge AlertManager",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }

    def format_email_message(self, payload: AlertManagerWebhook) -> tuple:
        """Format message for email"""
        subject = f"[GameForge] {payload.groupLabels.get('alertname', 'Alert')} - {payload.status.upper()}"
        
        body = f"""GameForge Production Alert

Status: {payload.status.upper()}
Receiver: {payload.receiver}
Group: {payload.groupKey}

Alerts:
"""
        
        for alert in payload.alerts:
            body += f"""
---
Alert: {alert.labels.get('alertname', 'Unknown')}
Service: {alert.labels.get('service', 'N/A')}
Severity: {alert.labels.get('severity', 'N/A')}
Summary: {alert.annotations.get('summary', 'N/A')}
Description: {alert.annotations.get('description', 'N/A')}
Started: {alert.startsAt}
Instance: {alert.labels.get('instance', 'N/A')}
"""
        
        body += f"""
---
Dashboard: http://grafana.gameforge.local:3000
AlertManager: http://alertmanager.gameforge.local:9093
"""
        
        return subject, body

    def format_pagerduty_event(self, payload: AlertManagerWebhook) -> Dict:
        """Format event for PagerDuty"""
        severity = payload.commonLabels.get('severity', 'info')
        pagerduty_severity = {
            'critical': 'critical',
            'warning': 'warning',
            'info': 'info'
        }.get(severity, 'info')
        
        event_action = "trigger" if payload.status == "firing" else "resolve"
        
        return {
            "routing_key": self.pagerduty_key,
            "event_action": event_action,
            "dedup_key": payload.groupKey,
            "payload": {
                "summary": f"GameForge: {payload.groupLabels.get('alertname', 'Alert')}",
                "severity": pagerduty_severity,
                "source": payload.commonLabels.get('instance', 'gameforge-production'),
                "component": payload.commonLabels.get('service', 'gameforge'),
                "group": "gameforge-production",
                "class": "production-alert",
                "custom_details": {
                    "alerts_count": len(payload.alerts),
                    "receiver": payload.receiver,
                    "dashboard": "http://grafana.gameforge.local:3000",
                    "runbook": f"https://docs.gameforge.local/runbooks/{payload.groupLabels.get('alertname', 'default')}"
                }
            },
            "links": [
                {
                    "href": "http://grafana.gameforge.local:3000",
                    "text": "GameForge Dashboard"
                },
                {
                    "href": "http://alertmanager.gameforge.local:9093",
                    "text": "AlertManager"
                }
            ]
        }

    def format_discord_message(self, payload: AlertManagerWebhook) -> Dict:
        """Format message for Discord"""
        color = 0xff0000 if payload.status == "firing" else 0x00ff00
        
        embeds = []
        for alert in payload.alerts[:10]:  # Discord limit
            embeds.append({
                "title": f"{alert.labels.get('alertname', 'Unknown Alert')}",
                "description": alert.annotations.get('summary', 'No summary available'),
                "color": color,
                "fields": [
                    {"name": "Service", "value": alert.labels.get('service', 'N/A'), "inline": True},
                    {"name": "Severity", "value": alert.labels.get('severity', 'N/A'), "inline": True},
                    {"name": "Instance", "value": alert.labels.get('instance', 'N/A'), "inline": True}
                ],
                "timestamp": alert.startsAt
            })
        
        return {
            "content": f"**GameForge Alert**: {payload.status.upper()}",
            "embeds": embeds
        }

    def format_teams_message(self, payload: AlertManagerWebhook) -> Dict:
        """Format message for Microsoft Teams"""
        color = "ff0000" if payload.status == "firing" else "00ff00"
        
        facts = []
        for alert in payload.alerts[:5]:
            facts.extend([
                {"name": "Alert", "value": alert.labels.get('alertname', 'Unknown')},
                {"name": "Service", "value": alert.labels.get('service', 'N/A')},
                {"name": "Severity", "value": alert.labels.get('severity', 'N/A')},
                {"name": "Summary", "value": alert.annotations.get('summary', 'N/A')}
            ])
        
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": f"GameForge Alert: {payload.groupLabels.get('alertname', 'Unknown')}",
            "sections": [{
                "activityTitle": f"GameForge Alert: {payload.status.upper()}",
                "activitySubtitle": f"Receiver: {payload.receiver}",
                "facts": facts,
                "markdown": True
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View Dashboard",
                "targets": [{
                    "os": "default",
                    "uri": "http://grafana.gameforge.local:3000"
                }]
            }]
        }

    def get_email_recipients(self, payload: AlertManagerWebhook) -> List[str]:
        """Get email recipients based on alert severity and service"""
        recipients = []
        
        severity = payload.commonLabels.get('severity', 'info')
        service = payload.commonLabels.get('service', '')
        
        # Default recipients
        default_email = os.getenv('ALERT_EMAIL_DEFAULT')
        if default_email:
            recipients.append(default_email)
        
        # Critical alerts
        if severity == "critical":
            critical_email = os.getenv('ALERT_EMAIL_CRITICAL')
            if critical_email:
                recipients.append(critical_email)
        
        # Security alerts
        if 'security' in service.lower() or 'vault' in service.lower():
            security_email = os.getenv('SECURITY_EMAIL')
            if security_email:
                recipients.append(security_email)
        
        # Infrastructure alerts
        if service in ['postgres', 'redis', 'elasticsearch']:
            infra_email = os.getenv('INFRASTRUCTURE_EMAIL')
            if infra_email:
                recipients.append(infra_email)
        
        return list(set(recipients))  # Remove duplicates

# Create the service instance
service = NotificationService()
app = service.app

if __name__ == "__main__":
    uvicorn.run(
        "notification_service:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )
