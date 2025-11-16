"""Tests for email notifier."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.notifier import EmailNotifier, NotifierError


@pytest.fixture
def email_config():
    """Return sample email configuration."""
    return {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'from': 'alerts@example.com',
        'password': 'app_password',
        'use_tls': True
    }


@pytest.fixture
def sample_results():
    """Return sample search results."""
    return {
        'LGPD': [
            {
                'id': 1,
                'titulo': 'Portaria sobre LGPD',
                'pubdate': '2025-01-15',
                'pubname': 'DO1',
                'artcategory': 'Ministério da Gestão',
                'texto': 'Estabelece diretrizes sobre <mark>LGPD</mark>',
                'snippet': 'Estabelece diretrizes sobre <mark>LGPD</mark>...'
            },
            {
                'id': 2,
                'titulo': 'Decreto LGPD',
                'pubdate': '2025-01-15',
                'pubname': 'DO2',
                'artcategory': 'Ministério da Economia',
                'texto': 'Regulamenta <mark>LGPD</mark>',
                'snippet': 'Regulamenta <mark>LGPD</mark>...'
            }
        ],
        'dados abertos': [
            {
                'id': 3,
                'titulo': 'Política de dados abertos',
                'pubdate': '2025-01-15',
                'pubname': 'DO1',
                'artcategory': 'Ministério da Gestão',
                'texto': 'Estabelece política de <mark>dados abertos</mark>',
                'snippet': 'Estabelece política de <mark>dados abertos</mark>...'
            }
        ]
    }


class TestEmailNotifier:
    """Test EmailNotifier class."""

    def test_init(self, email_config):
        """Test notifier initialization."""
        notifier = EmailNotifier(
            smtp_host=email_config['smtp_host'],
            smtp_port=email_config['smtp_port'],
            from_email=email_config['from'],
            password=email_config['password']
        )

        assert notifier.smtp_host == 'smtp.gmail.com'
        assert notifier.smtp_port == 587
        assert notifier.from_email == 'alerts@example.com'
        assert notifier.use_tls is True

    def test_from_config(self, email_config):
        """Test creating notifier from config dict."""
        notifier = EmailNotifier.from_config(email_config)

        assert notifier.smtp_host == email_config['smtp_host']
        assert notifier.from_email == email_config['from']

    @patch('smtplib.SMTP')
    def test_send_success(self, mock_smtp, email_config, sample_results):
        """Test successful email sending."""
        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        notifier = EmailNotifier.from_config(email_config)

        notifier.send(
            to_emails=['user@example.com'],
            subject='Test Alert',
            results=sample_results
        )

        # Verify SMTP was called
        mock_smtp.assert_called_once_with('smtp.gmail.com', 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    def test_send_no_recipients(self, email_config, sample_results, caplog):
        """Test send with no recipients."""
        notifier = EmailNotifier.from_config(email_config)

        # Should not raise, just log warning
        notifier.send(
            to_emails=[],
            subject='Test',
            results=sample_results
        )

        assert 'No recipients' in caplog.text

    def test_send_empty_results(self, email_config, caplog):
        """Test send with empty results."""
        notifier = EmailNotifier.from_config(email_config)

        notifier.send(
            to_emails=['user@example.com'],
            subject='Test',
            results={}
        )

        assert 'No results' in caplog.text

    @patch('smtplib.SMTP')
    def test_send_smtp_error(self, mock_smtp, email_config, sample_results):
        """Test handling SMTP errors."""
        import smtplib

        mock_smtp.side_effect = smtplib.SMTPException("SMTP error")

        notifier = EmailNotifier.from_config(email_config)

        with pytest.raises(NotifierError, match="SMTP error"):
            notifier.send(
                to_emails=['user@example.com'],
                subject='Test',
                results=sample_results
            )

    def test_format_html_contains_results(self, email_config, sample_results):
        """Test HTML formatting includes all results."""
        notifier = EmailNotifier.from_config(email_config)

        html = notifier._format_html(sample_results, None, None)

        # Check structure
        assert '<!DOCTYPE html>' in html
        assert '<html>' in html
        assert '</html>' in html

        # Check content
        assert 'LGPD' in html
        assert 'dados abertos' in html
        assert 'Portaria sobre LGPD' in html
        assert 'Política de dados abertos' in html

        # Check highlights
        assert '<mark>' in html

    def test_format_html_with_custom_header(self, email_config, sample_results):
        """Test HTML formatting with custom header."""
        notifier = EmailNotifier.from_config(email_config)

        header = '<p>Custom header text</p>'
        html = notifier._format_html(sample_results, header, None)

        assert header in html

    def test_format_html_with_custom_footer(self, email_config, sample_results):
        """Test HTML formatting with custom footer."""
        notifier = EmailNotifier.from_config(email_config)

        footer = '<p>Custom footer text</p>'
        html = notifier._format_html(sample_results, None, footer)

        assert footer in html

    def test_format_text_contains_results(self, email_config, sample_results):
        """Test plain text formatting includes results."""
        notifier = EmailNotifier.from_config(email_config)

        text = notifier._format_text(sample_results)

        # Check content
        assert 'LGPD' in text
        assert 'dados abertos' in text
        assert 'Portaria sobre LGPD' in text
        assert 'RO-DOU ALERTS' in text

    def test_format_text_no_html_tags(self, email_config, sample_results):
        """Test plain text formatting removes HTML tags."""
        notifier = EmailNotifier.from_config(email_config)

        text = notifier._format_text(sample_results)

        # Should not contain HTML tags
        assert '<mark>' not in text
        assert '</mark>' not in text
        assert '<div>' not in text

    @patch('smtplib.SMTP')
    def test_send_multiple_recipients(self, mock_smtp, email_config, sample_results):
        """Test sending to multiple recipients."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        notifier = EmailNotifier.from_config(email_config)

        recipients = ['user1@example.com', 'user2@example.com']
        notifier.send(
            to_emails=recipients,
            subject='Test',
            results=sample_results
        )

        # Verify sendmail called with all recipients
        args, kwargs = mock_server.sendmail.call_args
        assert args[1] == recipients

    @patch('smtplib.SMTP_SSL')
    def test_send_without_tls(self, mock_smtp_ssl, sample_results):
        """Test sending without TLS (SSL mode)."""
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        config = {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 465,
            'from': 'test@example.com',
            'password': 'password',
            'use_tls': False
        }

        notifier = EmailNotifier.from_config(config)

        notifier.send(
            to_emails=['user@example.com'],
            subject='Test',
            results=sample_results
        )

        # Should use SMTP_SSL instead of SMTP
        mock_smtp_ssl.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_without_password(self, mock_smtp, sample_results):
        """Test sending without authentication."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        notifier = EmailNotifier(
            smtp_host='localhost',
            smtp_port=25,
            from_email='test@example.com',
            password=None,
            use_tls=False
        )

        notifier.send(
            to_emails=['user@example.com'],
            subject='Test',
            results=sample_results
        )

        # Should not attempt login
        mock_server.login.assert_not_called()


@pytest.mark.integration
class TestEmailNotifierIntegration:
    """Integration tests for email notifier."""

    def test_format_real_html_output(self, email_config, sample_results):
        """Test that generated HTML is well-formed."""
        notifier = EmailNotifier.from_config(email_config)

        html = notifier._format_html(sample_results, None, None)

        # Check basic HTML structure
        assert html.count('<html>') == 1
        assert html.count('</html>') == 1
        assert html.count('<body>') == 1
        assert html.count('</body>') == 1

        # Check all articles are present
        assert html.count('<div class="article">') == 3  # 3 articles total

    def test_format_real_text_output(self, email_config, sample_results):
        """Test that generated plain text is readable."""
        notifier = EmailNotifier.from_config(email_config)

        text = notifier._format_text(sample_results)

        # Should be readable plain text
        lines = text.split('\n')
        assert len(lines) > 10

        # Should have clear structure
        assert any('=' in line for line in lines)  # Header separator
        assert any('-' in line for line in lines)  # Section separator
