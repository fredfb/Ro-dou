# CLAUDE.md - Ro-DOU Codebase Guide for AI Assistants

> **Last Updated**: 2025-11-18
> **Version**: 0.6.0
> **Project**: Ro-DOU - Official Brazilian Gazette Monitoring Tool

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Versions](#repository-versions)
3. [Architecture & Technology Stack](#architecture--technology-stack)
4. [Repository Structure](#repository-structure)
5. [Development Workflows](#development-workflows)
6. [Key Conventions](#key-conventions)
7. [Testing Guidelines](#testing-guidelines)
8. [Configuration System](#configuration-system)
9. [Common Tasks](#common-tasks)
10. [Troubleshooting](#troubleshooting)
11. [Code Modification Guidelines](#code-modification-guidelines)
12. [Ro-DOU Lite (Raspberry Pi)](#ro-dou-lite-raspberry-pi)

---

## Project Overview

**Ro-DOU** is a Brazilian government tool that performs automated monitoring and notification of official gazette publications (Diário Oficial da União and municipal gazettes). It enables users to receive notifications via email, Slack, or Discord when publications contain user-defined keywords.

**Developed by**: Secretaria de Gestão e Inovação - Ministério da Gestão e da Inovação em Serviços Públicos

**Core Functionality**:
- Search official publications (DOU, Querido Diário, INLABS) for keyword matches
- Filter by department, section, publication type, date ranges
- Send notifications via multiple channels (email, Slack, Discord)
- Generate reports with HTML formatting and CSV attachments
- Dynamic DAG generation from YAML configurations

**Documentation**: https://gestaogovbr.github.io/Ro-dou/
**Language**: Portuguese (all documentation, code comments, and user-facing content)

---

## Repository Versions

This repository contains **two versions** of Ro-DOU optimized for different deployment scenarios:

### 🚀 Ro-DOU (Main Version)

**Location**: Root directory (`/src`, `/dag_confs`, `/dag_load_inlabs`)

**Purpose**: Full-featured enterprise solution with Apache Airflow orchestration

**Key Features**:
- Multiple data sources: DOU API, Querido Diário, INLABS
- Dynamic DAG generation from YAML configurations
- Multiple notification channels: Email, Slack, Discord
- Airflow web UI for monitoring and management
- PostgreSQL for metadata and INLABS data storage
- CSV attachments and HTML reports

**Requirements**:
- Docker + Docker Compose
- ~800MB RAM (Airflow + PostgreSQL)
- Network access to DOU/QD/INLABS APIs

**Best for**: Server deployments, multiple users, complex workflows, organizational use

### 🍓 Ro-DOU Lite (Raspberry Pi Version)

**Location**: `/ro-dou-lite` directory

**Purpose**: Lightweight solution for resource-constrained devices

**Key Features**:
- INLABS data source only
- SQLite database with FTS5 full-text search
- Email notifications only
- Cron-based scheduling (no Airflow)
- Validated XML parser (96.8% signature extraction rate)
- Section-specific download scripts (DO1, DO2, DO3)

**Requirements**:
- Python 3.10+
- 150-250MB RAM (no containers)
- INLABS portal credentials

**Best for**: Raspberry Pi 3/4, edge deployments, personal use, learning

**Detailed Documentation**: See [Ro-DOU Lite section](#ro-dou-lite-raspberry-pi) below

---

## Architecture & Technology Stack

### Main Version (Airflow-based)

### Core Technologies

- **Apache Airflow 2.10.0**: Workflow orchestration platform
- **Python 3.10**: Programming language
- **Docker Compose**: Local development environment
- **PostgreSQL 17.5**: Database for Airflow metadata and INLABS data
- **Pydantic**: YAML schema validation
- **Pandas**: Data manipulation and CSV generation

### Data Sources

1. **DOU (Diário Oficial da União)**: Federal gazette via DOU API
2. **Querido Diário (QD)**: Municipal gazettes via QD API
3. **INLABS**: Alternative DOU data source with XML files stored in PostgreSQL

### Python Dependencies

**Production** (`requirements.txt`):
```
pandas==2.1.4
unidecode==1.2.0
html2text==2024.2.26
markdown==3.6.0
```

**Testing** (`tests-requirements.txt`):
```
pytest==7.2.1
pytest-mock==3.10.0
mock==5.0.1
jsonschema==4.21.1
PyYAML==6.0.1
requests==2.32.2
```

### Airflow Configuration

- **Executor**: LocalExecutor (single-machine deployment)
- **Timezone**: America/Sao_Paulo
- **Authentication**: Basic auth (airflow:airflow for development)
- **SMTP**: smtp4dev for local email testing
- **XCom Pickling**: Enabled for complex object serialization

---

## Repository Structure

```
/home/user/Ro-dou/
├── src/                              # Core application source code
│   ├── dou_dag_generator.py          # Dynamic DAG generator (539 lines)
│   ├── searchers.py                  # Search implementations for DOU/QD/INLABS (589 lines)
│   ├── parsers.py                    # YAML configuration parser (160 lines)
│   ├── schemas.py                    # Pydantic models for validation (246 lines)
│   ├── notification/                 # Notification delivery modules
│   │   ├── notifier.py              # Notification orchestrator
│   │   ├── email_sender.py          # SMTP email sender
│   │   ├── slack_sender.py          # Slack webhook integration
│   │   ├── discord_sender.py        # Discord webhook integration
│   │   └── isender.py               # Abstract sender interface
│   ├── hooks/                        # Custom Airflow hooks
│   │   ├── dou_hook.py              # DOU API integration
│   │   └── inlabs_hook.py           # INLABS API integration
│   └── utils/                        # Utility functions
│       ├── date.py                  # Date manipulation utilities
│       └── search_domains.py        # Enum definitions for search parameters
│
├── dag_confs/                        # YAML configuration directory
│   └── examples_and_tests/          # Example configurations (17 files)
│
├── dag_load_inlabs/                  # INLABS data loading DAG
│   ├── ro-dou_inlabs_load_pg_dag.py # DAG for downloading/loading INLABS data
│   ├── sql/init-db.sql              # Database initialization script
│   └── utils/                        # INLABS-specific utilities
│
├── tests/                            # Test suite (11 test files)
│   ├── test_validate_yaml_schemas.py
│   ├── searchers_test.py
│   ├── parsers_test.py
│   ├── dag_generator_test.py
│   └── conftest.py                   # Pytest fixtures
│
├── docs/                             # MkDocs documentation
│   ├── mkdocs.yml                    # MkDocs configuration
│   └── docs/                         # Markdown documentation files
│       ├── definicao/               # What is Ro-DOU
│       ├── como_utilizar/           # Installation and usage
│       ├── como_funciona/           # How it works
│       ├── como_contribuir/         # Contribution guidelines
│       └── outros/                  # FAQ, links, contact
│
├── .github/workflows/                # CI/CD workflows
│   ├── ci-tests.yml                 # Run tests on push/PR
│   ├── gh_pages.yml                 # Deploy documentation
│   └── docker_build_and_publish.yml # Build and publish Docker image
│
├── mnt/                              # Mount points (gitignored)
│   ├── airflow-logs/                # Airflow logs
│   └── pgdata/                      # PostgreSQL data
│
├── docker-compose.yml                # Multi-service Docker setup
├── Dockerfile                        # Airflow image with Ro-DOU
├── Makefile                          # Development workflow automation
├── requirements.txt                  # Production dependencies
└── tests-requirements.txt            # Testing dependencies
```

### Key Files by Functionality

| File | Purpose | Lines | Key Classes/Functions |
|------|---------|-------|----------------------|
| `src/dou_dag_generator.py` | Dynamic DAG generation from YAML | 539 | `DouDigestDagGenerator`, `merge_results()` |
| `src/searchers.py` | Search implementations | 589 | `BaseSearcher`, `DOUSearcher`, `QDSearcher`, `INLABSSearcher` |
| `src/schemas.py` | Pydantic validation models | 246 | `DAGConfig`, `SearchConfig`, `ReportConfig` |
| `src/parsers.py` | YAML configuration parser | 160 | `YAMLParser`, `DAGConfig` |
| `src/notification/notifier.py` | Notification orchestration | - | `Notifier` |

---

## Development Workflows

### Quick Start

```bash
# Start the complete environment
make run

# Access Airflow UI
# URL: http://localhost:8080
# Credentials: airflow / airflow

# Access SMTP4Dev (email testing)
# URL: http://localhost:5001

# Run tests
make tests

# Stop all containers
make down
```

### What `make run` Does

The `make run` command executes the following steps sequentially:

1. **Create log directories** (`./mnt/airflow-logs`)
2. **Start Docker containers** (PostgreSQL, Airflow webserver, Airflow scheduler, SMTP4Dev)
3. **Create Airflow variables**:
   - `termos_exemplo_variavel`: Example search terms (LGPD, lei geral de proteção de dados, acesso à informação)
   - `path_tmp`: Temporary path for file operations (`/tmp`)
4. **Initialize INLABS database**: Create `inlabs` database and schema
5. **Create Airflow connections**:
   - `inlabs_db`: PostgreSQL connection to INLABS database
   - `inlabs_portal`: HTTP connection to INLABS portal (requires valid credentials)
6. **Activate INLABS load DAG**: Unpause the `ro-dou_inlabs_load_pg` DAG

### Docker Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `postgres` | postgres:17.5-alpine | 5432 | Airflow metadata + INLABS data |
| `airflow-webserver` | Custom (Dockerfile) | 8080 | Airflow UI |
| `airflow-scheduler` | Custom (Dockerfile) | - | Task scheduling |
| `smtp4dev` | rnwood/smtp4dev:v3 | 5001, 25, 143 | Email testing |

### Environment Variables (from docker-compose.yml)

```bash
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__DEFAULT_TIMEZONE=America/Sao_Paulo
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
RO_DOU__DAG_CONF_DIR=/opt/airflow/dags/ro_dou/dag_confs
AIRFLOW__SMTP__SMTP_HOST=smtp4dev
AIRFLOW__SMTP__SMTP_PORT=25
```

### Volume Mounts

```yaml
./src → /opt/airflow/dags/ro_dou_src
./mnt/airflow-logs → /opt/airflow/logs
./dag_confs → /opt/airflow/dags/ro_dou/dag_confs
./dag_load_inlabs → /opt/airflow/dags/dag_load_inlabs
./tests → /opt/airflow/tests
```

### Airflow DAG Generation Flow

1. **YAML Configuration**: User creates a YAML file in `dag_confs/examples_and_tests/`
2. **Airflow Startup**: On scheduler startup, `dou_dag_generator.py` is executed
3. **YAML Parsing**: `YAMLParser` reads and validates YAML using Pydantic schemas
4. **DAG Creation**: `DouDigestDagGenerator` creates an Airflow DAG for each YAML file
5. **Task Structure**:
   ```
   start → [fetch_terms_from_db] → task_group:execute_searchs → check_if_has_match →
   send_notification OR skip_notification → end
   ```
6. **Scheduling**: DAG runs on defined schedule (default: 5 AM daily with hash-based minute randomization)

---

## Key Conventions

### Code Style

- **Language**: Portuguese for documentation, comments, variable names in user-facing code
- **Docstrings**: Use triple-quoted strings with clear descriptions
- **Type Hints**: Use type hints for function parameters and return values
- **Imports**: Follow PEP 8 ordering (standard library → third-party → local)

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `DOUSearcher`, `YAMLParser` |
| Functions | snake_case | `merge_results()`, `get_trigger_date()` |
| Constants | UPPER_SNAKE_CASE | `SEARCH_RESULT_TYPE` |
| Private methods | _leading_underscore | `_validate_config()` |
| DAG IDs | snake_case | `basic_example`, `ro-dou_inlabs_load_pg` |
| YAML fields | snake_case | `dou_sections`, `is_exact_search` |

### Airflow Conventions

- **DAG Tags**: Always include `{"dou", "generated_dag"}` for generated DAGs
- **DAG ID Format**: Use descriptive snake_case names (e.g., `ministry_search_lgpd`)
- **Task IDs**: Use descriptive names (`fetch_terms_from_db`, `send_notification`)
- **XCom Keys**: Use descriptive keys for data sharing between tasks
- **Default Schedule**: 5 AM daily with hash-based minute randomization for load distribution
- **Timezone**: Always use America/Sao_Paulo

### YAML Configuration Conventions

**Minimal Configuration**:
```yaml
dag:
  id: unique_dag_name
  description: Brief description
  search:
    terms:
      - search term 1
      - search term 2
  report:
    emails:
      - email@example.com
```

**Default Values** (from `schemas.py`):
- `sources`: `["DOU"]`
- `date`: `"DIA"` (today)
- `dou_sections`: `["TODOS"]`
- `field`: `"TUDO"` (all fields)
- `is_exact_search`: `True`
- `ignore_signature_match`: `False`
- `force_rematch`: `False`
- `skip_null`: `True`
- `attach_csv`: `False`

### Search Term Conventions

Search terms can be loaded from three sources:

1. **Direct YAML list**:
   ```yaml
   terms:
     - dados abertos
     - governo aberto
   ```

2. **Airflow variable**:
   ```yaml
   terms:
     from_airflow_variable: termos_exemplo_variavel
   ```

3. **Database query**:
   ```yaml
   terms:
     from_db_select:
       sql: "SELECT term FROM search_terms WHERE active = true"
       conn_id: my_database_connection
   ```

---

## Testing Guidelines

### Running Tests

```bash
# Run all tests
make tests

# Run specific test file (inside container)
docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest test_validate_yaml_schemas.py -vvv"

# Run with coverage (inside container)
docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest --cov=ro_dou_src --cov-report=html"
```

### Test Structure

Tests are organized by module:

- `test_validate_yaml_schemas.py`: YAML schema validation
- `searchers_test.py`: DOU searcher tests
- `qd_searcher_test.py`: Querido Diário searcher tests
- `inlabs_searcher_test.py`: INLABS searcher tests
- `parsers_test.py`: YAML parser tests
- `dag_generator_test.py`: DAG generation tests
- `discord_sender_test.py`: Discord notification tests
- `test_isender.py`: Sender interface tests
- `inlabs_hook_test.py`: INLABS hook tests

### Test Fixtures (conftest.py)

Key fixtures available for tests:

- Mock Airflow context
- Mock search results
- Mock database connections
- Example YAML configurations

### Writing New Tests

1. **Location**: Place tests in `/tests/` directory
2. **Naming**: Use `test_*.py` or `*_test.py` format
3. **Mocking**: Use `pytest-mock` for mocking Airflow components
4. **Assertions**: Use descriptive assertion messages
5. **Fixtures**: Define reusable fixtures in `conftest.py`

---

## Configuration System

### YAML Schema (Pydantic Models)

The configuration system uses Pydantic models defined in `src/schemas.py`:

```
RoDouConfig
└── DAGConfig
    ├── id (str)
    ├── description (str)
    ├── tags (Set[str])
    ├── owner (List[str])
    ├── schedule (Optional[str])
    ├── dataset (Optional[str])
    ├── search (Union[List[SearchConfig], SearchConfig])
    │   └── SearchConfig
    │       ├── header (Optional[str])
    │       ├── sources (List[str])
    │       ├── territory_id (Optional[Union[int, List[int]]])
    │       ├── date (str)
    │       ├── dou_sections (List[str])
    │       ├── department (Optional[List[str]])
    │       ├── department_ignore (Optional[List[str]])
    │       ├── terms (Union[List[str], FetchTermsConfig])
    │       ├── field (str)
    │       ├── is_exact_search (bool)
    │       ├── ignore_signature_match (bool)
    │       ├── force_rematch (bool)
    │       ├── full_text (bool)
    │       ├── use_summary (bool)
    │       ├── pubtype (Optional[List[str]])
    │       ├── excerpt_size (Optional[int])
    │       └── number_of_excerpts (Optional[int])
    └── report (ReportConfig)
        ├── slack (Optional[dict])
        ├── discord (Optional[dict])
        ├── emails (Optional[List[EmailStr]])
        ├── attach_csv (bool)
        ├── subject (Optional[str])
        ├── skip_null (bool)
        ├── hide_filters (bool)
        ├── header_text (Optional[str])
        ├── footer_text (Optional[str])
        └── no_results_found_text (str)
```

### Search Parameters

#### Date Options (`date`)
- `DIA`: Today (default)
- `SEMANA`: Last 7 days
- `MES`: Last 30 days
- `ANO`: Last 365 days

#### DOU Sections (`dou_sections`)
- `SECAO_1`, `SECAO_2`, `SECAO_3`
- `EDICAO_EXTRA`, `EDICAO_EXTRA_1A`, `EDICAO_EXTRA_1B`, `EDICAO_EXTRA_1D`
- `EDICAO_EXTRA_2A`, `EDICAO_EXTRA_2B`, `EDICAO_EXTRA_2D`
- `EDICAO_EXTRA_3A`, `EDICAO_EXTRA_3B`, `EDICAO_EXTRA_3D`
- `EDICAO_SUPLEMENTAR`
- `TODOS` (default)

#### Search Fields (`field`)
- `TUDO`: All fields (default)
- `TITULO`: Title only
- `CONTEUDO`: Content only

#### Data Sources (`sources`)
- `DOU`: Diário Oficial da União (default)
- `QD`: Querido Diário (municipal gazettes)
- `INLABS`: Alternative DOU source with PostgreSQL storage

### Example Configurations

The repository includes 17 example configurations in `dag_confs/examples_and_tests/`:

1. **basic_example.yaml**: Minimal configuration with search terms
2. **all_parameters_example.yaml**: Demonstrates all available parameters
3. **slack_example.yaml**: Slack webhook notification
4. **discord_example.yaml**: Discord webhook notification
5. **terms_from_variable.yaml**: Load terms from Airflow variable
6. **terms_from_db_example.yaml**: Load terms from database query
7. **inlabs_example.yaml**: Search INLABS data source
8. **qd_example.yaml**: Search Querido Diário (municipal gazettes)
9. **multiple_searchs_example.yaml**: Multiple search configurations in one DAG
10. **department_example.yaml**: Filter by department
11. **pubtype_example.yaml**: Filter by publication type
12. **header_and_footer_example.yaml**: Custom header/footer in reports
13. **hide_filters_example.yaml**: Hide filters in report output
14. **basic_example_skip_null.yaml**: Skip notifications when no results
15. **inlabs_advanced_search_example.yaml**: Advanced INLABS features
16. **qd_list_territory_id_example.yaml**: Multiple territory IDs for QD
17. **markdown_docs_example.yaml**: Markdown formatting in reports

---

## Common Tasks

### Adding a New Search Configuration

1. **Create YAML file** in `dag_confs/examples_and_tests/`:
   ```yaml
   dag:
     id: my_new_search
     description: Search for specific ministry publications
     search:
       terms:
         - termo de busca
       department:
         - Ministério da Gestão
     report:
       emails:
         - user@example.com
   ```

2. **Restart Airflow scheduler** (DAGs are loaded on startup):
   ```bash
   docker restart airflow-scheduler
   ```

3. **Verify DAG creation** in Airflow UI (http://localhost:8080)

### Adding a New Data Source

1. **Create searcher class** in `src/searchers.py`:
   ```python
   class NewSourceSearcher(BaseSearcher):
       def search(self, **kwargs):
           # Implement search logic
           pass
   ```

2. **Update DAG generator** in `src/dou_dag_generator.py`:
   ```python
   # Add to get_searchers() method
   if "NEWSOURCE" in search_sources:
       searchers.append(NewSourceSearcher(...))
   ```

3. **Update schema** in `src/schemas.py` if needed:
   ```python
   sources: Optional[List[str]] = Field(
       default=["DOU"],
       description="..., NEWSOURCE"
   )
   ```

4. **Add tests** in `tests/newsource_searcher_test.py`

### Adding a New Notification Channel

1. **Create sender class** in `src/notification/`:
   ```python
   from notification.isender import ISender

   class NewChannelSender(ISender):
       def send(self, message: str, **kwargs):
           # Implement send logic
           pass
   ```

2. **Update notifier** in `src/notification/notifier.py`:
   ```python
   if specs.report.newchannel:
       sender = NewChannelSender(specs.report.newchannel)
       sender.send(message)
   ```

3. **Update schema** in `src/schemas.py`:
   ```python
   class ReportConfig(BaseModel):
       newchannel: Optional[dict] = Field(
           default=None,
           description="New channel webhook configuration"
       )
   ```

4. **Add tests** in `tests/newchannel_sender_test.py`

### Modifying Search Logic

**Key files**:
- `src/searchers.py:BaseSearcher` - Abstract base class
- `src/searchers.py:DOUSearcher` - DOU implementation (lines 100-350)
- `src/searchers.py:QDSearcher` - QD implementation (lines 350-500)
- `src/searchers.py:INLABSSearcher` - INLABS implementation (lines 500-589)

**Search result structure**:
```python
SearchResult = Dict[str, Dict[str, Dict[str, List[dict]]]]
# Structure: {term: {department: {group_name: [results]}}}
```

### Debugging DAG Generation

1. **Check YAML syntax**:
   ```bash
   docker exec airflow-webserver python3 -c "
   import yaml
   with open('/opt/airflow/dags/ro_dou/dag_confs/examples_and_tests/your_file.yaml') as f:
       print(yaml.safe_load(f))
   "
   ```

2. **Validate against schema**:
   ```bash
   docker exec airflow-webserver sh -c "cd /opt/airflow/tests/ && pytest test_validate_yaml_schemas.py::test_your_file -vvv"
   ```

3. **Check Airflow logs**:
   ```bash
   docker exec airflow-scheduler cat /opt/airflow/logs/scheduler/latest/dou_dag_generator.py.log
   ```

4. **Test DAG manually**:
   ```bash
   docker exec airflow-webserver airflow dags test my_dag_id 2025-01-01
   ```

---

## Troubleshooting

### Common Issues

#### 1. DAG not appearing in Airflow UI

**Symptoms**: YAML file created but DAG doesn't show up

**Solutions**:
- Check YAML syntax: `yamllint your_file.yaml`
- Verify file is in correct directory: `dag_confs/examples_and_tests/`
- Check scheduler logs for parsing errors
- Restart scheduler: `docker restart airflow-scheduler`
- Verify `RO_DOU__DAG_CONF_DIR` environment variable

#### 2. Tests failing

**Symptoms**: `make tests` returns errors

**Solutions**:
- Ensure containers are running: `docker ps`
- Check test file imports: verify `sys.path` includes source directories
- Update test data if schema changed
- Clear pytest cache: `docker exec airflow-webserver sh -c "cd /opt/airflow/tests && pytest --cache-clear"`

#### 3. Email notifications not sent

**Symptoms**: DAG runs successfully but no emails received

**Solutions**:
- Check SMTP4Dev UI: http://localhost:5001
- Verify email address format in YAML (must be valid EmailStr)
- Check Airflow SMTP configuration: `AIRFLOW__SMTP__SMTP_HOST=smtp4dev`
- Review task logs: Airflow UI → DAG → Task → Logs

#### 4. Database connection errors

**Symptoms**: INLABS searches fail with connection errors

**Solutions**:
- Verify database is initialized: `docker exec airflow-webserver sh -c "PGPASSWORD=airflow psql -U airflow -h ro-dou-postgres-1 -d inlabs -c '\dt'"`
- Check connection exists: Airflow UI → Admin → Connections → `inlabs_db`
- Verify PostgreSQL is running: `docker ps | grep postgres`
- Re-run database initialization: `make create-inlabs-db`

#### 5. Permission issues with mounted volumes

**Symptoms**: "Permission denied" errors when writing logs or data

**Solutions**:
- Check directory permissions: `ls -la ./mnt/`
- Create directories with correct permissions: `mkdir -p ./mnt/airflow-logs -m a=rwx`
- Verify `AIRFLOW_UID` environment variable: defaults to 50000
- Fix ownership: `sudo chown -R 50000:0 ./mnt/`

#### 6. YAML validation errors

**Symptoms**: Pydantic validation errors on DAG generation

**Solutions**:
- Review error message for specific field
- Check against schema in `src/schemas.py`
- Validate email addresses are in correct format
- Ensure required fields are present: `dag.id`, `dag.description`, `search.terms`, `report`
- Use example files as templates

### Logs Locations

| Component | Log Location |
|-----------|--------------|
| Scheduler | `./mnt/airflow-logs/scheduler/` |
| DAG runs | `./mnt/airflow-logs/dag_id/` |
| Task instances | `./mnt/airflow-logs/dag_id/task_id/` |
| Webserver | `docker logs airflow-webserver` |
| PostgreSQL | `docker logs ro-dou-postgres-1` |

### Useful Commands

```bash
# Check running containers
docker ps

# View container logs
docker logs airflow-webserver
docker logs airflow-scheduler
docker logs ro-dou-postgres-1

# Access PostgreSQL
docker exec -it ro-dou-postgres-1 psql -U airflow -d airflow

# Access Airflow CLI
docker exec airflow-webserver airflow dags list
docker exec airflow-webserver airflow tasks list my_dag_id

# Restart specific service
docker restart airflow-scheduler
docker restart airflow-webserver

# Clean up and start fresh
make down
docker volume prune
make run
```

---

## Code Modification Guidelines

### Before Making Changes

1. **Read the documentation**: Check `docs/` for context on the feature
2. **Review existing examples**: Look at similar implementations in the codebase
3. **Check tests**: Ensure you understand how the component is tested
4. **Run tests**: Establish a baseline with `make tests`

### Making Changes

#### Modifying Searchers (`src/searchers.py`)

- **Inherit from `BaseSearcher`**: All searchers must implement the abstract base class
- **Implement `search()` method**: Return `SearchResult` type (Dict[str, Dict[str, Dict[str, List[dict]]]])
- **Handle errors gracefully**: Use try/except and log errors
- **Respect configuration**: Use parameters from `SearchConfig` schema
- **Group results**: Group by term, department, and custom groups
- **Add tests**: Create corresponding test file in `tests/`

#### Modifying Schemas (`src/schemas.py`)

- **Use Pydantic v2 syntax**: `Field()`, `field_validator()`, `BaseModel`
- **Provide descriptions**: All fields should have clear Portuguese descriptions
- **Set defaults**: Use `Optional` with `default=None` or explicit defaults
- **Add validators**: Use `@field_validator` for complex validation
- **Update docs**: Regenerate YAML examples if schema changes significantly

#### Modifying DAG Generator (`src/dou_dag_generator.py`)

- **Test thoroughly**: DAG generation errors affect all configurations
- **Maintain backward compatibility**: Existing YAML files should continue to work
- **Update merge logic carefully**: `merge_results()` is critical for multi-source searches
- **Add logging**: Use Airflow's logging system for debugging
- **Consider performance**: DAG generation happens on every scheduler restart

#### Adding Notification Channels (`src/notification/`)

- **Implement `ISender` interface**: Ensures consistent API
- **Handle formatting**: Support both HTML (email) and plain text (Slack/Discord)
- **Error handling**: Catch and log webhook/SMTP errors gracefully
- **Configuration**: Add fields to `ReportConfig` schema
- **Examples**: Create example YAML in `dag_confs/examples_and_tests/`

### Testing Your Changes

1. **Run unit tests**: `make tests`
2. **Test manually**: Create a test YAML and run the DAG
3. **Check logs**: Review Airflow task logs for errors
4. **Validate schema**: Run YAML validation tests
5. **Test edge cases**: Empty results, multiple sources, large datasets

### Committing Changes

1. **Follow commit message format**:
   ```
   type(scope): brief description

   Detailed explanation if needed

   Closes #issue_number
   ```

2. **Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

3. **Scopes**: `searcher`, `notification`, `schema`, `dag-generator`, `tests`, `docs`

4. **Examples**:
   ```
   feat(searcher): add support for publication type filtering
   fix(notification): handle empty Discord webhook responses
   docs(readme): update installation instructions
   test(searcher): add tests for INLABS date filtering
   ```

### Documentation Updates

After making changes:

1. **Update CLAUDE.md**: If architecture or conventions change
2. **Update inline comments**: Keep code comments accurate
3. **Update MkDocs**: If user-facing features change (`docs/docs/`)
4. **Update CHANGELOG.md**: Follow Keep a Changelog format
5. **Update examples**: Add/modify YAML examples if needed

---

## Additional Resources

### Official Documentation

- **Ro-DOU Docs**: https://gestaogovbr.github.io/Ro-dou/
- **Airflow Docs**: https://airflow.apache.org/docs/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Docker Compose Docs**: https://docs.docker.com/compose/

### Key External APIs

- **DOU API**: Official gazette API (authentication may be required)
- **Querido Diário API**: https://docs.queridodiario.ok.org.br/
- **INLABS Portal**: https://inlabs.in.gov.br/ (requires credentials)

### Code Architecture Patterns

- **Factory Pattern**: `BaseSearcher` with concrete implementations
- **Strategy Pattern**: `ISender` with multiple notification strategies
- **Template Method**: `BaseSearcher.search()` abstract method
- **Configuration as Code**: YAML-driven DAG generation
- **XCom Communication**: Airflow task data sharing
- **Dynamic DAG Generation**: Python generates multiple DAGs from configs

### Contact & Support

- **GitHub Issues**: https://github.com/gestaogovbr/Ro-dou/issues
- **GitHub Discussions**: For questions and community support
- **Documentation**: https://gestaogovbr.github.io/Ro-dou/outros/contato/

---

## Ro-DOU Lite (Raspberry Pi)

### Overview

**Ro-DOU Lite** is a lightweight, standalone version of Ro-DOU optimized for deployment on resource-constrained devices like Raspberry Pi 3/4. It focuses exclusively on INLABS data consumption with SQLite storage and FTS5 full-text search.

**Location**: `/ro-dou-lite`

**Key Characteristics**:
- 🎯 **INLABS-only**: Consumes DOU data from INLABS portal (XML format)
- 🗄️ **SQLite + FTS5**: Fast full-text search without PostgreSQL overhead
- 🔍 **Validated Parser**: 96.8% signature extraction rate (tested on 114,000+ articles)
- 📧 **Email notifications**: SMTP-based notifications (no Slack/Discord)
- ⚙️ **No Airflow**: Simple Python scripts + cron scheduling
- 💾 **Low memory**: 150-250MB RAM usage (vs 800MB for main version)

### Architecture

```
ro-dou-lite/
├── src/                      # Core modules
│   ├── config.py             # YAML configuration management
│   ├── database.py           # SQLite + FTS5 operations
│   ├── xml_parser.py         # INLABS XML parser (validated)
│   ├── inlabs_client.py      # INLABS portal authentication/download
│   ├── searcher.py           # FTS5-based search engine
│   └── notifier.py           # Email notification sender
├── scripts/                  # Executable scripts
│   ├── download_inlabs.py    # Download all sections
│   ├── download_secao1.py    # Download Section 1 only
│   ├── download_secao2.py    # Download Section 2 only
│   ├── download_secao3.py    # Download Section 3 only
│   └── run_searches.py       # Execute searches and send notifications
├── tests/                    # Test suite (>80% coverage)
├── config.example.yaml       # Example configuration
├── requirements.txt          # Python dependencies
├── XML_FORMAT.md            # INLABS XML structure documentation
└── VALIDATION.md            # Parser validation report
```

### INLABS XML Format (Validated)

The XML parser was validated with **13,638 real articles** from INLABS. Key findings:

**Structure**:
```xml
<xml>
  <article id="..." name="..." pubName="DO2" artType="Portaria"
           pubDate="01/01/2023" artCategory="..." pdfPage="...">
    <body>
      <Identifica><![CDATA[...]]></Identifica>
      <Titulo><![CDATA[...]]></Titulo>
      <Texto><![CDATA[<p>...</p><p class="assinaPr">NAME</p>]]></Texto>
    </body>
  </article>
</xml>
```

**Key Characteristics**:
- ✅ One article per XML file (filename: `JORNAL_YYYYMMDD_ID.xml.xml`)
- ✅ Metadata in `<article>` attributes (not child elements)
- ✅ CDATA sections for all content fields
- ✅ Capitalized tags: `<Titulo>`, `<Identifica>`, `<Texto>`
- ✅ Two signature classes: `class="assinaPr"` and `class="assina"`
- ✅ Double file extension: `.xml.xml`

**Parser Validation Results** (S02012023.zip):
- Total articles parsed: 13,638 (100% success)
- Signatures extracted: 13,203 (96.8%)
- Sections: DO2 (89%), DO2E (10.5%), DO2ESP (0.3%)
- Article types: Portaria (88%), Ato (5%), Retificação (2%)

See `ro-dou-lite/VALIDATION.md` for detailed validation report.

### Configuration

**Example `config.yaml`**:
```yaml
inlabs:
  username: "your_cpf"
  password: "your_password"
  base_url: "https://inlabs.in.gov.br"

database:
  path: "data/inlabs.db"
  retention_days: 365

searches:
  - name: "LGPD Search"
    terms:
      - "lei geral de proteção de dados"
      - "LGPD"
    sections:
      - "DO2"
    notification:
      email:
        smtp_host: "smtp.gmail.com"
        smtp_port: 587
        smtp_user: "your@email.com"
        smtp_password: "your_password"
        from_addr: "your@email.com"
        to_addrs:
          - "recipient@email.com"
        subject: "Publicações DOU - LGPD"
```

### Core Modules

#### 1. **xml_parser.py** (Validated with Real Data)

**Purpose**: Parse INLABS XML files into structured dictionaries

**Key Methods**:
- `parse_file(xml_path)`: Parse single XML file → list of articles
- `parse_directory(dir_path)`: Parse all XMLs in directory
- `_parse_article(article_elem)`: Extract article from ElementTree
- `_extract_signature(html_text)`: Extract signatures from HTML (both classes)
- `_parse_date(date_str)`: Convert DD/MM/YYYY → YYYY-MM-DD

**Validation Status**: ✅ Tested with 13,638 real articles

#### 2. **database.py** (SQLite + FTS5)

**Purpose**: Store and search articles with full-text search

**Schema**:
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    name TEXT,
    pubname TEXT,
    pubdate TEXT,
    artcategory TEXT,
    arttype TEXT,
    identifica TEXT,
    titulo TEXT,
    subtitulo TEXT,
    ementa TEXT,
    texto TEXT,
    assina TEXT,
    pdfpage TEXT,
    created_at TEXT
);

CREATE VIRTUAL TABLE articles_fts USING fts5(
    titulo, subtitulo, texto, artcategory,
    content=articles,
    tokenize='porter unicode61 remove_diacritics 2'
);
```

**Performance**: FTS5 is ~10x faster than regex search

#### 3. **inlabs_client.py**

**Purpose**: Authenticate and download INLABS data

**Key Methods**:
- `authenticate()`: Login to INLABS portal
- `find_files(start_date, end_date, sections)`: Find available files
- `download_file(url, dest_path)`: Download ZIP file
- `extract_zip(zip_path, extract_dir)`: Extract and parse XMLs

#### 4. **searcher.py** (FTS5-based)

**Purpose**: Search articles using SQLite FTS5

**Query Example**:
```python
query = """
    SELECT DISTINCT a.*,
           snippet(articles_fts, 2, '<mark>', '</mark>', '...', 64) as snippet
    FROM articles a
    JOIN articles_fts fts ON a.id = fts.rowid
    WHERE fts MATCH ?
    AND a.pubdate >= ? AND a.pubdate <= ?
    ORDER BY a.pubdate DESC
"""
```

**Features**:
- Full-text search with highlighting
- Date range filtering
- Section filtering (DO1, DO2, DO3)
- Department filtering
- Signature filtering (ignore_signature_match)

#### 5. **notifier.py**

**Purpose**: Send email notifications with search results

**Features**:
- HTML email with highlighted matches
- Grouped by search term
- SMTP with TLS/SSL support
- Retry logic for failed sends

### Running Ro-DOU Lite

#### Installation

```bash
cd ro-dou-lite

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp config.example.yaml config.yaml
# Edit config.yaml with your INLABS credentials and email settings
```

#### Download INLABS Data

```bash
# Download all sections
python scripts/download_inlabs.py

# Or download specific sections
python scripts/download_secao1.py  # Section 1
python scripts/download_secao2.py  # Section 2
python scripts/download_secao3.py  # Section 3
```

#### Run Searches

```bash
# Execute searches defined in config.yaml
python scripts/run_searches.py

# Or import and use programmatically
from src.searcher import Searcher
from src.database import Database

db = Database("data/inlabs.db")
searcher = Searcher(db)

results = searcher.search(
    terms=["LGPD", "lei geral de proteção de dados"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

#### Scheduling with Cron

```bash
# Edit crontab
crontab -e

# Download daily at 6 AM
0 6 * * * cd /home/pi/ro-dou-lite && python scripts/download_secao2.py

# Search and notify at 7 AM
0 7 * * * cd /home/pi/ro-dou-lite && python scripts/run_searches.py
```

### Testing

```bash
cd ro-dou-lite

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_xml_parser.py -v
```

**Test Coverage**: >80% (all core modules tested)

### Memory Usage Comparison

| Component | Main Version | Lite Version |
|-----------|--------------|--------------|
| Base | Airflow (400MB) | Python (50MB) |
| Database | PostgreSQL (200MB) | SQLite (20MB) |
| Search | Pandas + API (100MB) | FTS5 (50MB) |
| Scheduling | Airflow (100MB) | Cron (0MB) |
| **Total** | **~800MB** | **~150MB** |

**Result**: 70% reduction in RAM usage

### Performance Benchmarks (Raspberry Pi 3)

| Operation | Time | Notes |
|-----------|------|-------|
| Parse 13,638 XMLs | ~30s | ElementTree is efficient |
| Insert to SQLite | ~10s | Batch inserts with transactions |
| FTS5 Search | <100ms | Full-text search on 100k articles |
| Email send | ~2s | Depends on SMTP server |
| Total workflow | ~1min | Download → Parse → Search → Notify |

### Differences from Main Version

| Feature | Main Version | Lite Version |
|---------|--------------|--------------|
| **Data Sources** | DOU API, QD, INLABS | INLABS only |
| **Database** | PostgreSQL 17.5 | SQLite 3 |
| **Orchestration** | Apache Airflow | Cron + Python scripts |
| **Configuration** | YAML → DAGs | YAML → Direct execution |
| **UI** | Airflow web UI | Command-line only |
| **Notifications** | Email, Slack, Discord | Email only |
| **Deployment** | Docker Compose | Native Python |
| **RAM Usage** | ~800MB | ~150MB |
| **Startup Time** | ~2 minutes | <1 second |
| **Complexity** | High (enterprise) | Low (personal use) |

### When to Use Ro-DOU Lite

**Use Ro-DOU Lite when**:
- ✅ Running on Raspberry Pi 3/4 or similar devices
- ✅ Limited to INLABS data source (DOU sections 1-3)
- ✅ Personal use or small-scale deployment
- ✅ Email notifications are sufficient
- ✅ Want simple cron-based scheduling
- ✅ Learning Python/SQLite/FTS5
- ✅ Low-power, always-on deployment

**Use Main Version when**:
- ✅ Need multiple data sources (DOU API, Querido Diário, INLABS)
- ✅ Multiple users or team deployment
- ✅ Require Slack/Discord notifications
- ✅ Need web UI for monitoring
- ✅ Complex workflow orchestration
- ✅ Enterprise/organizational use
- ✅ Server infrastructure available

### Troubleshooting Ro-DOU Lite

#### Parser Errors

**Symptom**: XMLParseError when parsing files

**Solution**:
```bash
# Validate XML structure
python -c "
from src.xml_parser import XMLParser
parser = XMLParser()
articles = parser.parse_file('path/to/file.xml.xml')
print(f'Parsed {len(articles)} articles')
"
```

#### Database Locked

**Symptom**: "database is locked" error

**Solution**: Ensure only one process writes to SQLite at a time
```python
# Use WAL mode for better concurrency
db.connection.execute("PRAGMA journal_mode=WAL")
```

#### INLABS Authentication Failed

**Symptom**: HTTP 401/403 errors

**Solution**: Verify credentials in config.yaml and check INLABS portal status

#### Low Search Performance

**Symptom**: Searches taking >1 second

**Solution**: Ensure FTS5 indexes are built
```sql
INSERT INTO articles_fts(articles_fts) VALUES('rebuild');
```

### Additional Resources

- **Ro-DOU Lite README**: `ro-dou-lite/README.md`
- **XML Format Guide**: `ro-dou-lite/XML_FORMAT.md`
- **Validation Report**: `ro-dou-lite/VALIDATION.md`
- **Test Suite**: `ro-dou-lite/tests/`

---

## Summary for AI Assistants

When working with Ro-DOU:

### General Guidelines

1. **Identify the version**: Determine if working on main version (Airflow-based) or lite version (Raspberry Pi)
2. **Always read before writing**: Check existing implementations before creating new ones
3. **Test thoroughly**: Run tests before committing (`make tests` for main, `pytest` for lite)
4. **Follow Portuguese conventions**: All user-facing text should be in Portuguese
5. **Document changes**: Update CLAUDE.md, inline comments, and version-specific docs as needed
6. **Ask when uncertain**: Review documentation and existing code patterns first

### Main Version (Airflow-based)

**Key insights**:
- Configuration-driven system: YAML → Pydantic schemas → Airflow DAGs
- Respect Airflow patterns: Use XCom, task groups, proper task dependencies
- Validate YAML schemas: Changes affect all existing configurations
- Consider backward compatibility: Existing YAML files should continue to work
- Use example files: `dag_confs/examples_and_tests/` provides working templates
- Check logs: Airflow logs are essential for debugging

**Critical files**:
- `src/dou_dag_generator.py`: DAG generation (539 lines)
- `src/searchers.py`: Search implementations (589 lines)
- `src/schemas.py`: Pydantic validation (246 lines)

### Lite Version (Raspberry Pi)

**Key insights**:
- Direct execution system: YAML → Python scripts → SQLite/Email
- XML parser validated with 13,638 real articles (96.8% signature extraction)
- SQLite FTS5 provides 10x faster search than regex
- Memory-optimized: 150MB vs 800MB (70% reduction)
- No Airflow: Use simple Python scripts + cron

**Critical files**:
- `ro-dou-lite/src/xml_parser.py`: Validated INLABS parser
- `ro-dou-lite/src/database.py`: SQLite + FTS5 implementation
- `ro-dou-lite/src/searcher.py`: FTS5-based search
- `ro-dou-lite/VALIDATION.md`: Parser validation report

**IMPORTANT**: The XML parser in ro-dou-lite uses the REAL INLABS structure:
- Metadata in `<article>` **attributes** (not child elements)
- Capitalized tags: `<Titulo>`, `<Identifica>`, `<Texto>`
- Two signature classes: `assinaPr` AND `assina`
- One article per file with `.xml.xml` extension

### Version Selection Guide

**Choose main version** when modifying:
- `/src`, `/dag_confs`, `/dag_load_inlabs` directories
- Airflow DAGs, hooks, or operators
- Multi-source data integrations (DOU API, QD, INLABS)
- Slack/Discord notification features

**Choose lite version** when modifying:
- `/ro-dou-lite` directory
- XML parsing or INLABS client
- SQLite/FTS5 search functionality
- Email-only notifications
- Raspberry Pi deployment features
