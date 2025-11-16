"""Tests for searcher module."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.database import Database
from src.searcher import Searcher, SearchError


@pytest.fixture
def temp_db_with_data():
    """Create a temporary database with sample data."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    db.initialize()

    # Insert sample articles
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    articles = [
        {
            'pubname': 'DO1',
            'artcategory': 'Ministério da Gestão',
            'titulo': 'Portaria sobre LGPD',
            'texto': 'Esta portaria estabelece diretrizes sobre a Lei Geral de Proteção de Dados',
            'pubdate': str(today),
            'identifica': 'PORT-001'
        },
        {
            'pubname': 'DO2',
            'artcategory': 'Ministério da Economia',
            'titulo': 'Decreto sobre dados abertos',
            'texto': 'Regulamenta a política de dados abertos do governo',
            'pubdate': str(today),
            'identifica': 'DEC-001'
        },
        {
            'pubname': 'DO1',
            'artcategory': 'Ministério da Gestão',
            'titulo': 'Portaria antiga',
            'texto': 'Artigo antigo sem palavras-chave relevantes',
            'pubdate': str(week_ago),
            'identifica': 'PORT-OLD'
        },
        {
            'pubname': 'DO3',
            'artcategory': 'Ministério da Saúde',
            'titulo': 'Regulamento sanitário',
            'texto': 'Normas de vigilância sanitária',
            'pubdate': str(yesterday),
            'identifica': 'REG-001'
        },
        {
            'pubname': 'DO1',
            'artcategory': 'Ministério da Gestão',
            'titulo': 'Acesso à informação',
            'texto': 'Diretrizes sobre transparência e acesso à informação pública',
            'pubdate': str(today),
            'identifica': 'PORT-002'
        },
    ]

    db.insert_articles_batch(articles)

    yield db

    db.close()
    Path(db_path).unlink()


