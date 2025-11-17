# Pasta de Exemplos INLABS

Esta pasta contém exemplos de arquivos XML do INLABS para validação do parser.

## 📁 Estrutura

```
inlabs/
├── README.md           # Este arquivo
├── *.xml              # Arquivos XML de exemplo
└── *.zip              # Arquivos ZIP originais (opcional)
```

## 📤 Como Adicionar Exemplos

### Opção 1: Copiar XML Extraído
```bash
# Extraia seu ZIP do INLABS
unzip DO1_2025-01-15.zip -d /tmp/inlabs_temp

# Copie para esta pasta
cp /tmp/inlabs_temp/*.xml /home/user/Ro-dou/inlabs/
```

### Opção 2: Copiar ZIP Completo
```bash
# Copie o ZIP original
cp seu_arquivo_inlabs.zip /home/user/Ro-dou/inlabs/
```

### Opção 3: Criar Exemplo Sanitizado
```bash
# Pegue apenas primeiras 300 linhas (se quiser proteger dados)
head -n 300 arquivo_original.xml > /home/user/Ro-dou/inlabs/exemplo_do1.xml
```

## 🧪 Testar Parser com Exemplos

Depois de adicionar arquivos aqui, teste o parser:

```bash
cd /home/user/Ro-dou/ro-dou-lite
source venv/bin/activate

# Teste com XML específico
python -c "
from src.xml_parser import XMLParser
import sys
sys.path.insert(0, '..')

parser = XMLParser()
articles = parser.parse_file('../inlabs/seu_arquivo.xml')

print(f'✅ Artigos extraídos: {len(articles)}')
print(f'✅ Exemplo do primeiro artigo:')
print(f'   Título: {articles[0][\"titulo\"]}')
print(f'   Seção: {articles[0][\"pubname\"]}')
print(f'   Data: {articles[0][\"pubdate\"]}')
print(f'   Categoria: {articles[0][\"artcategory\"]}')
"
```

## 🔒 Privacidade

Esta pasta está em `.gitignore` - arquivos aqui **NÃO** serão commitados ao git.

Você pode adicionar XMLs reais sem se preocupar com vazamento de dados.

## 📝 Notas

- Adicione pelo menos 1 XML de cada seção (DO1, DO2, DO3) se possível
- Inclua exemplos de edições extras (DO1E, DO2E, DO3E) se tiver
- Mantenha nomes descritivos: `DO1_2025-01-15.xml`
