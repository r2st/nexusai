"""Email notification integration."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.services.notifications.models import (
    EmailConfig,
    NotificationMessage,
    NotificationResult,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send notifications via email using SMTP."""

    def __init__(self, config: EmailConfig):
        self.config = config

    async def send(
        self,
        message: NotificationMessage,
        recipients: list[str],
    ) -> NotificationResult:
        """Send a notification email.

        Args:
            message: The notification message to send
            recipients: List of email addresses

        Returns:
            NotificationResult indicating success or failure
        """
        if not recipients:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error="No recipients provided",
            )

        try:
            email_content = self._build_email(message, recipients)

            # Send synchronously (could be made async with aiosmtplib)
            await self._send_smtp(email_content, recipients)

            return NotificationResult(
                success=True,
                channel=NotificationChannel.EMAIL,
                message_id=None,
            )

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=str(e),
            )

    def _build_email(
        self,
        message: NotificationMessage,
        recipients: list[str],
    ) -> MIMEMultipart:
        """Build email message."""
        email = MIMEMultipart("alternative")

        email["Subject"] = self._get_subject(message)
        email["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        email["To"] = ", ".join(recipients)

        if self.config.reply_to:
            email["Reply-To"] = self.config.reply_to

        # Build plain text version
        text_content = self._build_text_content(message)
        text_part = MIMEText(text_content, "plain", "utf-8")
        email.attach(text_part)

        # Build HTML version
        html_content = self._build_html_content(message)
        html_part = MIMEText(html_content, "html", "utf-8")
        email.attach(html_part)

        return email

    def _get_subject(self, message: NotificationMessage) -> str:
        """Generate email subject with priority prefix."""
        prefix = ""
        if message.priority == NotificationPriority.CRITICAL:
            prefix = "[CRITICAL] "
        elif message.priority == NotificationPriority.HIGH:
            prefix = "[HIGH] "

        return f"{prefix}NexusAI: {message.title}"

    def _build_text_content(self, message: NotificationMessage) -> str:
        """Build plain text email content."""
        lines = [
            message.title,
            "=" * len(message.title),
            "",
            message.body,
            "",
        ]

        if message.data:
            lines.append("Details:")
            lines.append("-" * 20)
            for key, value in message.data.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        if message.actions:
            lines.append("Actions:")
            for action in message.actions:
                lines.append(f"  - {action.get('text', 'Link')}: {action.get('url', '#')}")
            lines.append("")

        lines.extend([
            "-" * 40,
            f"Source: {message.source}",
            f"Priority: {message.priority.value}",
            f"Type: {message.type.value}",
        ])

        if message.footer:
            lines.append(message.footer)

        return "\n".join(lines)

    def _build_html_content(self, message: NotificationMessage) -> str:
        """Build HTML email content."""
        color = self._get_color(message)

        # Build data table rows
        data_rows = ""
        if message.data:
            data_rows = "".join([
                f"<tr><td style='padding:8px;border-bottom:1px solid #eee;font-weight:bold;'>{k}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;'>{v}</td></tr>"
                for k, v in message.data.items()
            ])

        # Build action buttons
        action_buttons = ""
        if message.actions:
            action_buttons = "".join([
                f"<a href='{action.get('url', '#')}' style='display:inline-block;padding:10px 20px;"
                f"background-color:{color};color:white;text-decoration:none;border-radius:4px;margin-right:10px;'>"
                f"{action.get('text', 'Action')}</a>"
                for action in message.actions
            ])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;">
    <div style="border-left:4px solid {color};padding-left:20px;">
        <h1 style="color:{color};margin-bottom:10px;">{message.title}</h1>
        <p style="font-size:16px;margin-bottom:20px;">{message.body}</p>

        {f'''
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            {data_rows}
        </table>
        ''' if data_rows else ''}

        {f'''
        <div style="margin-bottom:20px;">
            {action_buttons}
        </div>
        ''' if action_buttons else ''}

        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">

        <p style="font-size:12px;color:#888;">
            Source: {message.source} | Priority: {message.priority.value} | Type: {message.type.value}
        </p>

        {f'<p style="font-size:12px;color:#888;">{message.footer}</p>' if message.footer else ''}
    </div>

    <p style="font-size:11px;color:#aaa;margin-top:20px;text-align:center;">
        This is an automated message from NexusAI. Do not reply directly to this email.
    </p>
</body>
</html>
"""
        return html

    def _get_color(self, message: NotificationMessage) -> str:
        """Get color based on message type and priority."""
        if message.color:
            return message.color

        if message.priority == NotificationPriority.CRITICAL:
            return "#FF0000"
        elif message.priority == NotificationPriority.HIGH:
            return "#FFA500"

        type_colors = {
            NotificationType.QUALITY_GATE_PASSED: "#36A64F",
            NotificationType.QUALITY_GATE_FAILED: "#FF0000",
            NotificationType.SECURITY_ISSUE_FOUND: "#FF0000",
            NotificationType.CRITICAL_ISSUE_FOUND: "#FF0000",
            NotificationType.ANALYSIS_COMPLETE: "#36A64F",
            NotificationType.DORA_METRICS_UPDATE: "#0076D7",
            NotificationType.WEEKLY_SUMMARY: "#0076D7",
        }

        return type_colors.get(message.type, "#0076D7")

    async def _send_smtp(self, email: MIMEMultipart, recipients: list[str]) -> None:
        """Send email via SMTP."""
        # Note: For production, use aiosmtplib for async
        import asyncio

        def send_sync():
            if self.config.use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)

            try:
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)

                server.sendmail(
                    self.config.from_email,
                    recipients,
                    email.as_string(),
                )
            finally:
                server.quit()

        # Run sync in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_sync)


async def send_email_notification(
    config: EmailConfig,
    message: NotificationMessage,
    recipients: list[str],
) -> NotificationResult:
    """Convenience function to send a single email.

    Args:
        config: Email configuration
        message: Message to send
        recipients: Email addresses

    Returns:
        NotificationResult
    """
    notifier = EmailNotifier(config)
    return await notifier.send(message, recipients)
