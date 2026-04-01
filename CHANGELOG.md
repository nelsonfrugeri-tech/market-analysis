# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-04-01

### Added

#### Development Automation & Testing
- **Comprehensive Makefile** - 30+ automated development commands covering complete workflow
- **One-command setup** - `make setup` installs dependencies and initializes database automatically
- **Development workflow automation** - `make dev` starts both backend and frontend servers
- **Complete test suite automation** - `make test` runs all backend and frontend tests with coverage
- **Code quality automation** - `make lint` and `make format` for consistent code standards
- **Virtual environment management** - Automatic `.venv` creation and management with Python 3.12
- **Database automation** - `make db-init` and `make db-reset` for database lifecycle management
- **Project status monitoring** - `make status` provides comprehensive project health overview

#### Developer Experience Enhancement
- **Updated README documentation** - Added comprehensive Testing & Development section
- **Command reference guide** - Complete documentation of all available make commands
- **Quick start workflow** - Streamlined setup process from clone to running in 2 commands
- **Development server automation** - Parallel backend/frontend startup with proper port management
- **Build artifact management** - `make clean` removes all temporary files and caches

### Improved
- **Project setup workflow** - Reduced from multiple manual steps to single `make setup` command
- **Testing workflow** - Unified command for running complete test suite with coverage reports
- **Development experience** - Simplified daily development workflow with consistent automation

### Developer Benefits
- **Time savings** - Setup time reduced from ~10 minutes to ~2 minutes
- **Consistency** - Standardized development environment across team members
- **Error reduction** - Automated workflows prevent common setup and configuration mistakes
- **Documentation** - Self-documenting commands with `make help` showing all options

## [0.3.0] - 2026-04-01

### Added

#### AI-Powered Fund Analysis (DeepSeek/Ollama Integration)
- **3 new REST API endpoints** for intelligent investment analysis:
  - `POST /api/v1/funds/{cnpj}/analysis` - Complete LLM-powered analysis (performance, risk, recommendation)
  - `GET /api/v1/funds/{cnpj}/insights` - Historical insights with latest analysis
  - `POST /api/v1/analysis/batch` - Batch analysis for up to 10 funds
- **LLM Fallback Chain**: DeepSeek:6.7b -> Qwen3:4b -> Anthropic -> Static analysis
- **3 Analysis Types**: Performance analysis, Risk analysis, Personalized recommendations
- **Structured JSON responses** with confidence scores and metadata
- **Graceful degradation** when LLM providers are unavailable (static fallback)
- **Response caching** via file-based cache to avoid redundant LLM calls
- **Async processing** for non-blocking LLM calls
- **Pydantic models** for all analysis request/response schemas
- **31 new tests** with 95% coverage on analysis modules
- **Regression tests** ensuring all v0.2.0 endpoints remain functional

#### Architecture
- **AnalysisService** - Orchestrates LLM calls with configurable client chain
- **AnalysisRouter** - FastAPI APIRouter for clean endpoint separation
- **Analysis Models** - Complete Pydantic v2 models for analysis types, responses, and batch operations
## [0.2.1] - 2026-04-01

### Security
- **Exact dependency pinning** - All frontend dependencies converted from range versions (`^`) to exact versions
- **Supply chain protection** - Prevents automatic updates that could introduce vulnerabilities
- **24 dependencies secured** - All `package.json` deps now use exact version pinning (e.g., `@tanstack/react-query: "5.96.0"` instead of `"^5.96.1"`)
- **Zero npm audit vulnerabilities** - Clean security scan after exact pinning implementation
- **Reproducible builds** - Exact versions ensure identical builds across environments

### Fixed
- **Dependency security regression** - Restored exact pinning that was lost during v0.2.0 merge conflicts
- **Range version vulnerabilities** - Eliminated potential for silent breaking changes via `^` version specifiers

## [0.2.0] - 2026-04-01

### Added

