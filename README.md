# Market Analysis System

**Automated fund analysis system for Nu Reserva Planejada with daily performance reports, benchmark comparisons, and market insights.**

## 🎯 Overview

This system automates the collection and analysis of fund performance data, providing daily reports with:
- **Real fund data** from CVM (Brazilian Securities Commission)
- **Official benchmarks** from BCB (Central Bank of Brazil): SELIC, CDI, IPCA
- **Market news** from Google News RSS
- **Professional PDF reports** with charts and KPIs
- **Email delivery** for automated distribution

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Gmail account (for SMTP)
- Internet connection for data collection

### Installation

1. **Clone and setup**
```bash
git clone https://github.com/nelsonfrugeri-tech/market-analysis.git
cd market-analysis
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your Gmail credentials
```

3. **Run analysis**
```bash
python -m market_analysis.cli --months 3 --output my_report.pdf
```

## 🏗 Architecture

### Data Pipeline
```
CVM API → Fund Daily Data → Performance Engine
BCB API → Benchmark Rates ↗     ↓
Google News → Market Context     PDF Report → Email
```

### Key Components
- **Collectors**: CVM, BCB, News data fetching
- **Performance Engine**: Return calculations, volatility, benchmark comparison
- **PDF Generator**: Professional reports with ReportLab + Matplotlib
- **Domain Models**: Pydantic v2 validation, frozen dataclasses
- **CLI Interface**: argparse with flexible parameters

## 📊 What Gets Analyzed

**Fund Performance:**
- Daily NAV evolution and returns
- Volatility (annualized standard deviation)
- Trend analysis (30-day window)
- Equity and shareholders tracking

**Benchmark Comparison:**
- vs SELIC (official interest rate)
- vs CDI (interbank rate)
- vs IPCA (inflation index)
- Outperformance calculations

**Market Context:**
- Recent news about Nubank and fund performance
- Market sentiment indicators

## 🚀 Usage Examples

**Basic analysis (3 months)**
```bash
python -m market_analysis.cli
```

**Extended analysis with custom output**
```bash
python -m market_analysis.cli --months 6 --output detailed_report.pdf
```

**Quick analysis without news**
```bash
python -m market_analysis.cli --months 1 --no-news
```

**Verbose output for debugging**
```bash
python -m market_analysis.cli --verbose
```

## 📁 Project Structure

```
market-analysis/
├── src/market_analysis/          # Main application code
│   ├── cli.py                   # Command-line interface
│   ├── application/             # Business logic
│   │   ├── config.py           # Pydantic settings
│   │   └── performance.py      # Performance calculations
│   ├── domain/                 # Domain models and interfaces
│   │   ├── models/             # Pydantic/dataclass models
│   │   └── interfaces.py       # Protocol definitions
│   └── infrastructure/         # External integrations
│       ├── cvm_collector.py    # CVM API integration
│       ├── benchmark_fetcher.py # BCB API integration
│       ├── news_fetcher.py     # Google News RSS
│       └── pdf_generator.py    # PDF report generation
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
└── reports/                    # Generated reports (gitignored)
```

## ⚙ Configuration

Key environment variables in `.env`:

```bash
# SMTP Configuration
MA_SMTP_HOST=smtp.gmail.com
MA_SMTP_PORT=587
MA_SMTP_USERNAME=your.email@gmail.com
MA_SMTP_PASSWORD=your_app_password
MA_SMTP_SENDER_EMAIL=your.email@gmail.com

# Fund Configuration
MA_FUND_CNPJ=43.121.002/0001-41

# Database
MA_DB_PATH=data/market_analysis.db
```

## 🧪 Testing

**Run all tests**
```bash
pytest tests/
```

**Integration tests**
```bash
pytest tests/integration/
```

**End-to-end validation**
```bash
python scripts/validate.py
```

## 📈 Current Status: v0.1.0

**✅ Implemented:**
- CVM data collection (daily fund records)
- BCB benchmark fetching (SELIC, CDI, IPCA)
- Google News collection
- Performance calculation engine
- PDF report generation with charts
- CLI interface with flexible parameters
- Comprehensive test suite (91-98% coverage)
- End-to-end validation

**🔄 In Progress:**
- Email automation (SMTP implementation)
- SQLite persistence (repository implementations)
- Scheduled execution (APScheduler integration)

## 🛣 Roadmap

### v0.2.0 - Complete MVP
- [ ] SMTP email sender implementation
- [ ] SQLite repository implementations
- [ ] APScheduler integration
- [ ] Local cron/scheduling setup

### v0.3.0 - Production Ready
- [ ] Docker containerization
- [ ] Structured logging (structlog)
- [ ] Health check endpoints
- [ ] Performance optimizations
- [ ] Multi-fund support

### v0.4.0 - Advanced Analytics
- [ ] Historical trend analysis
- [ ] Anomaly detection and alerts
- [ ] Mobile-responsive reports
- [ ] Multiple time window analysis

## 🤝 Contributing

**Development Workflow:**
1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests for new functionality
3. Implement changes with proper type hints
4. Run test suite: `pytest`
5. Open Pull Request (never push directly to main)

**Code Standards:**
- Python 3.11+ with type hints
- Pydantic v2 for validation
- Frozen dataclasses for immutability
- Protocol-based interfaces
- Comprehensive test coverage

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Links

- **GitHub**: https://github.com/nelsonfrugeri-tech/market-analysis
- **Documentation**: `/docs` folder
- **Change Log**: [CHANGELOG.md](CHANGELOG.md)

---

**Built with ❤️ for automated investment analysis**