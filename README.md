![banner](docs/img/banner.png)
# Ro-DOU

[![CI Tests](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml/badge.svg)](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml)

O Ro-DOU é uma ferramenta que efetua um clipping do Diário Oficial da União (D.O.U.) e dos Diários Oficiais de municípios, por meio do [Querido Diário](https://docs.queridodiario.ok.org.br/pt-br/latest/). O Ro-DOU permite o recebimento de notificações (via e-mail, Slack, Discord ou outros) de todas as publicações que contenham as palavras-chaves que você definir.

Para acessar a página de documentação do Ro-DOU, que contém detalhes sobre o funcionamento da ferramenta e o modo de utilizá-la, além de outras informações importantes, acesse o link <https://gestaogovbr.github.io/Ro-dou/>.

O Ro-DOU é uma solução desenvolvida pela Secretaria de Gestão e Inovação do [Ministério da Gestão e da Inovação em Serviços Públicos](https://www.gov.br/gestao/pt-br).

## 📦 Versões Disponíveis

Este repositório contém duas versões do Ro-DOU:

### 🚀 **Ro-DOU (Principal)**
Versão completa baseada em Apache Airflow com suporte a múltiplas fontes de dados (DOU, Querido Diário, INLABS) e notificações via e-mail, Slack e Discord.

- **Localização**: Raiz do repositório (`/src`, `/dag_confs`, `/dag_load_inlabs`)
- **Tecnologias**: Apache Airflow 2.10.0, PostgreSQL 17.5, Docker Compose
- **Requisitos**: ~800MB RAM, Docker instalado
- **Ideal para**: Servidores, implantações enterprise, múltiplos DAGs configuráveis

📖 **Documentação**: <https://gestaogovbr.github.io/Ro-dou/>

### 🍓 **Ro-DOU Lite** (Raspberry Pi)
Versão otimizada e leve para dispositivos com recursos limitados, focada em consumo de dados INLABS.

- **Localização**: `/ro-dou-lite`
- **Tecnologias**: Python 3.10+, SQLite com FTS5, scripts cron
- **Requisitos**: 150-250MB RAM, Python 3.10+
- **Ideal para**: Raspberry Pi 3/4, implantações edge, uso pessoal

📖 **Documentação**: [ro-dou-lite/README.md](ro-dou-lite/README.md)

---

## 🚀 Início Rápido

### Ro-DOU (Principal)

```bash
# Clone o repositório
git clone https://github.com/gestaogovbr/Ro-dou.git
cd Ro-dou

# Inicie o ambiente completo
make run

# Acesse a interface web
# URL: http://localhost:8080
# Usuário: airflow
# Senha: airflow
```

### Ro-DOU Lite

```bash
# Navegue para o diretório
cd ro-dou-lite

# Instale as dependências
pip install -r requirements.txt

# Configure suas credenciais
cp config.example.yaml config.yaml
# Edite config.yaml com suas credenciais INLABS

# Execute o download e busca
python scripts/download_secao2.py
python scripts/run_searches.py
```

---

## 📚 Documentação Completa

- **Documentação Oficial**: <https://gestaogovbr.github.io/Ro-dou/>
- **Guia para AI Assistants**: [CLAUDE.md](CLAUDE.md)
- **Ro-DOU Lite**: [ro-dou-lite/README.md](ro-dou-lite/README.md)
- **Formato XML INLABS**: [ro-dou-lite/XML_FORMAT.md](ro-dou-lite/XML_FORMAT.md)
- **Validação do Parser**: [ro-dou-lite/VALIDATION.md](ro-dou-lite/VALIDATION.md)
