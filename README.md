# Market Analysis Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.2-blue.svg)](https://nextjs.org/)
[![Production Ready](https://img.shields.io/badge/backend-production%20ready-green.svg)](https://github.com/nelsonfrugeri-tech/market-analysis)
[![Frontend](https://img.shields.io/badge/frontend-scaffolded-orange.svg)](https://github.com/nelsonfrugeri-tech/market-analysis)

A comprehensive **Brazilian investment fund analysis platform** with multiple delivery modes. Automatically collects data from Brazilian financial regulators (CVM, BCB), analyzes performance against benchmarks, and delivers insights through CLI, REST API, and web dashboard interfaces.

## 🏗️ System Architecture

The platform provides **three delivery modes** for accessing fund analysis capabilities:

### 1. **CLI Interface** (Production Ready ✅)
Command-line tool for automated data collection, analysis, and PDF report generation with email delivery.

### 2. **REST API** (Production Ready ✅)
FastAPI-based REST service with 6 endpoints for programmatic access to fund data and metrics.

### 3. **Web Dashboard** (Scaffolded ⚠️)
Next.js frontend with React components and TypeScript types (integration in progress).

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │   REST API      │    │  Web Dashboard  │
│   (Complete)    │    │   (Complete)    │    │   (Scaffolded)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────┬───────────┼──────────────────────┘
                     │           │
            ┌─────────▼───────────▼──────────┐
            │     Service Layer              │
            │  • Data Collection             │
            │  • Performance Calculation     │
            │  • Report Generation           │
            └─────────┬──────────────────────┘
                      │
            ┌─────────▼──────────┐
            │  Infrastructure    │
            │  • SQLite Database │
            │  • CVM/BCB APIs    │
            │  • AI Explanations │
            └────────────────────┘
```

## 🎯 Key Features

### 📊 **Data Collection Pipeline**
- **CVM Integration**: Daily fund data from Brazilian Securities Commission
- **BCB Integration**: Economic indicators (SELIC, CDI, IPCA) from Central Bank
- **News Aggregation**: RSS feed integration for market context
- **AI Explanations**: 29 metric explanations via DeepSeek/Ollama integration

### 📈 **Performance Analysis Engine**
- **Comprehensive Metrics**: 45+ financial metrics across Performance, Risk, Efficiency domains
- **Benchmark Comparisons**: Fund vs SELIC, CDI, IPCA, CDB, Poupança
- **Period Analysis**: Flexible date ranges and filtering
- **Brazilian Compliance**: CVM-compliant calculations and formatting

### 🔌 **REST API (v0.2.0)**
```bash
GET    /api/v1/health                            # System health check
GET    /api/v1/funds                             # List available funds
GET    /api/v1/funds/{cnpj}/performance          # Performance metrics + benchmarks
GET    /api/v1/funds/{cnpj}/daily                # Time series data for charts
GET    /api/v1/funds/{cnpj}/explanations         # Metric explanations for tooltips
POST   /api/v1/collect                          # Trigger data collection
```

**API Documentation**: Automatic Swagger/OpenAPI at `/api/docs`

### 📄 **Reporting & Delivery**
- **PDF Generation**: Professional reports with matplotlib charts
- **Email Automation**: SMTP delivery with configurable templates
- **Web Interface**: React components for interactive dashboards (in development)

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+**
- **Node.js 18+** (for frontend development)
- **Make** (for automated commands)
- **Git**
- **macOS** (current deployment target)

### One-Command Setup
```bash
# Clone repository
git clone https://github.com/nelsonfrugeri-tech/market-analysis.git
cd market-analysis

# Complete setup (install dependencies + initialize database)
make setup

# Start development servers
make dev
```

### Manual Setup
```bash
# Install dependencies (backend + frontend)
make install

# Or install individually
make install-backend
make install-frontend
# Initialize database
make db-init

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Individual Commands
```bash
# Backend only
make install-backend
make run-backend

# Frontend only
make install-frontend
make run-frontend
```

### Configuration
Create `.env` file with required variables:

```env
# Database
MA_DB_PATH=data/market_analysis.db

# SMTP (for email reports)
MA_SMTP_HOST=smtp.gmail.com
MA_SMTP_PORT=587
MA_SMTP_USERNAME=your_email@gmail.com
MA_SMTP_PASSWORD=your_app_password
MA_SMTP_SENDER_EMAIL=your_email@gmail.com

# AI Integration (optional)
MA_OLLAMA_BASE_URL=http://localhost:11434
MA_ANTHROPIC_API_KEY=your_anthropic_key

# Logging
MA_LOG_LEVEL=INFO
```

## 🧪 Testing & Development

### Quick Testing
```bash
# Test everything (backend + frontend)
make test

# Run with coverage reports
make test-coverage

# Quick quality check (lint + test)
make check
```

### Detailed Testing

#### Backend Tests
```bash
# All backend tests with coverage
make test-backend

# API integration tests only
make test-api

# End-to-end with real CVM/BCB data
make test-e2e
```

#### Frontend Tests
```bash
# React component tests
make test-frontend

# Type checking
cd frontend && npm run type-check

# Build validation
make build-frontend
```

#### Code Quality
```bash
# Run all linters and formatters
make lint

# Python code quality
make lint-backend    # ruff + mypy

# TypeScript code quality
make lint-frontend   # Biome + tsc

# Auto-format all code
make format
```

### Validation Checklist

Before committing changes, run:
```bash
# 1. Full test suite
make test

# 2. Code quality checks
make lint

# 3. Security audit
make security-audit

# 4. Build validation
make build

# All-in-one check
make check
```

### Test Coverage

**Current Coverage:**
- **Backend**: 93% API coverage + comprehensive unit tests
- **Frontend**: 36 component tests with 100% component coverage
- **Integration**: End-to-end tests with real CVM/BCB APIs

**Coverage Reports:**
```bash
# Generate HTML coverage reports
make test-coverage

# View backend coverage
open htmlcov/index.html

# View frontend coverage
cd frontend && npm run test:coverage
```

### Database Testing
```bash
# Reset database for clean tests
make db-reset

# Seed with test data
make db-seed

# Test database connectivity
make run-backend
curl http://localhost:8000/api/v1/health
```

### Development Workflow
```bash
# 1. Start development
make dev

# 2. Make changes...

# 3. Test changes
make test

# 4. Lint and format
make lint format

# 5. Commit (if all pass)
git add . && git commit -m "feat: ..."
```

## 📋 Usage Examples

### Development Mode
```bash
# Start both backend and frontend
make dev

# Access interfaces:
# • Backend API: http://localhost:8000
# • Frontend: http://localhost:3000
# • API Docs: http://localhost:8000/api/docs
```

### CLI Interface
```bash
# Quick analysis using make
make run-cli

# Manual CLI commands
python -m market_analysis.cli --months 3 --email recipient@email.com
python -m market_analysis.cli --months 1 --output report.pdf
python -m market_analysis.cli --collect-only
```

### REST API
```bash
# Start API server
make run-backend

# Test endpoints
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/funds
curl "http://localhost:8000/api/v1/funds/26.331.064%2F0001-48/performance?months=3"

# View interactive docs
open http://localhost:8000/api/docs
```

### Web Dashboard
```bash
# Start frontend only
make run-frontend

# Or start full stack
make dev

# Access dashboard
open http://localhost:3000
```

### Production Build
```bash
# Build for production
make build

# Test production build
make build-frontend && cd frontend && npm start
```

## 🏛️ Technical Architecture

### Backend Architecture (Clean Architecture)
```
src/market_analysis/
├── api/                    # FastAPI REST interface
│   ├── main.py            # App + 6 endpoints
│   ├── models.py          # Pydantic response schemas
│   └── service.py         # Service orchestration
├── application/           # Application services
│   ├── config.py          # pydantic-settings configuration
│   ├── performance.py     # Performance calculations
│   └── retry.py           # Retry logic
├── domain/                # Business domain
│   ├── models/            # Domain models (dataclasses)
│   ├── interfaces.py      # Protocols/interfaces
│   ├── exceptions.py      # Exception hierarchy
│   └── schemas.py         # Domain schemas
├── infrastructure/        # External integrations
│   ├── cvm_collector.py   # CVM API integration
│   ├── benchmarks/        # BCB rates collection
│   ├── database/          # SQLite repositories
│   ├── pdf_generator.py   # ReportLab PDF generation
│   └── email_sender.py    # SMTP delivery
├── ai/                    # AI/LLM integration
│   ├── explainer.py       # Metric explanations
│   ├── clients/           # LLM clients (Anthropic, Ollama)
│   └── templates/         # Prompt templates
└── cli.py                 # Command-line interface
```

### Frontend Architecture (Next.js App Router)
```
frontend/src/
├── app/                   # Next.js App Router
│   └── page.tsx          # Main dashboard page (scaffolded)
├── components/
│   ├── ui/               # Reusable UI components
│   │   ├── metric-card.tsx      # Financial metrics display
│   │   └── metrics-section.tsx  # Collapsible sections
│   └── metrics/          # Domain-specific components
│       └── performance-section.tsx  # Performance metrics
├── types/                # TypeScript definitions
│   ├── api.ts           # API contract types
│   └── components.ts    # Component prop types
├── lib/                 # Utility libraries
│   ├── utils.ts         # General utilities
│   ├── formatters.ts    # Brazilian number/currency formatting
│   └── mock-data.ts     # Development mock data
└── test/                # Component tests (Vitest)
```

### Database Schema
**SQLite** with 8 tables for comprehensive fund analysis:
- `funds_metadata` - Fund registration information
- `daily_data` - Daily NAV and performance data
- `bcb_data` - Economic benchmark indicators
- `news_data` - Market news and context
- `performance_metrics` - Calculated performance indicators
- `fund_benchmarks` - Benchmark comparison results
- `fund_performance` - Historical performance analysis
- `analysis_reports` - Generated report metadata

## 🧪 Testing & Quality

### Backend Tests
```bash
# Run all tests
python -m pytest tests/

# API tests (21 tests covering all endpoints)
python -m pytest tests/test_api.py

# Integration tests
python -m pytest tests/integration/

# End-to-end with real data
python test_end_to_end.py --email your@email.com
```

### Frontend Tests
```bash
# Component tests
cd frontend
npm test

# Coverage report
npm run test:coverage
```

### Test Coverage
- **Backend**: 93% API coverage, comprehensive unit and integration tests
- **Frontend**: 36 component tests with 100% component coverage
- **E2E**: Real API validation with live CVM/BCB data

## 📊 Current State (v0.2.0)

### ✅ **Production Ready**
- **CLI Interface**: Complete fund analysis pipeline with PDF reports
- **REST API**: 6 endpoints with comprehensive testing and documentation
- **Data Collection**: Automated CVM/BCB integration with error handling
- **Database**: Robust SQLite schema with WAL mode for concurrency

### ⚠️ **Development State**
- **Web Dashboard**: Components scaffolded but main page not implemented
- **API Integration**: Frontend-backend integration layer in progress
- **Type Alignment**: Frontend types need alignment with actual API schemas

### 🔧 **Known Issues**
- **Frontend Build**: Missing utility module imports prevent compilation
- **Type Contracts**: API response types don't match frontend expectations
- **Integration**: No fetch layer or React Query hooks implemented yet

## 🗺️ Roadmap

### v0.2.1 (In Progress) - Frontend Integration
- ✅ **Dependency Security**: Exact version pinning for supply chain protection
- 🚧 **API Integration**: React Query hooks and fetch layer implementation
- 🚧 **Type Alignment**: Sync frontend types with backend schemas
- 🚧 **Dashboard Pages**: Implement main dashboard and fund detail pages

### v0.3.0 (Planned) - Enhanced Analytics
- **Multi-Fund Support**: Analyze and compare multiple funds
- **Advanced Metrics**: Risk-adjusted returns, Sharpe ratios, drawdown analysis
- **Portfolio Analysis**: Multi-fund portfolio performance tracking
- **Historical Trends**: Long-term performance visualization

### v0.4.0 (Future) - Platform Features
- **Authentication**: User accounts and fund watchlists
- **Real-time Updates**: WebSocket integration for live data
- **Custom Benchmarks**: User-defined comparison benchmarks
- **Export Features**: Excel, CSV, and advanced PDF exports

## 🔧 Development

### Tech Stack

**Backend:**
- **Python 3.12+**: Core runtime with modern async/await
- **FastAPI 0.135**: REST API framework with automatic docs
- **Pydantic 2.12**: Data validation and serialization
- **SQLite + aiosqlite**: Database with async access
- **ReportLab**: Professional PDF generation
- **structlog**: Structured logging
- **httpx**: Async HTTP client for external APIs

**Frontend:**
- **Next.js 16.2**: React framework with App Router
- **React 19.2**: Latest React with new features
- **TypeScript 5.7**: Strict type checking
- **Tailwind CSS 4.2**: Utility-first styling
- **TanStack Query**: Data fetching and caching
- **Vitest**: Modern testing framework

### Development Workflow
1. **Feature Branch**: Branch from main for new features
2. **Testing**: Write tests for backend changes, component tests for frontend
3. **Quality**: Run linting (ruff/biome) and type checking (mypy/tsc)
4. **Pull Request**: Open PR with comprehensive description
5. **Code Review**: Team review with focus on architecture and testing
6. **Integration**: Merge after all checks pass

### Development Automation

All development tasks are automated via **Makefile**:
```bash
# See all available commands
make help

# Common development tasks
make setup          # Complete project setup
make dev            # Start development servers
make test           # Run all tests
make lint           # Code quality checks
make clean          # Clean build artifacts
```

### Environment Setup
```bash
# Automated setup (recommended)
make setup

# Manual setup
pip install -e ".[dev]"
cd frontend && npm install

# Development workflow
make dev            # Start servers
make test           # Run tests
make lint format    # Quality checks
```

## 🤝 Contributing

### Code Standards
- **Python**: Type hints, docstrings, async/await patterns
- **TypeScript**: Strict mode, comprehensive type definitions
- **Testing**: Unit tests for new features, integration tests for APIs
- **Documentation**: Update README and API docs for user-facing changes

### Team
- **Mr. Robot**: System Architecture & REST API Infrastructure
- **Elliot Alderson**: Backend Implementation & Data Collection Systems
- **Tyrell Wellick**: Frontend Development & Business Logic

## 📄 License & Data Sources

### Data Providers
- **CVM** (Comissão de Valores Mobiliários): Brazilian Securities Commission
- **BCB** (Banco Central do Brasil): Central Bank of Brazil economic indicators
- **RSS Feeds**: Market news aggregation

### External APIs
- **Ollama**: Local LLM for metric explanations
- **Anthropic Claude**: Alternative AI explanation provider

---

**📚 Documentation**
- [API Reference](http://localhost:8000/api/docs) - Interactive Swagger documentation
- [Changelog](CHANGELOG.md) - Version history and feature additions
- [Database Schema](docs/database-schema.md) - Complete schema documentation

**🔗 Links**
- [Repository](https://github.com/nelsonfrugeri-tech/market-analysis)
- [Issues](https://github.com/nelsonfrugeri-tech/market-analysis/issues)
- [Releases](https://github.com/nelsonfrugeri-tech/market-analysis/releases)

**📧 Support**
For questions, feature requests, or bug reports, please open an issue in the GitHub repository.