"""Tests for XML parser."""

import pytest
import tempfile
from pathlib import Path

from src.xml_parser import XMLParser, XMLParseError


@pytest.fixture
def sample_xml():
    """Return sample XML content matching INLABS format."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<articles>
    <article>
        <name>Diário Oficial da União</name>
        <pubName>DO1</pubName>
        <artCategory>Ministério da Gestão</artCategory>
        <artType>Portaria</artType>
        <identifica>PORTARIA Nº 123</identifica>
        <titulo>Estabelece diretrizes sobre LGPD</titulo>
        <subtitulo>Proteção de dados pessoais</subtitulo>
        <ementa>Dispõe sobre a proteção de dados</ementa>
        <pubDate>15/01/2025</pubDate>
        <pdfPage>12</pdfPage>
        <body>
            <p>Este é o texto completo do artigo sobre LGPD.</p>
            <p class="assina">JOÃO DA SILVA</p>
            <p class="assina">Secretário</p>
        </body>
    </article>
    <article>
        <name>Diário Oficial da União</name>
        <pubName>DO2</pubName>
        <artCategory>Ministério da Economia</artCategory>
        <artType>Decreto</artType>
        <identifica>DECRETO Nº 456</identifica>
        <titulo>Regulamenta dados abertos</titulo>
        <pubDate>15/01/2025</pubDate>
        <pdfPage>25</pdfPage>
        <body>
            <p>Conteúdo sobre dados abertos governamentais.</p>
        </body>
    </article>
</articles>
"""


@pytest.fixture
def sample_xml_file(sample_xml):
    """Create a temporary XML file with sample content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(sample_xml)
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink()


@pytest.fixture
def empty_xml_file():
    """Create an empty XML file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<articles></articles>')
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink()


@pytest.fixture
def invalid_xml_file():
    """Create an invalid XML file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write('<invalid><unclosed>')
        temp_path = f.name

    yield temp_path

    Path(temp_path).unlink()


class TestXMLParser:
    """Test XMLParser class."""

    def test_parse_file_success(self, sample_xml_file):
        """Test parsing a valid XML file."""
        parser = XMLParser()
        articles = parser.parse_file(sample_xml_file)

        assert len(articles) == 2
        assert articles[0]['titulo'] == 'Estabelece diretrizes sobre LGPD'
        assert articles[1]['titulo'] == 'Regulamenta dados abertos'

    def test_parse_file_extracts_all_fields(self, sample_xml_file):
        """Test that all fields are extracted correctly."""
        parser = XMLParser()
        articles = parser.parse_file(sample_xml_file)

        article = articles[0]

        assert article['name'] == 'Diário Oficial da União'
        assert article['pubname'] == 'DO1'
        assert article['artcategory'] == 'Ministério da Gestão'
        assert article['arttype'] == 'Portaria'
        assert article['identifica'] == 'PORTARIA Nº 123'
        assert article['titulo'] == 'Estabelece diretrizes sobre LGPD'
        assert article['subtitulo'] == 'Proteção de dados pessoais'
        assert article['ementa'] == 'Dispõe sobre a proteção de dados'
        assert article['pdfpage'] == '12'
        assert article['pubdate'] == '2025-01-15'
        assert 'LGPD' in article['texto']
        assert article['assina'] == 'JOÃO DA SILVA, Secretário'

    def test_parse_file_missing_signature(self, sample_xml_file):
        """Test parsing article without signature."""
        parser = XMLParser()
        articles = parser.parse_file(sample_xml_file)

        # Second article has no signature
        article = articles[1]
        assert article['assina'] is None

    def test_parse_file_not_found(self):
        """Test parsing non-existent file raises error."""
        parser = XMLParser()

        with pytest.raises(XMLParseError, match="XML file not found"):
            parser.parse_file('/nonexistent/file.xml')

    def test_parse_file_invalid_xml(self, invalid_xml_file):
        """Test parsing invalid XML raises error."""
        parser = XMLParser()

        with pytest.raises(XMLParseError, match="Failed to parse XML"):
            parser.parse_file(invalid_xml_file)

    def test_parse_file_empty(self, empty_xml_file):
        """Test parsing empty XML file returns empty list."""
        parser = XMLParser()
        articles = parser.parse_file(empty_xml_file)

        assert articles == []

    def test_parse_directory_success(self, sample_xml_file):
        """Test parsing directory with XML files."""
        parser = XMLParser()
        directory = Path(sample_xml_file).parent

        articles = parser.parse_directory(str(directory), "*.xml")

        # At least our sample file should be parsed
        assert len(articles) >= 2

    def test_parse_directory_not_found(self):
        """Test parsing non-existent directory raises error."""
        parser = XMLParser()

        with pytest.raises(XMLParseError, match="Directory not found"):
            parser.parse_directory('/nonexistent/directory')

    def test_parse_directory_no_xml_files(self):
        """Test parsing directory with no XML files returns empty list."""
        parser = XMLParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a non-XML file
            (Path(tmpdir) / "test.txt").write_text("not xml")

            articles = parser.parse_directory(tmpdir)
            assert articles == []

    def test_parse_directory_multiple_files(self):
        """Test parsing directory with multiple XML files."""
        parser = XMLParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple XML files
            for i in range(3):
                xml_path = Path(tmpdir) / f"test_{i}.xml"
                xml_path.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<articles>
    <article>
        <pubName>DO{i}</pubName>
        <titulo>Test {i}</titulo>
        <pubDate>15/01/2025</pubDate>
        <body><p>Content {i}</p></body>
    </article>
</articles>
""")

            articles = parser.parse_directory(tmpdir)
            assert len(articles) == 3

    def test_parse_directory_skips_invalid_files(self, sample_xml_file, invalid_xml_file):
        """Test that invalid files are skipped without crashing."""
        parser = XMLParser()

        directory = Path(sample_xml_file).parent

        # This should not raise, just log errors for invalid files
        articles = parser.parse_directory(str(directory))

        # Should still get articles from valid file
        assert len(articles) >= 2

    def test_parse_date_valid(self):
        """Test date parsing with valid format."""
        parser = XMLParser()

        result = parser._parse_date('15/01/2025')
        assert result == '2025-01-15'

    def test_parse_date_invalid(self):
        """Test date parsing with invalid format."""
        parser = XMLParser()

        result = parser._parse_date('invalid-date')
        assert result is None

    def test_parse_date_none(self):
        """Test date parsing with None input."""
        parser = XMLParser()

        result = parser._parse_date(None)
        assert result is None

    def test_extract_signature_with_multiple_tags(self):
        """Test extracting multiple signature tags."""
        parser = XMLParser()

        html = '<p class="assina">John Doe</p><p class="assina">Director</p>'
        signature = parser._extract_signature(html)

        assert signature == 'John Doe, Director'

    def test_extract_signature_none(self):
        """Test extracting signature from text without signature tags."""
        parser = XMLParser()

        html = '<p>Regular text without signature</p>'
        signature = parser._extract_signature(html)

        assert signature is None

    def test_extract_signature_empty(self):
        """Test extracting signature from empty text."""
        parser = XMLParser()

        signature = parser._extract_signature('')
        assert signature is None

    def test_extract_text_with_html(self):
        """Test text extraction preserves content."""
        parser = XMLParser()

        import xml.etree.ElementTree as ET
        body = ET.fromstring('<body><p>Paragraph 1</p><p>Paragraph 2</p></body>')

        text = parser._extract_text(body)

        assert 'Paragraph 1' in text
        assert 'Paragraph 2' in text

    def test_extract_text_none(self):
        """Test text extraction with None input."""
        parser = XMLParser()

        text = parser._extract_text(None)
        assert text == ''


