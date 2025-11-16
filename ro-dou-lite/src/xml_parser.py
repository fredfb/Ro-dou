"""XML parser for INLABS DOU files.

This module parses XML files downloaded from INLABS portal and extracts
article data into dictionaries suitable for database insertion.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from slugify import slugify
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class XMLParseError(Exception):
    """Raised when XML parsing fails."""
    pass


class XMLParser:
    """Parser for INLABS DOU XML files.

    Parses XML files containing DOU articles and extracts structured data.
    Uses ElementTree (lighter than pandas) for better performance on Pi.

    Example:
        >>> parser = XMLParser()
        >>> articles = parser.parse_file("DO1_2025-01-15.xml")
        >>> len(articles)
        150
    """

    def parse_file(self, xml_path: str) -> List[Dict[str, Any]]:
        """Parse a single XML file and extract articles.

        Args:
            xml_path: Path to XML file

        Returns:
            List of article dictionaries

        Raises:
            XMLParseError: If file cannot be parsed
        """
        path = Path(xml_path)

        if not path.exists():
            raise XMLParseError(f"XML file not found: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            articles = []
            for article_elem in root.findall('.//article'):
                article = self._parse_article(article_elem)
                if article:
                    articles.append(article)

            logger.info(f"Parsed {len(articles)} articles from {path.name}")
            return articles

        except ET.ParseError as e:
            raise XMLParseError(f"Failed to parse XML file {xml_path}: {e}")
        except Exception as e:
            raise XMLParseError(f"Unexpected error parsing {xml_path}: {e}")

    def parse_directory(self, dir_path: str, pattern: str = "**/*.xml") -> List[Dict[str, Any]]:
        """Parse all XML files in a directory.

        Args:
            dir_path: Path to directory containing XML files
            pattern: Glob pattern for XML files (default: **/*.xml)

        Returns:
            List of all articles from all files

        Raises:
            XMLParseError: If directory doesn't exist
        """
        directory = Path(dir_path)

        if not directory.exists():
            raise XMLParseError(f"Directory not found: {dir_path}")

        all_articles = []
        xml_files = list(directory.glob(pattern))

        if not xml_files:
            logger.warning(f"No XML files found in {dir_path} matching {pattern}")
            return []

        for xml_file in xml_files:
            try:
                articles = self.parse_file(str(xml_file))
                all_articles.extend(articles)
            except XMLParseError as e:
                logger.error(f"Failed to parse {xml_file.name}: {e}")
                continue

        logger.info(f"Parsed {len(all_articles)} total articles from {len(xml_files)} files")
        return all_articles

    def _parse_article(self, article_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single article XML element.

        Args:
            article_elem: XML Element representing an article

        Returns:
            Article dictionary or None if parsing fails
        """
        try:
            # Extract text content from nested body element
            body_elem = article_elem.find('.//body')
            texto = self._extract_text(body_elem) if body_elem is not None else ""

            # Extract signature from body
            assina = self._extract_signature(texto) if texto else None

            # Extract other fields
            article = {
                'name': self._get_text(article_elem, 'name'),
                'pubname': self._get_text(article_elem, 'pubName'),
                'artcategory': self._get_text(article_elem, 'artCategory'),
                'arttype': self._get_text(article_elem, 'artType'),
                'identifica': self._get_text(article_elem, 'identifica'),
                'titulo': self._get_text(article_elem, 'titulo'),
                'subtitulo': self._get_text(article_elem, 'subtitulo'),
                'ementa': self._get_text(article_elem, 'ementa'),
                'texto': texto,
                'assina': assina,
                'pdfpage': self._get_text(article_elem, 'pdfPage'),
                'pubdate': self._parse_date(self._get_text(article_elem, 'pubDate'))
            }

            return article

        except Exception as e:
            logger.debug(f"Failed to parse article element: {e}")
            return None

    def _get_text(self, element: ET.Element, tag: str) -> Optional[str]:
        """Safely extract text from XML element.

        Args:
            element: Parent XML element
            tag: Child tag name to extract

        Returns:
            Text content or None
        """
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _extract_text(self, body_elem: ET.Element) -> str:
        """Extract and clean text from body element.

        Args:
            body_elem: Body XML element containing article text

        Returns:
            Cleaned text content
        """
        if body_elem is None:
            return ""

        # Get all text content
        text = ET.tostring(body_elem, encoding='unicode', method='html')

        # Remove excessive whitespace
        text = ' '.join(text.split())

        return text

    def _extract_signature(self, html_text: str) -> Optional[str]:
        """Extract signature from article HTML.

        Searches for <p class="assina"> elements which contain
        the signature information.

        Args:
            html_text: HTML content of article

        Returns:
            Comma-separated signatures or None
        """
        if not html_text:
            return None

        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            p_tags = soup.find_all('p', class_='assina')

            if p_tags:
                signatures = [p.get_text(strip=True) for p in p_tags]
                return ', '.join(signatures)

        except Exception as e:
            logger.debug(f"Failed to extract signature: {e}")

        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format (YYYY-MM-DD).

        INLABS uses DD/MM/YYYY format.

        Args:
            date_str: Date string from XML (DD/MM/YYYY)

        Returns:
            ISO format date string (YYYY-MM-DD) or None
        """
        if not date_str:
            return None

        try:
            # Parse DD/MM/YYYY format
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')

        except ValueError as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
