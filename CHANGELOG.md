# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

#### Backend REST API (FastAPI)
- **6 REST endpoints** fully implemented and tested:
  - `GET /api/v1/funds` - List available funds
  - `GET /api/v1/funds/{cnpj}/performance` - Fund performance with dynamic filters
  - `GET /api/v1/funds/{cnpj}/daily` - Daily time series data for charts
  - `GET /api/v1/funds/{cnpj}/explanations` - Metric explanations for UI tooltips
  - `GET /api/v1/health` - Health check with database status
  - `POST /api/v1/collect` - Trigger data collection from CVM/BCB
- **FastAPI Framework** with automatic Swagger/OpenAPI documentation
- **Pydantic models** for type-safe request/response validation
- **CORS middleware** configured for localhost:3000 frontend
- **Async/sync integration** with existing CLI backend using asyncio executors
- **Dynamic query parameters** for filtering and date range selection
- **Error handling** for missing data and collection failures

#### Frontend Web Dashboard
- **Next.js 16.2.2 + React 19.2.4** complete dashboard implementation
- **TypeScript strict mode** with zero `any` types for type safety
- **Tailwind CSS v4 + shadcn/ui** component library for elegant UI
- **Brazilian formatters** (pt-BR locale) for currency, percentages, and numbers
- **WCAG 2.2 accessibility** compliance with semantic HTML

#### Core Components Delivered
- **MetricCard** - Financial metrics display component with tooltips (13 tests)
- **MetricsSection** - Collapsible sections container component (10 tests)
- **PerformanceSection** - Complete performance metrics section (11 tests)

#### Architecture & Type System
- **45+ financial metrics** fully typed (Performance, Risk, Efficiency, Consistency)
- **6 API endpoints contracts** defined for FastAPI integration
- **Multi-fund extensible structure** with dynamic `/dashboard/[cnpj]` routing
- **Mock data system** for parallel frontend/backend development

#### Developer Experience & Quality
- **36 unit tests** passing with 100% component coverage
- **Vitest + Testing Library** modern testing framework
- **Biome linting/formatting** with strict code quality rules
- **TanStack Query** setup for API caching and state management
- **Production build** optimization and validation

#### Documentation & Diagrams
- **v0.2.0 Architecture diagram** created in `docs/v0.2.0-architecture.drawio`
- **Complete type definitions** in TypeScript for API contracts
- **Component documentation** with usage examples and tests

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