#### Backend REST API (FastAPI) - COMPLETE ✅
- **6 REST endpoints** fully implemented and tested:
  - `GET /api/v1/funds` - List available funds
  - `GET /api/v1/funds/{cnpj}/performance` - Fund performance with dynamic filters
  - `GET /api/v1/funds/{cnpj}/daily` - Daily time series data for charts
  - `GET /api/v1/funds/{cnpj}/explanations` - Metric explanations for UI tooltips
  - `GET /api/v1/health` - Health check with database status
  - `POST /api/v1/collect` - Trigger data collection from CVM/BCB
- **FastAPI Framework** with automatic Swagger/OpenAPI documentation at `/api/docs`
- **Pydantic models** for type-safe request/response validation (no `Dict[str, Any]`)
- **CORS middleware** configured for localhost:3000 frontend
- **Async/sync integration** with existing CLI backend using `asyncio.to_thread()`
- **Dynamic query parameters** for filtering and date range selection
- **Error handling** for missing data and collection failures
- **597 lines of API tests** covering all endpoints with 93% coverage
- **Clean Architecture** with layered separation: API → Service → Domain → Infrastructure

#### Frontend Web Dashboard - SCAFFOLDED ⚠️
- **Next.js 16.2.2 + React 19.2.4** framework setup
- **TypeScript strict mode** with comprehensive type definitions
- **Tailwind CSS v4 + shadcn/ui** styling system configured
- **Brazilian formatters** (pt-BR locale) for currency, percentages, and numbers
- **WCAG 2.2 accessibility** considerations in component design

#### Core Components Delivered
- **MetricCard** - Financial metrics display component with tooltips, trend indicators
- **MetricsSection** - Collapsible sections container with accessibility attributes
- **PerformanceSection** - Performance metrics composition component
- **36 unit tests** for components with Vitest + Testing Library
- **Utility libraries** (`@/lib/utils`, `@/lib/formatters`, `@/lib/mock-data`)

#### Architecture & Type System
- **45+ financial metrics** typed across Performance, Risk, Efficiency, Consistency domains
- **API contracts** defined for frontend-backend integration
- **Multi-fund extensible structure** prepared for dynamic CNPJ routing
- **Mock data system** for parallel frontend/backend development

### Known Issues in v0.2.0
- **Frontend page not implemented**: Main page (`app/page.tsx`) still shows default Next.js template
- **API integration missing**: No fetch layer, API client, or React Query hooks implemented
- **Type contract mismatch**: Frontend types don't match actual backend API response schemas
- **Build-blocking bugs**: Some component imports reference missing utility modules

### Notes
- **Backend is production-ready** with comprehensive test coverage and clean architecture
- **Frontend is scaffolded** with components and types but requires integration work to be functional
- **Two delivery modes**: CLI (fully functional) + REST API (fully functional) + Web Dashboard (scaffolded)

## [0.1.0] - 2026-03-27

### Added

#### Core System Architecture
- **SQLite Database** with WAL mode for concurrent access
- **Database Schema** with 8 tables: funds_metadata, daily_data, bcb_data, news_data, performance_metrics, fund_benchmarks, fund_performance, and analysis_reports
- **Protocol-based interfaces** for data collectors using Python structural typing
- **Repository pattern** for data access layer
- **Pydantic v2 models** for data validation with frozen dataclasses

#### Data Collection Systems
- **CVM Data Collector** for fund daily information
  - Downloads and processes monthly ZIP files from CVM API
  - Supports configurable date ranges and fund filtering by CNPJ
  - Handles 57+ daily records with automatic data validation
- **BCB Data Collector** for economic indicators
  - SELIC rate collection (series 11 and 432)
  - CDI rate collection (series 12)
  - IPCA inflation collection (series 433)
  - Automatic date range handling and data aggregation
- **News Collector** via Google RSS feeds
  - Configurable search terms for fund-specific news
  - 10+ news items per collection with metadata extraction
  - RSS feed parsing with error handling

#### Fund Analysis Engine
- **Performance Calculator** with benchmark comparisons
  - Fund return calculation vs SELIC, CDI benchmarks
  - Percentage-based performance metrics (e.g., 3.0976% vs -0.0894%)
  - Period-based analysis (1, 3, 6 months configurable)
- **Fund Identification System** targeting Nu Reserva Planejada
  - CNPJ validation and fund matching (43.121.002/0001-41)
  - Metadata extraction and validation

