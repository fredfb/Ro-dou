"""XML parser for INLABS DOU files.

This module parses XML files downloaded from INLABS portal and extracts
article data into dictionaries suitable for database insertion.

INLABS XML Structure:
    - Each file contains ONE article
    - Metadata is in <article> attributes
    - Content is inside <body> with CDATA sections
    - Signature is in <p class="assinaPr">
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class XMLParseError(Exception):
    """Raised when XML parsing fails."""
    pass


class XMLParser:
    """Parser for INLABS DOU XML files.

    Parses XML files containing DOU articles (one per file) and extracts
    structured data. Uses ElementTree (lighter than pandas) for better
    performance on Pi.

    INLABS Format:
        <xml>
          <article pubName="DO2" pubDate="01/01/2023" artCategory="..." ...>
            <body>
              <Identifica><![CDATA[...]]></Identifica>
              <Titulo><![CDATA[...]]></Titulo>
              <Texto><![CDATA[<p>...</p>]]></Texto>
            </body>
          </article>
        </xml>

    Example:
        >>> parser = XMLParser()
        >>> articles = parser.parse_file("529_20230101_20225185.xml.xml")
        >>> len(articles)
        1
    """

    def parse_file(self, xml_path: str) -> List[Dict[str, Any]]:
        """Parse a single XML file and extract article.

        INLABS files contain ONE article per file.

        Args:
            xml_path: Path to XML file

        Returns:
            List with single article dictionary

        Raises:
            XMLParseError: If file cannot be parsed
        """
        path = Path(xml_path)

        if not path.exists():
            raise XMLParseError(f"XML file not found: {xml_path}")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Find the <article> element (should be only one)
            article_elem = root.find('.//article')

            if article_elem is None:
                logger.warning(f"No <article> element found in {path.name}")
                return []

            article = self._parse_article(article_elem)

            if article:
                logger.debug(f"Parsed 1 article from {path.name}")
                return [article]
            else:
                return []

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

        Extracts metadata from attributes and content from <body> children.

        Args:
            article_elem: XML Element representing an article

        Returns:
            Article dictionary or None if parsing fails
        """
        try:
            # Extract metadata from ATTRIBUTES
            pubname = article_elem.get('pubName')
            pubdate = article_elem.get('pubDate')
            artcategory = article_elem.get('artCategory')
            arttype = article_elem.get('artType')
            name = article_elem.get('name')
            pdfpage = article_elem.get('pdfPage')

            # Extract content from <body> children
            body_elem = article_elem.find('body')

            if body_elem is None:
                logger.debug("No <body> element found in article")
                return None

            # Extract fields from body children (with CDATA)
            identifica = self._get_cdata(body_elem, 'Identifica')
            titulo = self._get_cdata(body_elem, 'Titulo')
            subtitulo = self._get_cdata(body_elem, 'SubTitulo')
            ementa = self._get_cdata(body_elem, 'Ementa')
            texto_html = self._get_cdata(body_elem, 'Texto')

            # Extract signature from HTML texto
            assina = self._extract_signature(texto_html) if texto_html else None

            # Build article dictionary
            article = {
                'name': name,
                'pubname': pubname,
                'artcategory': artcategory,
                'arttype': arttype,
                'identifica': identifica,
                'titulo': titulo,
                'subtitulo': subtitulo,
                'ementa': ementa,
                'texto': texto_html,
                'assina': assina,
                'pdfpage': pdfpage,
                'pubdate': self._parse_date(pubdate)
            }

            return article

        except Exception as e:
            logger.debug(f"Failed to parse article element: {e}")
            return None

    def _get_cdata(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Extract text from child element (handles CDATA).

        Args:
            parent: Parent XML element
            tag: Child tag name to extract

        Returns:
            Text content (from CDATA or text) or None
        """
        child = parent.find(tag)

        if child is None:
            return None

        # ElementTree automatically unwraps CDATA
        text = child.text

        if text:
            return text.strip()

        return None

    def _extract_signature(self, html_text: str) -> Optional[str]:
        """Extract signature from article HTML.

        Searches for <p class="assinaPr"> and <p class="assina"> elements
        which contain signature information in INLABS format.

        Args:
            html_text: HTML content of article

        Returns:
            Comma-separated signatures or None
        """
        if not html_text:
            return None

        try:
            soup = BeautifulSoup(html_text, 'html.parser')

            # INLABS uses both class="assinaPr" and class="assina"
            p_tags = soup.find_all('p', class_=['assinaPr', 'assina'])

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
