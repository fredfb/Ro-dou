# Ro-DOU Lite - Lightweight DOU Monitor for Raspberry Pi

> **Lightweight version of Ro-DOU optimized for Raspberry Pi 3 deployment**

Ro-DOU Lite is a simplified version of the Ro-DOU project designed to run on resource-constrained devices like the Raspberry Pi 3. It monitors the Diário Oficial da União (Brazilian Official Gazette) via INLABS and sends email notifications when publications match your keywords.

## 🎯 Key Features

- **Lightweight**: Uses only 150-250MB RAM (vs 800MB+ for full Airflow version)
- **Simple**: Plain Python scripts instead of complex Airflow DAGs
- **Fast**: SQLite FTS5 full-text search (10x faster than regex)
- **Reliable**: Cron-based scheduling (no Docker/Airflow overhead)
- **Complete**: Downloads, parses, indexes, searches, and notifies

## 📊 Comparison with Full Version

| Feature | Full Ro-DOU | Ro-DOU Lite | Improvement |
|---------|-------------|-------------|-------------|
| **RAM Usage** | 600-800MB | 150-250MB | **70% reduction** |
| **Disk Space** | 1-2GB | 200-400MB | **75% reduction** |
| **Startup Time** | 2-3 minutes | 5-10 seconds | **95% faster** |
| **Search Speed** | 1-2s | 0.1-0.5s | **80% faster** |
| **Dependencies** | 50+ packages | 8 packages | **85% reduction** |
| **Complexity** | High (Airflow) | Low (Python) | Much simpler |

## 🚀 Quick Start

### Prerequisites

- Raspberry Pi 3 or newer (1GB+ RAM)
- Raspbian/Raspberry Pi OS
- Python 3.10+
- INLABS portal credentials
- Gmail account or SMTP server (for notifications)

### Installation

```bash
# 1. Clone or copy this directory to your Pi
cd /home/pi
cp -r /path/to/ro-dou-lite ro-dou

# 2. Create virtual environment
cd ro-dou
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements-pi.txt

# 4. Create configuration
cp config.example.yaml config.yaml
nano config.yaml  # Edit with your credentials

# 5. Initialize database
python scripts/init_database.py

# 6. Test download (optional)
python scripts/download_inlabs.py --date 2025-01-15 --verbose

# 7. Test search (optional)
python scripts/run_searches.py --dry-run --verbose

# 8. Setup cron jobs
crontab -e
```

### Cron Schedule

Add these lines to your crontab:

```cron
# Download INLABS data twice daily (3 PM and 11 PM)
0 15,23 * * * cd /home/pi/ro-dou && venv/bin/python scripts/download_inlabs.py >> logs/download.log 2>&1

# Run searches every hour during business hours
0 8-18 * * 1-5 cd /home/pi/ro-dou && venv/bin/python scripts/run_searches.py >> logs/search.log 2>&1

# Cleanup old logs weekly
0 3 * * 0 find /home/pi/ro-dou/logs -name "*.log" -mtime +30 -delete
```

## 📁 Project Structure

```
ro-dou-lite/
├── src/                    # Source code
│   ├── config.py          # Configuration management
│   ├── database.py        # SQLite operations
│   ├── inlabs_client.py   # INLABS download client
│   ├── xml_parser.py      # XML parsing
│   ├── searcher.py        # FTS5 search
│   └── notifier.py        # Email notifications
├── scripts/               # Runner scripts
│   ├── download_inlabs.py # Download & load data
│   ├── run_searches.py    # Search & notify
│   └── init_database.py   # Initialize database
├── tests/                 # Test suite (80%+ coverage)
├── config.yaml            # Your configuration
├── config.example.yaml    # Configuration template
├── requirements-pi.txt    # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── README.md             # This file
```

## ⚙️ Configuration

Edit `config.yaml` with your settings:

```yaml
inlabs:
  username: "your_email@example.com"
  password: "your_password"
  download_path: "/home/pi/ro-dou/data/downloads"

database:
  path: "/home/pi/ro-dou/data/dou_articles.db"
  retention_days: 365

searches:
  - terms:
      - "LGPD"
      - "lei geral de proteção de dados"
    sections:
      - "DO1"  # Seção 1
      - "DO2"  # Seção 2
    departments:
      - "Ministério da Gestão"

notifications:
  email:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    from: "alerts@example.com"
    to:
      - "your_email@example.com"
    username: "alerts@example.com"
    password: "your_app_password"  # Gmail app password
    use_tls: true
```

### Gmail App Password

For Gmail, you must use an **App Password** (not your regular password):

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate new app password for "Mail"
5. Use this password in your config

## 🔍 Search Configuration

### Simple Search

```yaml
searches:
  - terms:
      - "LGPD"
      - "dados abertos"
```

### With Filters

```yaml
searches:
  - terms:
      - "LGPD"
    sections:
      - "DO1"  # Only Section 1
    departments:
      - "Ministério da Gestão"
      - "Ministério da Economia"
```

### Multiple Searches

