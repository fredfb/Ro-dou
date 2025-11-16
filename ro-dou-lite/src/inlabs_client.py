"""INLABS portal client for downloading DOU data.

This module handles authentication and download of DOU XML files
from the INLABS portal (https://inlabs.in.gov.br/).
"""

import logging
import zipfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class INLABSClientError(Exception):
    """Raised when INLABS operations fail."""
    pass


class INLABSClient:
    """Client for INLABS portal authentication and file download.

    Handles login, file discovery, download, and extraction of DOU
    XML files from the INLABS portal.

    Example:
        >>> client = INLABSClient("user@example.com", "password")
        >>> client.authenticate()
        >>> files = client.download_date("2025-01-15", "/tmp/downloads")
        >>> len(files)
        3
    """

    BASE_URL = "https://inlabs.in.gov.br/"
    LOGIN_PATH = "logar.php"
    INDEX_PATH = "index.php"

    def __init__(self, username: str, password: str):
        """Initialize INLABS client.

        Args:
            username: INLABS portal email
            password: INLABS portal password
        """
        self.username = username
        self.password = password
        self.session: Optional[requests.Session] = None

    def authenticate(self) -> None:
        """Authenticate with INLABS portal.

        Raises:
            INLABSClientError: If authentication fails
        """
        self.session = requests.Session()

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        login_url = urljoin(self.BASE_URL, self.LOGIN_PATH)

        try:
            response = self.session.post(
                login_url,
                data={'email': self.username, 'password': self.password},
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            # Check if session cookie was set
            if not self.session.cookies.get('inlabs_session_cookie'):
                raise INLABSClientError("Authentication failed: no session cookie received")

            logger.info("Successfully authenticated with INLABS portal")

        except requests.RequestException as e:
            raise INLABSClientError(f"Failed to authenticate: {e}")

    def find_files(self, target_date: str) -> List[str]:
        """Find available ZIP files for a specific date.

        Args:
            target_date: Date in YYYY-MM-DD format

        Returns:
            List of file URLs (relative paths)

        Raises:
            INLABSClientError: If not authenticated or request fails
        """
        if not self.session:
            raise INLABSClientError("Not authenticated. Call authenticate() first.")

        cookie = self.session.cookies.get('inlabs_session_cookie')
        headers = {
            'Cookie': f'inlabs_session_cookie={cookie}',
            'origem': '736372697074'
        }

        # Convert YYYY-MM-DD to YYYY-MM-DD format expected by portal
        index_url = urljoin(self.BASE_URL, f"{self.INDEX_PATH}?p={target_date}")

        try:
            response = self.session.get(
                index_url,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            # Parse HTML to find download links
            soup = BeautifulSoup(response.text, 'html.parser')
            download_links = soup.find_all('a', title='Baixar Arquivo')

            files = [
                link.get('href')
                for link in download_links
                if link.get('href') and link.get('href').endswith('.zip')
            ]

            logger.info(f"Found {len(files)} files for {target_date}")
            return files

        except requests.RequestException as e:
            raise INLABSClientError(f"Failed to find files: {e}")

    def download_file(self, file_url: str, dest_dir: Path) -> Path:
        """Download a single ZIP file.

        Args:
            file_url: Relative URL to file (e.g., '?dl=DO1_2025-01-15.zip')
            dest_dir: Destination directory

        Returns:
            Path to downloaded file

        Raises:
            INLABSClientError: If download fails
        """
        if not self.session:
            raise INLABSClientError("Not authenticated. Call authenticate() first.")

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Extract filename from URL
        filename = file_url.split('dl=')[1] if 'dl=' in file_url else 'download.zip'
        dest_path = dest_dir / filename

        cookie = self.session.cookies.get('inlabs_session_cookie')
        headers = {
            'Cookie': f'inlabs_session_cookie={cookie}',
            'origem': '736372697074'
        }

        download_url = urljoin(self.BASE_URL, f"{self.INDEX_PATH}{file_url}")

        try:
            response = self.session.get(
                download_url,
                headers=headers,
                timeout=120,
                stream=True
            )

            response.raise_for_status()

            # Write file in chunks
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded {filename} ({dest_path.stat().st_size} bytes)")
            return dest_path

        except requests.RequestException as e:
            raise INLABSClientError(f"Failed to download {filename}: {e}")

    def extract_zip(self, zip_path: Path, extract_dir: Path) -> List[Path]:
        """Extract ZIP file.

        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to

        Returns:
            List of extracted file paths

        Raises:
            INLABSClientError: If extraction fails
        """
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

                # Get list of extracted files
                extracted = [extract_dir / name for name in zip_ref.namelist()]

            logger.info(f"Extracted {len(extracted)} files from {zip_path.name}")
            return extracted

        except zipfile.BadZipFile as e:
            raise INLABSClientError(f"Invalid ZIP file {zip_path}: {e}")
        except Exception as e:
            raise INLABSClientError(f"Failed to extract {zip_path}: {e}")

    def download_date(
        self,
        target_date: str,
        dest_dir: str,
        cleanup_zip: bool = True
    ) -> List[Path]:
        """Download and extract all files for a specific date.

        Complete workflow: find files, download, extract, optionally cleanup.

        Args:
            target_date: Date in YYYY-MM-DD format
            dest_dir: Destination directory
            cleanup_zip: Whether to delete ZIP files after extraction

        Returns:
            List of extracted XML file paths

        Raises:
            INLABSClientError: If any step fails
        """
        dest_path = Path(dest_dir)

        # Ensure authenticated
        if not self.session:
            self.authenticate()

        # Find available files
        file_urls = self.find_files(target_date)

        if not file_urls:
            logger.warning(f"No files found for {target_date}")
            return []

        # Download and extract each file
        all_extracted = []

        for file_url in file_urls:
            try:
                # Download ZIP
                zip_path = self.download_file(file_url, dest_path)

                # Extract to date-specific subdirectory
                extract_dir = dest_path / target_date
                extracted_files = self.extract_zip(zip_path, extract_dir)
                all_extracted.extend(extracted_files)

                # Cleanup ZIP if requested
                if cleanup_zip:
                    zip_path.unlink()
                    logger.debug(f"Removed {zip_path.name}")

            except INLABSClientError as e:
                logger.error(f"Failed to process {file_url}: {e}")
                continue

        logger.info(f"Downloaded and extracted {len(all_extracted)} files for {target_date}")
        return all_extracted

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            self.session = None
