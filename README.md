# Brazilian Investment Fund Analysis System

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-green.svg)](https://github.com/nelsonfrugeri-tech/market-analysis/releases/tag/v0.1.0)
[![Local Execution](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A comprehensive fund analysis system designed for **Brazilian investment fund** analysis. The system automatically collects data from Brazilian financial regulators (CVM, BCB), analyzes performance against benchmarks, and generates professional PDF reports with automated email delivery.

## 🎯 Key Features

### 📊 **Data Collection Pipeline**
- **CVM Integration**: Automated download and processing of daily fund data from Brazilian Securities Commission
- **BCB Integration**: Real-time collection of economic indicators (SELIC, CDI, IPCA) from Central Bank of Brazil
- **News Aggregation**: Google RSS feed integration for fund-related news and market updates

### 📈 **Performance Analysis Engine**
- **Benchmark Comparison**: Fund performance vs SELIC, CDI, and IPCA benchmarks
- **Period Analysis**: Configurable analysis periods (1, 3, 6 months)
- **Performance Metrics**: Detailed return calculations and performance attribution

### 📄 **Professional Reporting**
- **PDF Generation**: Professional reports with charts and performance visualizations
- **Email Automation**: Automated delivery via Gmail SMTP integration
- **Rich Visualizations**: matplotlib-powered charts and data presentations

### 🔧 **Technical Architecture**
- **SQLite Database**: WAL mode for concurrent access with 8-table schema
- **Protocol-Based Design**: Structural typing with Python Protocols
- **Async Processing**: Modern async/await patterns for optimal performance
- **Pydantic v2**: Advanced data validation and serialization

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+**
- **Node.js 18+** (for frontend development)
- **Make** (for automated commands)
- **macOS** (current deployment target)

### One-Command Setup
```bash
# Clone the repository
git clone https://github.com/nelsonfrugeri-tech/market-analysis.git
cd market-analysis

# Complete setup (install dependencies + initialize database)
make setup

# Start development servers
make dev
```

### Manual Installation
```bash
# Install all dependencies
make install

# Or install individually
make install-backend
make install-frontend

# Initialize database
make db-init

# Configure environment
cp .env.example .env
# Edit .env with your Gmail credentials
```

### Configuration
Create a `.env` file with the following variables:
```env
# SMTP Configuration for Email Delivery
MA_SMTP_USERNAME=<your_gmail_address>
MA_SMTP_PASSWORD=<your_gmail_app_password>
MA_SMTP_SENDER_EMAIL=<your_gmail_address>
MA_SMTP_HOST=smtp.gmail.com
MA_SMTP_PORT=587
```

> **⚠️ Important**: Replace the placeholder values above with your actual Gmail credentials. Use Gmail App Passwords for authentication.

## 🧪 Testing & Development

### Quick Testing
```bash
# Test everything (backend + frontend)
make test

# Run with coverage reports
make test-backend

# Quality check (lint + format)
make lint format
```

### Development Workflow
```bash
# Start development servers
make dev
# Access: Backend (http://localhost:8000) + Frontend (http://localhost:3000)

# Make changes, then test
make test

# Check code quality
make lint

# Format code
make format
```

### Available Commands
```bash
make help              # Show all available commands
make setup             # Complete project setup
make test              # Run all tests
make test-backend      # Python tests with coverage
make test-frontend     # React component tests
make lint              # Code quality checks
make run-backend       # Start FastAPI server
make run-frontend      # Start Next.js dev server
make db-init           # Initialize database
make clean             # Clean build artifacts
make status            # Project status check
```

### Usage
```bash
# Run complete analysis with 3-month period
python -m market_analysis.cli --months 3 --email recipient@email.com

# Generate PDF only (no email)
python -m market_analysis.cli --months 1 --output report.pdf

# Run end-to-end test
python test_end_to_end.py --email test@email.com
```

## 📋 System Architecture

### Database Schema
The system uses SQLite with the following 8-table structure:
- `funds_metadata` - Fund registration and basic information
- `daily_data` - Daily fund performance data from CVM
- `bcb_data` - Economic indicators from Central Bank
- `news_data` - Aggregated news and market updates
- `performance_metrics` - Calculated performance indicators
- `fund_benchmarks` - Benchmark comparison data
- `fund_performance` - Historical performance analysis
- `analysis_reports` - Generated report metadata

### Data Flow
```
CVM API → SQLite ↘
BCB API → SQLite → Analysis Engine → PDF Generator → Email Delivery
News RSS → SQLite ↗
```

## 🧪 Testing & Quality

### Test Suite
- **End-to-End Testing**: Real API validation with live data
- **Integration Testing**: Database and external service integration
- **Unit Testing**: Individual component validation

### Run Tests
```bash
# End-to-end test with real data
python test_end_to_end.py --email your@email.com

# System validation
python validate_system.py

# Schema integration test
python test_schema_integration.py
```

## 📊 Current Scope

### Target Fund Configuration
- **Configurable Fund Analysis**: System supports any Brazilian investment fund via CNPJ
- **Current Example**: Nu Reserva Planejada (CNPJ: 43.121.002/0001-41)
- **Fund Types**: Optimized for fixed-income and conservative investment funds

### Benchmarks
- **SELIC**: Brazilian central bank rate
- **CDI**: Interbank deposit rate
- **IPCA**: Brazilian inflation index

### Data Sources
- **CVM** (Brazilian Securities Commission): Daily fund data
- **BCB** (Central Bank of Brazil): Economic indicators
- **Google News RSS**: Market news and updates

## 🗺️ Roadmap

### v0.1.0 (Current) - ✅ Production Ready
- Complete local execution system
- CVM/BCB/News data collection
- PDF reporting with email delivery
- End-to-end testing suite

### v0.2.0 (Planned) - 🚧 Automation
- GitHub Actions integration
- Scheduled daily execution (9 AM Brazil time)
- Enhanced error handling and monitoring
- Improved local execution setup

### v0.3.0 (Future) - 📈 Enhanced Analytics
- Multi-fund support
- Advanced performance metrics
- Risk analysis and attribution
- Historical trend analysis

### v0.4.0 (Future) - 🌐 Platform Expansion
- Web dashboard interface
- Real-time data updates
- Portfolio-level analysis
- Custom benchmark creation

## 🔧 Development

### Project Structure
```
market-analysis/
├── src/market_analysis/           # Main package
│   ├── domain/                    # Business logic & models
│   ├── infrastructure/            # External integrations
│   ├── collectors/               # Data collection services
│   └── reports/                  # PDF generation
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
└── reports/                      # Generated reports
```

### Tech Stack
- **Python 3.12+**: Core runtime
- **SQLite**: Data persistence with WAL mode
- **Pydantic v2**: Data validation and serialization
- **ReportLab**: PDF generation
- **matplotlib**: Chart generation
- **aiohttp/requests**: HTTP clients for API integration
- **feedparser**: RSS feed processing

### Development Workflow
1. **Feature Branch**: Create feature branch from main
2. **Development**: Implement changes with tests
3. **Pull Request**: Open PR for code review
4. **Testing**: Run end-to-end validation
5. **Merge**: Merge to main after approval

## 📈 Performance & Scalability

### Current Performance
- **Data Processing**: 57+ daily records in <10 seconds
- **API Efficiency**: Concurrent collection from multiple sources
- **Memory Usage**: Optimized for large dataset processing
- **PDF Generation**: 118KB+ reports with charts in <5 seconds

### Scalability Considerations
- **Database**: SQLite WAL mode for concurrent access
- **API Limits**: Respectful rate limiting for external APIs
- **Memory Management**: Streaming processing for large datasets
- **Error Handling**: Exponential backoff and retry logic

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/market-analysis.git

# Install development dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/

# Run linting
python -m flake8 src/
```

### Code Standards
- **Python 3.12+** features and syntax
- **Type hints** for all public APIs
- **Docstrings** following Google style
- **Test coverage** for new features
- **Error handling** with proper logging

## 📄 License & Acknowledgments

### Team
- **Mr. Robot**: Architecture & Infrastructure
- **Elliot Alderson**: Implementation & Data Collection
- **Tyrell Wellick**: Business Logic & PDF Generation

### Data Sources
- **CVM** (Comissão de Valores Mobiliários): Brazilian Securities Commission
- **BCB** (Banco Central do Brasil): Central Bank of Brazil
- **Google News**: Market news and updates

---

**🔗 Links**
- [Repository](https://github.com/nelsonfrugeri-tech/market-analysis)
- [Releases](https://github.com/nelsonfrugeri-tech/market-analysis/releases)
- [Issues](https://github.com/nelsonfrugeri-tech/market-analysis/issues)
- [Changelog](CHANGELOG.md)

**📧 Contact**
For questions or support, please open an issue in the GitHub repository.