#### Reporting System
- **PDF Report Generator** using ReportLab
  - Professional layout with charts via matplotlib integration
  - Performance summaries and benchmark comparisons
  - News integration in reports
  - Configurable output format (118KB+ reports)
- **Email Delivery System**
  - Gmail SMTP integration with App Password authentication
  - Automated PDF attachment delivery
  - Configuration via environment variables

#### Testing & Quality Assurance
- **End-to-End Testing Suite** (`test_end_to_end.py`)
  - Real data validation with CVM and BCB APIs
  - PDF generation testing with mock and real data
  - Email delivery validation
  - Complete system integration testing
- **System Validation Scripts** for development workflow
  - Data collection validation
  - Performance calculation verification
  - Report generation testing

#### Command Line Interface
- **Unified CLI** via `market_analysis.cli` module
  - Configurable analysis periods (--months parameter)
  - Custom output file specification (--output parameter)
  - Email delivery integration (--email parameter)
  - Real-time logging and progress tracking

#### Local macOS Execution
- **Native macOS support** with Python 3.12+
- **Local environment configuration** via `.env` files
- **Manual execution workflow** for development and testing
- **Integration with macOS system** for file handling and notifications

### Technical Details

#### Dependencies & Environment
- **Python 3.12+** with async/await support
- **Key Libraries**: Pydantic v2, SQLite3, ReportLab, matplotlib, feedparser, requests
- **Development Tools**: pytest for testing, python-dotenv for configuration
- **Environment Configuration**: `.env` file with SMTP and API settings

#### Performance & Scalability
- **Concurrent Data Processing** with async interfaces
- **Efficient Data Storage** using SQLite WAL mode
- **Memory-Optimized** PDF generation for large datasets
- **Configurable Retry Logic** for external API calls

#### Security & Configuration
- **Environment-based Configuration** (`.env` protection via `.gitignore`)
- **Secure SMTP Authentication** using Gmail App Passwords
- **API Error Handling** with exponential backoff
- **Data Validation** at input/output boundaries

### Infrastructure

#### Repository Setup
- **GitHub Repository**: nelsonfrugeri-tech/market-analysis
- **Branching Strategy**: Feature branches with PR reviews
- **Issue Tracking**: GitHub Issues for roadmap management
- **Documentation**: Comprehensive README and inline code documentation

#### Development Workflow
- **3-Agent Development Team**: Architecture (Mr. Robot), Implementation (Elliot), Business Logic (Tyrell)
- **Code Review Process**: Mandatory PR reviews before merge
- **Testing Strategy**: End-to-end validation with real API data
- **Version Control**: Git with semantic versioning

### Validated Use Cases
- ✅ **Daily Fund Analysis**: Manual collection and analysis of Nu Reserva Planejada performance
- ✅ **Benchmark Comparison**: Real-time comparison against SELIC, CDI, and IPCA indicators
- ✅ **Manual Reporting**: PDF generation with charts and performance metrics
- ✅ **Email Delivery**: On-demand report delivery via SMTP
- ✅ **Data Persistence**: Historical data storage and retrieval
- ✅ **News Integration**: Contextual news collection for fund analysis

### Known Limitations
- **Single Fund Focus**: Currently optimized for Nu Reserva Planejada analysis
- **Manual Execution**: Requires manual trigger for analysis and reporting
- **Brazilian Market Only**: BCB and CVM APIs specific to Brazilian financial market
- **Email Provider**: Gmail SMTP dependency for automated delivery

### Future Enhancements (Planned for v0.2.0)
- **GitHub Actions Integration**: Automated daily execution via CI/CD
- **Scheduled Automation**: Cron-based execution at 9 AM Brazil time
- **Multi-Fund Support**: Analysis of multiple investment funds
- **Enhanced Analytics**: Advanced performance metrics and comparisons
- **Web Dashboard**: Browser-based interface for analysis and reports

---

**Full System Status**: ✅ **PRODUCTION READY** (Local Execution)
**Homologation**: ✅ **PASSED** with real data validation
**Documentation**: ✅ **COMPLETE** with architecture and usage guides
**Automation**: 🚧 **PLANNED** for next version (GitHub Actions)