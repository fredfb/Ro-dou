"""Search module using SQLite FTS5 full-text search.

This module provides simple, fast searching using SQLite's FTS5
capabilities, optimized for Raspberry Pi.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from src.database import Database

logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Raised when search operations fail."""
    pass


class Searcher:
    """Full-text searcher using SQLite FTS5.

    Provides simple search interface using SQLite's built-in
    FTS5 full-text search, which is much faster and simpler than
    regex-based approaches.

    Example:
        >>> db = Database("/path/to/db")
        >>> searcher = Searcher(db)
        >>> results = searcher.search(
        ...     terms=["LGPD", "dados abertos"],
        ...     sections=["DO1"],
        ...     days_back=7
        ... )
    """

    def __init__(self, database: Database):
        """Initialize searcher with database.

        Args:
            database: Database instance
        """
        self.db = database

    def search(
        self,
        terms: List[str],
        sections: Optional[List[str]] = None,
        departments: Optional[List[str]] = None,
        days_back: int = 1,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for articles matching terms and filters.

        Uses SQLite FTS5 for fast full-text search. Searches across
        title, subtitle, and text content.

        Args:
            terms: Search terms (e.g., ["LGPD", "dados abertos"])
            sections: Filter by sections (e.g., ["DO1", "DO2"])
            departments: Filter by departments (e.g., ["Ministério da Gestão"])
            days_back: Number of days to search back (default: 1)
            limit: Maximum number of results to return

        Returns:
            List of article dictionaries with matched terms highlighted

        Raises:
            SearchError: If search fails
        """
        if not terms:
            return []

        conn = self.db.connect()
        cursor = conn.cursor()

        try:
            # Build FTS5 query
            # OR logic: match any term
            fts_query = ' OR '.join([f'"{term}"' for term in terms])

            # Build base query with FTS
            query = """
                SELECT DISTINCT
                    a.id,
                    a.name,
                    a.pubname,
                    a.artcategory,
                    a.arttype,
                    a.identifica,
                    a.titulo,
                    a.subtitulo,
                    a.texto,
                    a.ementa,
                    a.assina,
                    a.pdfpage,
                    a.pubdate,
                    snippet(articles_fts, 2, '<mark>', '</mark>', '...', 64) as snippet
                FROM articles a
                JOIN articles_fts fts ON a.id = fts.rowid
                WHERE fts MATCH ?
            """

            params = [fts_query]

            # Add date filter
            cutoff_date = datetime.now().date() - timedelta(days=days_back)
            query += " AND a.pubdate >= ?"
            params.append(str(cutoff_date))

            # Add section filter
            if sections:
                placeholders = ','.join(['?' for _ in sections])
                query += f" AND a.pubname IN ({placeholders})"
                params.extend(sections)

            # Add department filter
            if departments:
                dept_conditions = ' OR '.join(
                    ['a.artcategory LIKE ?' for _ in departments]
                )
                query += f" AND ({dept_conditions})"
                params.extend([f'%{dept}%' for dept in departments])

            # Order by date (newest first)
            query += " ORDER BY a.pubdate DESC, a.id DESC"

            # Add limit
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            # Execute search
            cursor.execute(query, params)

            # Convert to dictionaries
            results = []
            for row in cursor.fetchall():
                result = dict(row)

                # Add matched terms
                result['matched_terms'] = self._find_matched_terms(result, terms)

                results.append(result)

            logger.info(f"Found {len(results)} results for terms: {terms}")
            return results

        except Exception as e:
            raise SearchError(f"Search failed: {e}")

    def search_by_config(self, search_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Search using configuration dictionary.

        Convenience method that accepts search configuration in the
        format from config.yaml.

        Args:
            search_config: Search configuration dictionary

        Returns:
            Dictionary mapping search terms to results

        Example:
            >>> config = {
            ...     'terms': ['LGPD', 'dados abertos'],
            ...     'sections': ['DO1'],
            ...     'departments': ['Ministério da Gestão']
            ... }
            >>> results = searcher.search_by_config(config)
        """
        terms = search_config.get('terms', [])
        sections = search_config.get('sections')
        departments = search_config.get('departments')

        results = self.search(
            terms=terms,
            sections=sections,
            departments=departments
        )

        # Group results by matched term
        grouped = {}
        for term in terms:
            grouped[term] = [
                r for r in results
                if term.lower() in r.get('matched_terms', [])
            ]

        return grouped

    def _find_matched_terms(
        self,
        article: Dict[str, Any],
        search_terms: List[str]
    ) -> List[str]:
        """Find which search terms matched in an article.

        Args:
            article: Article dictionary
            search_terms: List of search terms

        Returns:
            List of matched terms (lowercased)
        """
        # Combine searchable text
        searchable = ' '.join([
            str(article.get('titulo', '')),
            str(article.get('subtitulo', '')),
            str(article.get('texto', '')),
            str(article.get('artcategory', ''))
        ]).lower()

        matched = []
        for term in search_terms:
            if term.lower() in searchable:
                matched.append(term.lower())

        return matched

    def get_recent_articles(
        self,
        days: int = 1,
        sections: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent articles without search terms.

        Args:
            days: Number of days back to retrieve
            sections: Filter by sections
            limit: Maximum results

        Returns:
            List of recent articles
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        query = """
            SELECT *
            FROM articles
            WHERE pubdate >= ?
        """

        params = [str((datetime.now().date() - timedelta(days=days)))]

        if sections:
            placeholders = ','.join(['?' for _ in sections])
            query += f" AND pubname IN ({placeholders})"
            params.extend(sections)

        query += " ORDER BY pubdate DESC, id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        return [dict(row) for row in cursor.fetchall()]

    def count_articles(
        self,
        days: Optional[int] = None,
        sections: Optional[List[str]] = None
    ) -> int:
        """Count articles matching filters.

        Args:
            days: Number of days back (optional)
            sections: Filter by sections (optional)

        Returns:
            Article count
        """
        conn = self.db.connect()
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM articles WHERE 1=1"
        params = []

        if days:
            query += " AND pubdate >= ?"
            params.append(str((datetime.now().date() - timedelta(days=days))))

        if sections:
            placeholders = ','.join(['?' for _ in sections])
            query += f" AND pubname IN ({placeholders})"
            params.extend(sections)

        cursor.execute(query, params)
        return cursor.fetchone()[0]
