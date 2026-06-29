import os
import json
import logging
import time
import httpx
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlertManager:
    """
    Handles critical system alerts via Slack and Email.
    Includes simple deduplication to prevent alert storms.
    """
    def __init__(self, slack_webhook_url: str = None, alert_email: str = None):
        self.slack_webhook_url = slack_webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
        self.alert_email = alert_email or os.environ.get("ALERT_EMAIL")
        
        # Deduplication tracking: map of "alert_title" -> timestamp of last sent
        self._sent_alerts = {}
        # Cooldown in seconds (1 hour default)
        self.cooldown_seconds = 3600

    def alert(self, title: str, message: str, severity: str = "warning") -> bool:
        """
        Send an alert. Severity can be 'info', 'warning', or 'critical'.
        """
        now = time.time()
        dedup_key = f"{severity}:{title}"
        
        # Deduplication check
        if dedup_key in self._sent_alerts:
            last_sent = self._sent_alerts[dedup_key]
            if now - last_sent < self.cooldown_seconds:
                logger.debug(f"Alert '{title}' suppressed due to cooldown.")
                return False
                
        self._sent_alerts[dedup_key] = now
        logger.warning(f"ALERT [{severity.upper()}]: {title} - {message}")

        success = True
        if self.slack_webhook_url:
            if not self._send_slack(title, message, severity):
                success = False
                
        if self.alert_email:
            # We would typically use SendGrid here
            # Since this is internal alerting, we might just log it if no mailer configured
            logger.info(f"Would send email to {self.alert_email} with title: {title}")
            
        return success

    def _send_slack(self, title: str, message: str, severity: str) -> bool:
        colors = {
            "info": "#36a64f",      # Green
            "warning": "#ffae42",   # Yellow/Orange
            "critical": "#ff0000"   # Red
        }
        color = colors.get(severity.lower(), colors["info"])
        
        payload = {
            "attachments": [
                {
                    "fallback": f"{title} - {message}",
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "AutoScan System Alerts",
                    "ts": int(time.time())
                }
            ]
        }
        
        try:
            resp = httpx.post(self.slack_webhook_url, json=payload, timeout=10.0)
            if resp.status_code >= 400:
                logger.error(f"Failed to send Slack alert: {resp.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")
            return False

# Global instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
