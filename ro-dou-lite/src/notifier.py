"""Email notification module for search results.

This module handles formatting and sending email notifications
for DOU search results. Simplified for Raspberry Pi deployment.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotifierError(Exception):
    """Raised when notification fails."""
    pass


class EmailNotifier:
    """Email notifier for DOU search results.

    Formats search results as HTML email and sends via SMTP.
    Optimized for simple, reliable delivery (Gmail, etc.).

    Example:
        >>> notifier = EmailNotifier(
        ...     smtp_host="smtp.gmail.com",
        ...     smtp_port=587,
        ...     from_email="alerts@example.com",
        ...     password="app_password"
        ... )
        >>> notifier.send(
        ...     to_emails=["user@example.com"],
        ...     subject="DOU Alerts",
        ...     results=results
        ... )
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        password: Optional[str] = None,
        username: Optional[str] = None,
        use_tls: bool = True
    ):
        """Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (usually 587 for TLS, 465 for SSL)
            from_email: Sender email address
            password: SMTP password (optional if no auth needed)
            username: SMTP username (default: same as from_email)
            use_tls: Use TLS encryption (default: True)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.password = password
        self.username = username or from_email
        self.use_tls = use_tls

    def send(
        self,
        to_emails: List[str],
        subject: str,
        results: Dict[str, List[Dict[str, Any]]],
        custom_header: Optional[str] = None,
        custom_footer: Optional[str] = None
    ) -> None:
        """Send email notification with search results.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            results: Search results grouped by term
            custom_header: Optional custom header text
            custom_footer: Optional custom footer text

        Raises:
            NotifierError: If sending fails
        """
        if not to_emails:
            logger.warning("No recipients specified, skipping notification")
            return

        if not results or all(not v for v in results.values()):
            logger.info("No results to send, skipping notification")
            return

        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = ', '.join(to_emails)
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

        # Generate HTML body
        html_body = self._format_html(results, custom_header, custom_footer)
        text_body = self._format_text(results)

        # Attach both plain text and HTML versions
        part_text = MIMEText(text_body, 'plain', 'utf-8')
        part_html = MIMEText(html_body, 'html', 'utf-8')

        msg.attach(part_text)
        msg.attach(part_html)

        # Send email
        try:
            self._send_smtp(msg, to_emails)
            logger.info(f"Sent notification to {len(to_emails)} recipients")

        except Exception as e:
            raise NotifierError(f"Failed to send email: {e}")

    def _send_smtp(self, msg: MIMEMultipart, to_emails: List[str]) -> None:
        """Send email via SMTP.

        Args:
            msg: Email message
            to_emails: Recipient addresses

        Raises:
            NotifierError: If SMTP operation fails
        """
        try:
            # Create SMTP connection
            if self.use_tls:
                smtp = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
            else:
                smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)

            # Authenticate if credentials provided
            if self.password:
                smtp.login(self.username, self.password)

            # Send message
            smtp.sendmail(self.from_email, to_emails, msg.as_string())
            smtp.quit()

        except smtplib.SMTPException as e:
            raise NotifierError(f"SMTP error: {e}")
        except Exception as e:
            raise NotifierError(f"Failed to send via SMTP: {e}")

    def _format_html(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        custom_header: Optional[str],
        custom_footer: Optional[str]
    ) -> str:
        """Format search results as HTML.

        Args:
            results: Search results grouped by term
            custom_header: Optional header text
            custom_footer: Optional footer text

        Returns:
            HTML formatted email body
        """
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="UTF-8">',
            '<style>',
            'body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }',
            'h1 { color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }',
            'h2 { color: #0066cc; margin-top: 30px; }',
            'h3 { color: #333; font-size: 1.1em; margin-top: 20px; }',
            '.article { background: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #0066cc; }',
            '.meta { color: #666; font-size: 0.9em; margin-top: 5px; }',
            '.snippet { margin-top: 10px; }',
            'mark { background-color: #ffff00; font-weight: bold; }',
            '.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc; color: #666; font-size: 0.9em; }',
            '</style>',
            '</head>',
            '<body>',
        ]

        # Header
        html_parts.append('<h1>Ro-DOU Alerts - Diário Oficial da União</h1>')

        if custom_header:
            html_parts.append(f'<div class="header">{custom_header}</div>')

        # Results by term
        for term, articles in results.items():
            if not articles:
                continue

            html_parts.append(f'<h2>Termo de busca: "{term}" ({len(articles)} resultados)</h2>')

            for article in articles:
                html_parts.append('<div class="article">')

                # Title
                titulo = article.get('titulo', 'Sem título')
                html_parts.append(f'<h3>{titulo}</h3>')

                # Metadata
                pubdate = article.get('pubdate', '')
                section = article.get('pubname', '')
                category = article.get('artcategory', '')

                html_parts.append('<div class="meta">')
                html_parts.append(f'<strong>Data:</strong> {pubdate} | ')
                html_parts.append(f'<strong>Seção:</strong> {section} | ')
                html_parts.append(f'<strong>Órgão:</strong> {category}')
                html_parts.append('</div>')

                # Snippet (with highlights)
                snippet = article.get('snippet', article.get('texto', ''))[:500]
                if snippet:
                    html_parts.append(f'<div class="snippet">{snippet}...</div>')

                html_parts.append('</div>')  # article

        # Footer
        if custom_footer:
            html_parts.append(f'<div class="footer">{custom_footer}</div>')
        else:
            html_parts.append('<div class="footer">')
            html_parts.append(f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}<br>')
            html_parts.append('Ro-DOU Lite - Raspberry Pi Edition')
            html_parts.append('</div>')

        html_parts.extend(['</body>', '</html>'])

        return '\n'.join(html_parts)

    def _format_text(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format search results as plain text.

        Args:
            results: Search results grouped by term

        Returns:
            Plain text formatted email body
        """
        lines = [
            'RO-DOU ALERTS - DIÁRIO OFICIAL DA UNIÃO',
            '=' * 60,
            ''
        ]

        for term, articles in results.items():
            if not articles:
                continue

            lines.append(f'TERMO DE BUSCA: "{term}" ({len(articles)} resultados)')
            lines.append('-' * 60)
            lines.append('')

            for article in articles:
                titulo = article.get('titulo', 'Sem título')
                pubdate = article.get('pubdate', '')
                section = article.get('pubname', '')
                category = article.get('artcategory', '')

                lines.append(titulo)
                lines.append(f'Data: {pubdate} | Seção: {section}')
                lines.append(f'Órgão: {category}')
                lines.append('')

                # Text preview (no HTML tags in plain text)
                texto = article.get('texto', '')[:300]
                if texto:
                    # Remove HTML tags
                    import re
                    texto_clean = re.sub(r'<[^>]+>', '', texto)
                    lines.append(texto_clean + '...')

                lines.append('')

        lines.append('=' * 60)
        lines.append(f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}')
        lines.append('Ro-DOU Lite - Raspberry Pi Edition')

        return '\n'.join(lines)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "EmailNotifier":
        """Create EmailNotifier from configuration dictionary.

        Args:
            config: Email configuration from YAML

        Returns:
            EmailNotifier instance
        """
        return cls(
            smtp_host=config['smtp_host'],
            smtp_port=config['smtp_port'],
            from_email=config['from'],
            password=config.get('password'),
            username=config.get('username'),
            use_tls=config.get('use_tls', True)
        )
