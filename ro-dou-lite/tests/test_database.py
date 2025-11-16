"""Tests for database management."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.database import Database, DatabaseError


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    db.initialize()

    yield db

    db.close()
    Path(db_path).unlink()


@pytest.fixture
def sample_article():
    """Return a sample article dictionary."""
    return {
        'name': 'Test Publication',
        'pubname': 'DO1',
        'artcategory': 'Ministério da Gestão',
        'arttype': 'Portaria',
        'identifica': 'PORTARIA Nº 123',
        'titulo': 'Test Title',
        'subtitulo': 'Test Subtitle',
        'texto': 'This is the full text content with LGPD keywords',
        'ementa': 'Brief summary',
        'assina': 'John Doe, Director',
        'pdfpage': '12',
        'pubdate': '2025-01-15'
    }


class TestDatabase:
    """Test Database class."""

    def test_initialize_creates_tables(self, temp_db):
        """Test that initialize creates all required tables."""
        conn = temp_db.connect()
        cursor = conn.cursor()

        # Check main tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)

        tables = [row[0] for row in cursor.fetchall()]
        assert 'articles' in tables
        assert 'articles_fts' in tables
        assert 'search_log' in tables
        assert 'metadata' in tables

    def test_initialize_creates_indexes(self, temp_db):
        """Test that initialize creates indexes."""
        conn = temp_db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        indexes = [row[0] for row in cursor.fetchall()]
        assert 'idx_pubdate' in indexes
        assert 'idx_pubname' in indexes
        assert 'idx_artcategory' in indexes

    def test_initialize_idempotent(self, temp_db):
        """Test that calling initialize multiple times is safe."""
        # Should not raise an error
        temp_db.initialize()
        temp_db.initialize()

        assert temp_db.get_article_count() == 0

    def test_insert_article_success(self, temp_db, sample_article):
        """Test inserting a single article."""
        article_id = temp_db.insert_article(sample_article)

        assert article_id > 0
        assert temp_db.get_article_count() == 1

    def test_insert_article_duplicate(self, temp_db, sample_article):
        """Test that duplicate articles are ignored."""
        # Insert once
        article_id_1 = temp_db.insert_article(sample_article)
        assert article_id_1 > 0

        # Insert again (should be ignored)
        article_id_2 = temp_db.insert_article(sample_article)
        assert article_id_2 == -1

        # Should still have only 1 article
        assert temp_db.get_article_count() == 1

    def test_insert_article_fts_sync(self, temp_db, sample_article):
        """Test that FTS index is automatically synced."""
        temp_db.insert_article(sample_article)

        conn = temp_db.connect()
        cursor = conn.cursor()

        # Search FTS index
        cursor.execute("""
            SELECT rowid FROM articles_fts
            WHERE articles_fts MATCH 'lgpd'
        """)

        results = cursor.fetchall()
        assert len(results) == 1

    def test_insert_articles_batch(self, temp_db, sample_article):
        """Test batch insert of multiple articles."""
        articles = []
        for i in range(5):
            article = sample_article.copy()
            article['identifica'] = f'PORTARIA Nº {i}'
            article['titulo'] = f'Title {i}'
            articles.append(article)

        inserted_count = temp_db.insert_articles_batch(articles)

        assert inserted_count == 5
        assert temp_db.get_article_count() == 5

    def test_insert_articles_batch_with_duplicates(self, temp_db, sample_article):
        """Test batch insert skips duplicates."""
        # Insert one article first
        temp_db.insert_article(sample_article)

        # Batch insert including the duplicate
        articles = [sample_article]
        for i in range(1, 4):
            article = sample_article.copy()
            article['identifica'] = f'PORTARIA Nº {i}'
            articles.append(article)

        inserted_count = temp_db.insert_articles_batch(articles)

        # Should insert 3 new articles (skipping 1 duplicate)
        assert inserted_count == 3
        assert temp_db.get_article_count() == 4

    def test_cleanup_old_articles(self, temp_db, sample_article):
        """Test cleaning up old articles."""
        # Insert articles with different dates
        old_article = sample_article.copy()
        old_article['identifica'] = 'OLD'
        old_article['pubdate'] = '2020-01-01'

        recent_article = sample_article.copy()
        recent_article['identifica'] = 'RECENT'
        recent_article['pubdate'] = datetime.now().date().isoformat()

        temp_db.insert_article(old_article)
        temp_db.insert_article(recent_article)

        # Cleanup articles older than 365 days
        deleted_count = temp_db.cleanup_old_articles(retention_days=365)

        assert deleted_count == 1
        assert temp_db.get_article_count() == 1

    def test_get_article_count_empty(self, temp_db):
        """Test getting article count from empty database."""
        assert temp_db.get_article_count() == 0

    def test_get_article_count_nonempty(self, temp_db, sample_article):
        """Test getting article count from populated database."""
        temp_db.insert_article(sample_article)
        assert temp_db.get_article_count() == 1

    def test_get_date_range_empty(self, temp_db):
        """Test getting date range from empty database."""
        assert temp_db.get_date_range() is None

    def test_get_date_range(self, temp_db, sample_article):
        """Test getting date range from populated database."""
        article1 = sample_article.copy()
        article1['identifica'] = 'A1'
        article1['pubdate'] = '2025-01-01'

        article2 = sample_article.copy()
        article2['identifica'] = 'A2'
        article2['pubdate'] = '2025-01-15'

        temp_db.insert_article(article1)
        temp_db.insert_article(article2)

        date_range = temp_db.get_date_range()
        assert date_range == ('2025-01-01', '2025-01-15')

    def test_log_notification(self, temp_db, sample_article):
        """Test logging notification."""
        article_id = temp_db.insert_article(sample_article)

        temp_db.log_notification('LGPD', article_id)

        # Verify log entry exists
        conn = temp_db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_log")
        assert cursor.fetchone()[0] == 1

    def test_log_notification_duplicate(self, temp_db, sample_article):
        """Test logging same notification twice (should be ignored)."""
        article_id = temp_db.insert_article(sample_article)

        temp_db.log_notification('LGPD', article_id)
        temp_db.log_notification('LGPD', article_id)

        # Should still have only 1 log entry
        conn = temp_db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_log")
        assert cursor.fetchone()[0] == 1

    def test_was_notified_false(self, temp_db, sample_article):
        """Test checking notification status when not notified."""
        article_id = temp_db.insert_article(sample_article)

        assert temp_db.was_notified('LGPD', article_id) is False

    def test_was_notified_true(self, temp_db, sample_article):
        """Test checking notification status when already notified."""
        article_id = temp_db.insert_article(sample_article)

        temp_db.log_notification('LGPD', article_id)

        assert temp_db.was_notified('LGPD', article_id) is True

    def test_was_notified_different_term(self, temp_db, sample_article):
        """Test that notification is term-specific."""
        article_id = temp_db.insert_article(sample_article)

        temp_db.log_notification('LGPD', article_id)

        # Different term should return False
        assert temp_db.was_notified('dados abertos', article_id) is False

    def test_context_manager(self, sample_article):
        """Test using database as context manager."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            with Database(db_path) as db:
                db.initialize()
                db.insert_article(sample_article)
                assert db.get_article_count() == 1

            # Connection should be closed
            assert db._conn is None

        finally:
            Path(db_path).unlink()

    def test_database_path_created(self):
        """Test that database parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'subdir' / 'nested' / 'test.db'

            db = Database(str(db_path))
            db.initialize()

            assert db_path.exists()
            assert db_path.parent.exists()

            db.close()


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_full_workflow(self, temp_db, sample_article):
        """Test complete database workflow."""
        # Insert articles
        articles = []
        for i in range(10):
            article = sample_article.copy()
            article['identifica'] = f'ART-{i}'
            article['titulo'] = f'Article about {"LGPD" if i % 2 == 0 else "dados"}'
            articles.append(article)

        inserted = temp_db.insert_articles_batch(articles)
        assert inserted == 10

        # Verify FTS search works
        conn = temp_db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM articles a
            JOIN articles_fts fts ON a.id = fts.rowid
            WHERE fts MATCH 'lgpd'
        """)

        lgpd_count = cursor.fetchone()[0]
        assert lgpd_count == 5

        # Log some notifications
        cursor.execute("SELECT id FROM articles LIMIT 3")
        for row in cursor.fetchall():
            temp_db.log_notification('LGPD', row[0])

        # Verify notification log
        cursor.execute("SELECT COUNT(*) FROM search_log")
        assert cursor.fetchone()[0] == 3
