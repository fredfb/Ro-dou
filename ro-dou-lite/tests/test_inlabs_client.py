"""Tests for INLABS client."""

import pytest
import tempfile
from pathlib import Path
import zipfile
import responses

from src.inlabs_client import INLABSClient, INLABSClientError


@pytest.fixture
def inlabs_client():
    """Create INLABS client instance."""
    return INLABSClient("test@example.com", "testpass123")


@pytest.fixture
def temp_download_dir():
    """Create temporary download directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_zip_file():
    """Create a sample ZIP file with XML content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create XML file
        xml_path = Path(tmpdir) / "test.xml"
        xml_path.write_text('<?xml version="1.0"?><articles></articles>')

        # Create ZIP
        zip_path = Path(tmpdir) / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(xml_path, arcname="test.xml")

        yield zip_path


class TestINLABSClient:
    """Test INLABSClient class."""

    @responses.activate
    def test_authenticate_success(self, inlabs_client):
        """Test successful authentication."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie_value'}
        )

        inlabs_client.authenticate()

        assert inlabs_client.session is not None
        assert inlabs_client.session.cookies.get('inlabs_session_cookie') == 'test_cookie_value'

    @responses.activate
    def test_authenticate_no_cookie(self, inlabs_client):
        """Test authentication fails without session cookie."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200
        )

        with pytest.raises(INLABSClientError, match="no session cookie"):
            inlabs_client.authenticate()

    @responses.activate
    def test_authenticate_http_error(self, inlabs_client):
        """Test authentication handles HTTP errors."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=500
        )

        with pytest.raises(INLABSClientError, match="Failed to authenticate"):
            inlabs_client.authenticate()

    @responses.activate
    def test_find_files_success(self, inlabs_client):
        """Test finding files for a date."""
        # Mock authentication
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie'}
        )

        # Mock file listing page
        html_content = """
        <html>
            <a href="?dl=DO1_2025-01-15.zip" title="Baixar Arquivo">DO1</a>
            <a href="?dl=DO2_2025-01-15.zip" title="Baixar Arquivo">DO2</a>
            <a href="notazip.pdf" title="Baixar Arquivo">PDF</a>
        </html>
        """
        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?p=2025-01-15",
            body=html_content,
            status=200
        )

        inlabs_client.authenticate()
        files = inlabs_client.find_files("2025-01-15")

        assert len(files) == 2
        assert '?dl=DO1_2025-01-15.zip' in files
        assert '?dl=DO2_2025-01-15.zip' in files

    def test_find_files_not_authenticated(self, inlabs_client):
        """Test find_files requires authentication."""
        with pytest.raises(INLABSClientError, match="Not authenticated"):
            inlabs_client.find_files("2025-01-15")

    @responses.activate
    def test_find_files_no_results(self, inlabs_client):
        """Test finding files when none available."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie'}
        )

        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?p=2025-01-15",
            body="<html><body>No files</body></html>",
            status=200
        )

        inlabs_client.authenticate()
        files = inlabs_client.find_files("2025-01-15")

        assert files == []

    @responses.activate
    def test_download_file_success(self, inlabs_client, temp_download_dir):
        """Test downloading a file."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie'}
        )

        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?dl=test.zip",
            body=b'fake zip content',
            status=200
        )

        inlabs_client.authenticate()
        downloaded_path = inlabs_client.download_file("?dl=test.zip", temp_download_dir)

        assert downloaded_path.exists()
        assert downloaded_path.name == "test.zip"
        assert downloaded_path.read_bytes() == b'fake zip content'

    def test_download_file_not_authenticated(self, inlabs_client, temp_download_dir):
        """Test download_file requires authentication."""
        with pytest.raises(INLABSClientError, match="Not authenticated"):
            inlabs_client.download_file("?dl=test.zip", temp_download_dir)

    def test_extract_zip_success(self, inlabs_client, sample_zip_file, temp_download_dir):
        """Test extracting ZIP file."""
        extracted = inlabs_client.extract_zip(sample_zip_file, temp_download_dir)

        assert len(extracted) == 1
        assert extracted[0].name == "test.xml"
        assert extracted[0].exists()

    def test_extract_zip_invalid(self, inlabs_client, temp_download_dir):
        """Test extracting invalid ZIP file."""
        bad_zip = temp_download_dir / "bad.zip"
        bad_zip.write_text("not a zip file")

        with pytest.raises(INLABSClientError, match="Invalid ZIP file"):
            inlabs_client.extract_zip(bad_zip, temp_download_dir)

    @responses.activate
    def test_download_date_success(self, inlabs_client, temp_download_dir, sample_zip_file):
        """Test complete download workflow for a date."""
        # Mock authentication
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie'}
        )

        # Mock file listing
        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?p=2025-01-15",
            body='<html><a href="?dl=DO1.zip" title="Baixar Arquivo">DO1</a></html>',
            status=200
        )

        # Mock file download (use real ZIP content)
        zip_content = sample_zip_file.read_bytes()
        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?dl=DO1.zip",
            body=zip_content,
            status=200
        )

        # Execute
        extracted = inlabs_client.download_date(
            "2025-01-15",
            str(temp_download_dir),
            cleanup_zip=True
        )

        # Verify
        assert len(extracted) > 0
        assert all(f.exists() for f in extracted if f.suffix == '.xml')

        # ZIP should be cleaned up
        zip_files = list(temp_download_dir.glob("*.zip"))
        assert len(zip_files) == 0

    @responses.activate
    def test_download_date_no_files(self, inlabs_client, temp_download_dir):
        """Test download_date when no files available."""
        responses.add(
            responses.POST,
            "https://inlabs.in.gov.br/logar.php",
            status=200,
            headers={'Set-Cookie': 'inlabs_session_cookie=test_cookie'}
        )

        responses.add(
            responses.GET,
            "https://inlabs.in.gov.br/index.php?p=2025-01-15",
            body='<html><body>No files</body></html>',
            status=200
        )

        extracted = inlabs_client.download_date("2025-01-15", str(temp_download_dir))

        assert extracted == []

    def test_close_session(self, inlabs_client):
        """Test closing session."""
        import requests
        inlabs_client.session = requests.Session()

        inlabs_client.close()

        assert inlabs_client.session is None


@pytest.mark.slow
class TestINLABSClientIntegration:
    """Integration tests for INLABS client (require network access)."""

    def test_authentication_integration(self):
        """
        Integration test for authentication.

        NOTE: This test is disabled by default as it requires valid credentials.
        Enable by removing @pytest.mark.skip and providing real credentials.
        """
        pytest.skip("Integration test disabled - requires valid credentials")

        client = INLABSClient("your_email@example.com", "your_password")

        # This would test real authentication
        # client.authenticate()
        # assert client.session is not None