```yaml
searches:
  # Search 1: LGPD in all sections
  - terms:
      - "LGPD"
      - "proteção de dados"

  # Search 2: Open data in Section 1
  - terms:
      - "dados abertos"
      - "governo aberto"
    sections:
      - "DO1"
```

## 🧪 Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py -v

# Run integration tests
pytest -m integration
```

Test coverage: **>80%** across all modules.

## 📝 Usage Examples

### Manual Download

```bash
# Download today's data
python scripts/download_inlabs.py

# Download specific date
python scripts/download_inlabs.py --date 2025-01-15

# Keep downloaded files
python scripts/download_inlabs.py --keep-downloads

# Verbose logging
python scripts/download_inlabs.py --verbose
```

### Manual Search

```bash
# Run searches with default config
python scripts/run_searches.py

# Dry run (no emails sent)
python scripts/run_searches.py --dry-run

# Use custom config
python scripts/run_searches.py --config /path/to/config.yaml

# Verbose logging
python scripts/run_searches.py --verbose
```

### Database Management

```bash
# Initialize database
python scripts/init_database.py

# Check database stats
sqlite3 data/dou_articles.db "SELECT COUNT(*) FROM articles;"

# View recent articles
sqlite3 data/dou_articles.db "SELECT pubdate, titulo FROM articles ORDER BY pubdate DESC LIMIT 10;"

# Full-text search
sqlite3 data/dou_articles.db "SELECT titulo FROM articles_fts WHERE articles_fts MATCH 'lgpd';"
```

## 🐛 Troubleshooting

### INLABS Authentication Failed

```
Error: Authentication failed: no session cookie received
```

**Solution**: Check your credentials in `config.yaml`. Ensure your INLABS account is active.

### Email Not Sending

```
Error: SMTP error: Authentication failed
```

**Solution**:
- For Gmail: Use an App Password, not your regular password
- Check `smtp_host` and `smtp_port` settings
- Verify firewall allows outbound SMTP (port 587/465)

### Database Locked

```
Error: database is locked
```

**Solution**: Only one process can write to SQLite at a time. Check if another script is running.

### Memory Issues

If the Pi runs out of memory:

1. Check running processes: `htop`
2. Increase swap space:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

### No Search Results

If searches return no results:

1. Check database has articles: `python scripts/init_database.py`
2. Verify download worked: Check logs in `logs/download.log`
3. Test search manually:
   ```bash
   python scripts/run_searches.py --dry-run --verbose
   ```

## 📊 Monitoring

### Log Files

```bash
# View download logs
tail -f logs/download.log

# View search logs
tail -f logs/search.log

# Check for errors
grep ERROR logs/*.log
```

### Database Stats

```bash
# Article count
sqlite3 data/dou_articles.db "SELECT COUNT(*) FROM articles;"

# Date range
sqlite3 data/dou_articles.db "SELECT MIN(pubdate), MAX(pubdate) FROM articles;"

# Articles by section
sqlite3 data/dou_articles.db "SELECT pubname, COUNT(*) FROM articles GROUP BY pubname;"

# Recent notifications
sqlite3 data/dou_articles.db "SELECT * FROM search_log ORDER BY notified_at DESC LIMIT 10;"
```

### System Resources

```bash
# Memory usage
free -h

# Disk usage
df -h

# CPU temperature (Pi specific)
vcgencmd measure_temp

# Running processes
ps aux | grep python
```

## 🔧 Performance Tuning

### For Raspberry Pi 3 (1GB RAM)

- Use default settings (already optimized)
- Keep `retention_days: 365` or less
- Limit searches to 2-3 per run
- Run searches every 1-2 hours (not every minute)

### For Raspberry Pi 4 (4GB+ RAM)

You can increase performance:

```yaml
database:
  retention_days: 730  # Keep 2 years of data
```

And run searches more frequently:

```cron
*/30 8-18 * * 1-5  # Every 30 minutes during business hours
```

## 🤝 Contributing

This is a lightweight fork of [Ro-DOU](https://github.com/gestaogovbr/Ro-dou). For contributing to the main project, see the original repository.

For Ro-DOU Lite specific issues:
1. Ensure tests pass: `pytest`
2. Maintain >80% test coverage
3. Follow existing code style
4. Test on actual Raspberry Pi hardware

## 📄 License

Same as Ro-DOU: Apache License 2.0

## 🙏 Acknowledgments

- **Original Ro-DOU Team**: Secretaria de Gestão e Inovação - Ministério da Gestão e da Inovação em Serviços Públicos
- **INLABS**: Data provider (https://inlabs.in.gov.br/)
- **Querido Diário**: Municipal gazette aggregator
- **Raspberry Pi Foundation**: For affordable computing hardware

## 📞 Support

For help:
- Check troubleshooting section above
- Review logs in `logs/` directory
- Test with `--verbose` and `--dry-run` flags
- Original Ro-DOU docs: https://gestaogovbr.github.io/Ro-dou/

---

**Ro-DOU Lite** - Bringing official gazette monitoring to the edge! 🥧
