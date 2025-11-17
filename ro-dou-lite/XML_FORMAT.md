# Formato XML do INLABS - Guia para Validação

Este documento descreve o formato esperado dos arquivos XML do INLABS e como fornecer exemplos para validação do parser.

## 📋 Estrutura XML Esperada

Baseado na implementação original do Ro-DOU, o XML do INLABS deve ter a seguinte estrutura:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<articles>
    <article>
        <!-- Metadados do artigo -->
        <name>Nome da publicação</name>
        <pubName>DO1</pubName>           <!-- Seção: DO1, DO2, DO3, DO1E, etc -->
        <pubDate>15/01/2025</pubDate>    <!-- Formato: DD/MM/YYYY -->
        <artSection>Seção 1</artSection>
        <artCategory>Ministério da Gestão</artCategory>
        <artType>Portaria</artType>
        <identifica>PORTARIA Nº 123</identifica>
        <titulo>Título do artigo</titulo>
        <subtitulo>Subtítulo (opcional)</subtitulo>
        <ementa>Resumo/ementa (opcional)</ementa>
        <pdfPage>15</pdfPage>            <!-- Página do PDF -->

        <!-- Corpo do artigo (HTML) -->
        <body>
            <p class="identifica">PORTARIA Nº 123</p>
            <p>Conteúdo do artigo...</p>
            <p>Mais conteúdo...</p>
            <p class="assina">JOÃO DA SILVA</p>
            <p class="assina">Secretário de Gestão</p>
        </body>
    </article>

    <!-- Mais artigos... -->
</articles>
```

## 🔍 Campos Importantes

### Metadados
- **`name`**: Nome da publicação (ex: "DIÁRIO OFICIAL DA UNIÃO")
- **`pubName`**: Código da seção (DO1, DO2, DO3, DO1E, DO2E, DO3E, etc)
- **`pubDate`**: Data de publicação no formato **DD/MM/YYYY**
- **`artCategory`**: Órgão/categoria (ex: "Ministério da Gestão")
- **`artType`**: Tipo de ato (Portaria, Decreto, Resolução, etc)
- **`identifica`**: Identificador do ato
- **`titulo`**: Título principal
- **`pdfPage`**: Página no PDF original

### Corpo (Body)
- Elemento `<body>` contém HTML com o texto completo
- Tags `<p class="assina">` contêm as assinaturas
- O parser extrai assinaturas automaticamente desses elementos

## 📤 Como Fornecer Exemplos

Para validar se o parser está correto para seu caso específico, por favor forneça:

### 1. **Arquivo XML Completo** (preferencial)
```bash
# Exemplo de como extrair um XML do INLABS
# Após baixar e descompactar, você terá arquivos .xml

# Compartilhe um arquivo pequeno com 2-3 artigos
cat DO1_2025-01-15.xml | head -n 200 > exemplo_do1.xml
```

### 2. **Amostra de Artigo Individual**

Se não puder compartilhar o arquivo completo, forneça pelo menos:

```xml
<article>
    <name>DIÁRIO OFICIAL DA UNIÃO</name>
    <pubName>DO1</pubName>
    <pubDate>15/01/2025</pubDate>
    <artCategory>Ministério da Gestão</artCategory>
    <artType>Portaria</artType>
    <identifica>PORTARIA Nº 123</identifica>
    <titulo>Seu título aqui</titulo>
    <body>
        <p>Conteúdo aqui...</p>
        <p class="assina">Nome do Assinante</p>
    </body>
</article>
```

### 3. **Informações Adicionais Úteis**

- Nome dos arquivos ZIP que você baixa (ex: `DO1_2025-01-15.zip`)
- Estrutura de diretórios dentro do ZIP
- Campos que são críticos para suas buscas
- Exemplos de valores em campos como `artCategory`, `artType`, etc.

## 🐛 Possíveis Problemas

### Parser Atual Assume:
1. **Elemento raiz**: `<articles>` contém múltiplos `<article>`
2. **Data**: Formato `DD/MM/YYYY` (convertido para `YYYY-MM-DD`)
3. **Body**: Elemento separado com HTML
4. **Assinaturas**: Tags `<p class="assina">`
5. **Encoding**: UTF-8

### Se Seu XML for Diferente:

Envie exemplos e podemos adaptar o parser para:
- Formatos de data alternativos
- Estruturas XML diferentes
- Campos adicionais ou nomes diferentes
- Encodings específicos

## 🔧 Testando o Parser

Depois de fornecer exemplos, você pode testar:

```bash
# Teste o parser com seu XML
cd ro-dou-lite
source venv/bin/activate

# Crie um script de teste
python -c "
from src.xml_parser import XMLParser
parser = XMLParser()
articles = parser.parse_file('seu_arquivo.xml')
print(f'Artigos extraídos: {len(articles)}')
for art in articles[:2]:  # Primeiros 2 artigos
    print(f'Título: {art[\"titulo\"]}')
    print(f'Seção: {art[\"pubname\"]}')
    print(f'Data: {art[\"pubdate\"]}')
    print('---')
"
```

## 📊 Validação Esperada

Um XML válido deve resultar em:

```python
{
    'name': 'DIÁRIO OFICIAL DA UNIÃO',
    'pubname': 'DO1',
    'pubdate': '2025-01-15',  # Convertido para ISO
    'artcategory': 'Ministério da Gestão',
    'arttype': 'Portaria',
    'identifica': 'PORTARIA Nº 123',
    'titulo': 'Título do ato',
    'subtitulo': 'Subtítulo (se houver)',
    'ementa': 'Resumo (se houver)',
    'texto': 'HTML do body com tags preservadas',
    'assina': 'Nome1, Nome2',  # Extraído automaticamente
    'pdfpage': '15'
}
```

## 📧 Como Enviar

Por favor, compartilhe:

1. **Arquivo XML de exemplo** (sanitize dados sensíveis se necessário)
2. **Descrição**: De qual seção é (DO1, DO2, DO3)
3. **Data**: Qual data do DOU
4. **Observações**: Qualquer particularidade que notou

Isso ajudará a garantir 100% de compatibilidade com o formato real do INLABS!

---

**Nota**: O parser atual foi criado com base na análise do código original do Ro-DOU que usa `pandas.read_xml()`. Exemplos reais garantirão que todos os detalhes estão corretos.