class TestSearcher:
    """Test Searcher class."""

    def test_search_single_term(self, temp_db_with_data):
        """Test searching for a single term."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=["LGPD"])

        assert len(results) == 1
        assert results[0]['titulo'] == 'Portaria sobre LGPD'
        assert 'lgpd' in results[0]['matched_terms']

    def test_search_multiple_terms(self, temp_db_with_data):
        """Test searching for multiple terms (OR logic)."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=["LGPD", "dados abertos"])

        # Should match both articles
        assert len(results) >= 2
        titulos = [r['titulo'] for r in results]
        assert 'Portaria sobre LGPD' in titulos
        assert 'Decreto sobre dados abertos' in titulos

    def test_search_with_section_filter(self, temp_db_with_data):
        """Test searching with section filter."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(
            terms=["LGPD", "dados"],
            sections=["DO1"]
        )

        # Should only return DO1 articles
        assert all(r['pubname'] == 'DO1' for r in results)

    def test_search_with_department_filter(self, temp_db_with_data):
        """Test searching with department filter."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(
            terms=["LGPD", "informação"],
            departments=["Ministério da Gestão"]
        )

        # Should only return articles from Ministério da Gestão
        assert all('Gestão' in r['artcategory'] for r in results)
        assert len(results) >= 2

    def test_search_with_days_back(self, temp_db_with_data):
        """Test searching with date range."""
        searcher = Searcher(temp_db_with_data)

        # Search only today
        results = searcher.search(
            terms=["Portaria"],
            days_back=1
        )

        # Should not include week-old article
        identifiers = [r['identifica'] for r in results]
        assert 'PORT-OLD' not in identifiers

    def test_search_with_limit(self, temp_db_with_data):
        """Test searching with result limit."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(
            terms=["Ministério"],
            limit=2
        )

        assert len(results) <= 2

    def test_search_no_results(self, temp_db_with_data):
        """Test search returning no results."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=["nonexistent term xyz"])

        assert results == []

    def test_search_empty_terms(self, temp_db_with_data):
        """Test search with empty terms returns nothing."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=[])

        assert results == []

    def test_search_case_insensitive(self, temp_db_with_data):
        """Test search is case-insensitive."""
        searcher = Searcher(temp_db_with_data)

        results_upper = searcher.search(terms=["LGPD"])
        results_lower = searcher.search(terms=["lgpd"])

        assert len(results_upper) == len(results_lower)
        assert results_upper[0]['id'] == results_lower[0]['id']

    def test_search_by_config(self, temp_db_with_data):
        """Test search using configuration dictionary."""
        searcher = Searcher(temp_db_with_data)

        config = {
            'terms': ['LGPD', 'dados abertos'],
            'sections': ['DO1', 'DO2'],
            'departments': None
        }

        results = searcher.search_by_config(config)

        # Should return dict with terms as keys
        assert isinstance(results, dict)
        assert 'LGPD' in results or 'lgpd' in [k.lower() for k in results.keys()]

    def test_get_recent_articles(self, temp_db_with_data):
        """Test getting recent articles without search."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.get_recent_articles(days=1)

        # Should return today's articles
        assert len(results) > 0
        assert all(
            r['pubdate'] == str(datetime.now().date())
            for r in results
        )

    def test_get_recent_articles_with_section_filter(self, temp_db_with_data):
        """Test getting recent articles with section filter."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.get_recent_articles(days=1, sections=["DO1"])

        # Should only return DO1 articles
        assert all(r['pubname'] == 'DO1' for r in results)

    def test_get_recent_articles_with_limit(self, temp_db_with_data):
        """Test getting recent articles with limit."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.get_recent_articles(days=7, limit=2)

        assert len(results) <= 2

    def test_count_articles_no_filter(self, temp_db_with_data):
        """Test counting all articles."""
        searcher = Searcher(temp_db_with_data)

        count = searcher.count_articles()

        assert count == 5  # We inserted 5 articles

    def test_count_articles_with_days_filter(self, temp_db_with_data):
        """Test counting articles with date filter."""
        searcher = Searcher(temp_db_with_data)

        count = searcher.count_articles(days=1)

        # Should only count today's articles
        assert count == 3  # 3 articles from today

    def test_count_articles_with_section_filter(self, temp_db_with_data):
        """Test counting articles with section filter."""
        searcher = Searcher(temp_db_with_data)

        count = searcher.count_articles(sections=["DO1"])

        # Should only count DO1 articles
        assert count == 3  # 3 DO1 articles

    def test_matched_terms_tracking(self, temp_db_with_data):
        """Test that matched terms are correctly tracked."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=["LGPD", "dados"])

        # Find the LGPD article
        lgpd_article = next(r for r in results if 'LGPD' in r['titulo'])

        assert 'lgpd' in lgpd_article['matched_terms']
        assert 'dados' in lgpd_article['matched_terms']

    def test_snippet_generation(self, temp_db_with_data):
        """Test that search results include snippets."""
        searcher = Searcher(temp_db_with_data)

        results = searcher.search(terms=["LGPD"])

        assert len(results) > 0
        # Snippet should exist and contain highlights
        assert 'snippet' in results[0]


@pytest.mark.integration
class TestSearcherIntegration:
    """Integration tests for searcher."""

    def test_full_search_workflow(self, temp_db_with_data):
        """Test complete search workflow."""
        searcher = Searcher(temp_db_with_data)

        # Perform multiple searches
        lgpd_results = searcher.search(terms=["LGPD"], days_back=7)
        dados_results = searcher.search(terms=["dados abertos"], sections=["DO2"])

        # Get recent articles
        recent = searcher.get_recent_articles(days=2)

        # Count articles
        total = searcher.count_articles()
        recent_count = searcher.count_articles(days=1)

        # Assertions
        assert len(lgpd_results) >= 1
        assert len(dados_results) >= 1
        assert len(recent) >= 3
        assert total == 5
        assert recent_count <= total

    def test_search_performance(self, temp_db_with_data):
        """Test search performance with larger dataset."""
        # Insert more articles
        articles = []
        today = str(datetime.now().date())

        for i in range(100):
            articles.append({
                'pubname': f'DO{i % 3 + 1}',
                'artcategory': 'Test Category',
                'titulo': f'Article {i} about {"LGPD" if i % 10 == 0 else "other topic"}',
                'texto': f'Content {i}',
                'pubdate': today,
                'identifica': f'ART-{i}'
            })

        temp_db_with_data.insert_articles_batch(articles)

        # Perform search
        import time
        searcher = Searcher(temp_db_with_data)

        start = time.time()
        results = searcher.search(terms=["LGPD"])
        elapsed = time.time() - start

        # Search should be fast (< 100ms even on Pi)
        assert elapsed < 0.1
        assert len(results) >= 10  # Should find all LGPD articles