@pytest.mark.integration
class TestXMLParserIntegration:
    """Integration tests for XML parser."""

    def test_parse_realistic_xml(self):
        """Test parsing realistic INLABS XML structure."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<articles>
    <article>
        <name>DIÁRIO OFICIAL DA UNIÃO</name>
        <pubName>DO1</pubName>
        <pubDate>16/11/2025</pubDate>
        <artSection>Seção 1</artSection>
        <artCategory>Ministério da Gestão e da Inovação em Serviços Públicos/Secretaria de Gestão e Inovação</artCategory>
        <artType>Portaria</artType>
        <identifica>PORTARIA SGI Nº 9.999, DE 15 DE NOVEMBRO DE 2025</identifica>
        <titulo>Dispõe sobre a proteção de dados pessoais</titulo>
        <subtitulo>Lei Geral de Proteção de Dados Pessoais</subtitulo>
        <ementa>Estabelece diretrizes para conformidade com LGPD</ementa>
        <pdfPage>15</pdfPage>
        <body>
            <p class="identifica">PORTARIA SGI Nº 9.999, DE 15 DE NOVEMBRO DE 2025</p>
            <p>O SECRETÁRIO DE GESTÃO E INOVAÇÃO, no uso das atribuições que lhe conferem...</p>
            <p>Art. 1º Esta Portaria estabelece diretrizes sobre LGPD e dados pessoais.</p>
            <p>Art. 2º As disposições desta Portaria aplicam-se a todos os órgãos.</p>
            <p class="assina">JOÃO DA SILVA</p>
            <p class="assina">Secretário de Gestão e Inovação</p>
        </body>
    </article>
</articles>
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(xml_content)
            temp_path = f.name

        try:
            parser = XMLParser()
            articles = parser.parse_file(temp_path)

            assert len(articles) == 1

            article = articles[0]
            assert article['pubname'] == 'DO1'
            assert article['pubdate'] == '2025-11-16'
            assert 'LGPD' in article['texto']
            assert 'dados pessoais' in article['texto']
            assert article['assina'] == 'JOÃO DA SILVA, Secretário de Gestão e Inovação'
            assert article['ementa'] == 'Estabelece diretrizes para conformidade com LGPD'

        finally:
            Path(temp_path).unlink()
