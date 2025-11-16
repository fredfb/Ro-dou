"""SQLite database management for Ro-DOU Lite.

This module handles all database operations including schema creation,
article insertion, FTS5 full-text search index, and data cleanup.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class Database:
    """SQLite database manager for DOU articles.

    Manages a SQLite database with FTS5 full-text search capabilities
    optimized for Raspberry Pi (low memory usage, fast queries).

    Example:
        >>> db = Database("/path/to/dou_articles.db")
        >>> db.initialize()
        >>> db.insert_article({
        ...     'titulo': 'Example',
        ...     'texto': 'Content',
        ...     'pubdate': '2025-01-15'
        ... })
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Get or create database connection.

        Returns:
            SQLite connection object
        """
        if self._conn is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._conn.row_factory = sqlite3.Row

            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")

        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def initialize(self) -> None:
        """Create database schema if it doesn't exist.

        Creates:
        - articles table for storing DOU publications
        - articles_fts virtual table for full-text search (FTS5)
        - Triggers to keep FTS index in sync
        - search_log table for tracking notifications
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Main articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                pubname TEXT NOT NULL,
                artcategory TEXT,
                arttype TEXT,
                identifica TEXT,
                titulo TEXT,
                subtitulo TEXT,
                texto TEXT NOT NULL,
                ementa TEXT,
                assina TEXT,
                pdfpage TEXT,
                pubdate DATE NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(identifica, pubdate, pubname)
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pubdate
            ON articles(pubdate DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pubname
            ON articles(pubname)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_artcategory
            ON articles(artcategory)
        """)

        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
            USING fts5(
                titulo,
                subtitulo,
                texto,
                artcategory,
                content=articles,
                content_rowid=id,
                tokenize='porter unicode61 remove_diacritics 2'
            )
        """)

        # Triggers to keep FTS in sync with articles table
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_ai
            AFTER INSERT ON articles
            BEGIN
                INSERT INTO articles_fts(rowid, titulo, subtitulo, texto, artcategory)
                VALUES (new.id, new.titulo, new.subtitulo, new.texto, new.artcategory);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_ad
            AFTER DELETE ON articles
            BEGIN
                DELETE FROM articles_fts WHERE rowid = old.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_au
            AFTER UPDATE ON articles
            BEGIN
                UPDATE articles_fts
                SET titulo = new.titulo,
                    subtitulo = new.subtitulo,
                    texto = new.texto,
                    artcategory = new.artcategory
                WHERE rowid = new.id;
            END
        """)

        # Search log table for tracking sent notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term TEXT NOT NULL,
                article_id INTEGER NOT NULL,
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id),
                UNIQUE(search_term, article_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_log_article
            ON search_log(article_id)
        """)

        # Metadata table for schema versioning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Store schema version
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('schema_version', ?)
        """, (str(self.SCHEMA_VERSION),))

        conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def insert_article(self, article: Dict[str, Any]) -> int:
        """Insert a single article into database.

        Args:
            article: Dictionary containing article fields

        Returns:
            Article ID (rowid)

        Raises:
            DatabaseError: If insertion fails
        """
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO articles (
                    name, pubname, artcategory, arttype, identifica,
                    titulo, subtitulo, texto, ementa, assina, pdfpage, pubdate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.get('name'),
                article.get('pubname'),
                article.get('artcategory'),
                article.get('arttype'),
                article.get('identifica'),
                article.get('titulo'),
                article.get('subtitulo'),
                article.get('texto'),
                article.get('ementa'),
                article.get('assina'),
                article.get('pdfpage'),
                article.get('pubdate')
            ))

            conn.commit()
            article_id = cursor.lastrowid
            logger.debug(f"Inserted article ID {article_id}")
            return article_id

        except sqlite3.IntegrityError as e:
            # Duplicate article, skip silently
            logger.debug(f"Skipping duplicate article: {article.get('identifica')}")
            return -1
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert article: {e}")

    def insert_articles_batch(self, articles: List[Dict[str, Any]]) -> int:
        """Insert multiple articles in a single transaction.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of articles successfully inserted

        Raises:
            DatabaseError: If batch insertion fails
        """
        conn = self.connect()
        cursor = conn.cursor()
        inserted_count = 0

        try:
            for article in articles:
                try:
                    cursor.execute("""
                        INSERT INTO articles (
                            name, pubname, artcategory, arttype, identifica,
                            titulo, subtitulo, texto, ementa, assina, pdfpage, pubdate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article.get('name'),
                        article.get('pubname'),
                        article.get('artcategory'),
                        article.get('arttype'),
                        article.get('identifica'),
                        article.get('titulo'),
                        article.get('subtitulo'),
                        article.get('texto'),
                        article.get('ementa'),
                        article.get('assina'),
                        article.get('pdfpage'),
                        article.get('pubdate')
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # Skip duplicates
                    continue

            conn.commit()
            logger.info(f"Inserted {inserted_count}/{len(articles)} articles")
            return inserted_count

        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"Failed to insert batch: {e}")

    def cleanup_old_articles(self, retention_days: int) -> int:
        """Delete articles older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of articles deleted
        """
        conn = self.connect()
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        try:
            cursor.execute("""
                DELETE FROM articles
                WHERE pubdate < ?
            """, (cutoff_date.date(),))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Deleted {deleted_count} articles older than {cutoff_date.date()}")
            return deleted_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to cleanup old articles: {e}")

    def get_article_count(self) -> int:
        """Get total number of articles in database.

        Returns:
            Article count
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM articles")
        return cursor.fetchone()[0]

    def get_date_range(self) -> Optional[tuple[str, str]]:
        """Get earliest and latest publication dates in database.

        Returns:
            Tuple of (earliest_date, latest_date) or None if empty
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MIN(pubdate), MAX(pubdate)
            FROM articles
        """)

        result = cursor.fetchone()
        if result[0] and result[1]:
            return (result[0], result[1])
        return None

    def log_notification(self, search_term: str, article_id: int) -> None:
        """Log that a notification was sent for an article.

        Args:
            search_term: The search term that matched
            article_id: ID of the article

        Raises:
            DatabaseError: If logging fails
        """
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO search_log (search_term, article_id)
                VALUES (?, ?)
            """, (search_term, article_id))

            conn.commit()

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to log notification: {e}")

    def was_notified(self, search_term: str, article_id: int) -> bool:
        """Check if notification was already sent for this article+term.

        Args:
            search_term: The search term
            article_id: ID of the article

        Returns:
            True if already notified
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM search_log
            WHERE search_term = ? AND article_id = ?
        """, (search_term, article_id))

        return cursor.fetchone() is not None
