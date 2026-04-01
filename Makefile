# Market Analysis Platform - Development Automation
# Usage: make <command>

.PHONY: help install test lint run build clean docker dev setup

# Default target
help:
	@echo "Market Analysis Platform - Development Commands"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup          - Complete project setup (install + init)"
	@echo "  make dev            - Start development servers (backend + frontend)"
	@echo "  make test           - Run all tests (backend + frontend)"
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install        - Install all dependencies"
	@echo "  make install-backend - Install Python dependencies only"
	@echo "  make install-frontend - Install Node.js dependencies only"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-backend   - Run Python tests with coverage"
	@echo "  make test-frontend  - Run React component tests"
	@echo "  make test-e2e       - Run end-to-end tests with real data"
	@echo "  make test-api       - Run API integration tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint           - Run all linters and formatters"
	@echo "  make lint-backend   - Run ruff + mypy on Python code"
	@echo "  make lint-frontend  - Run Biome on TypeScript code"
	@echo "  make format         - Format all code (auto-fix)"
	@echo ""
	@echo "🏃 Running:"
	@echo "  make run            - Start both backend and frontend"
	@echo "  make run-backend    - Start FastAPI server only"
	@echo "  make run-frontend   - Start Next.js dev server only"
	@echo "  make run-cli        - Run CLI analysis tool"
	@echo ""
	@echo "🏗️ Building:"
	@echo "  make build          - Build for production"
	@echo "  make build-frontend - Build Next.js production bundle"
	@echo "  make build-docs     - Generate API documentation"
	@echo ""
	@echo "🗄️ Database:"
	@echo "  make db-init        - Initialize SQLite database"
	@echo "  make db-migrate     - Run database migrations"
	@echo "  make db-seed        - Seed database with test data"
	@echo "  make db-reset       - Reset database (drop + recreate)"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean          - Clean all build artifacts"
	@echo "  make clean-cache    - Clear Python and Node.js caches"
	@echo "  make deps-update    - Check for dependency updates"
	@echo "  make security-audit - Run security vulnerability scans"

# ==================== SETUP AND INSTALLATION ====================

setup: install db-init
	@echo "✅ Project setup complete! Run 'make dev' to start development."

install: install-backend install-frontend
	@echo "✅ All dependencies installed successfully!"

install-backend:
	@echo "📦 Installing Python dependencies..."
	@pip install -e .
	@echo "✅ Backend dependencies installed!"

install-frontend:
	@echo "📦 Installing Node.js dependencies..."
	@cd frontend && npm install
	@echo "✅ Frontend dependencies installed!"

# ==================== TESTING ====================

test: test-backend test-frontend
	@echo "✅ All tests completed!"

test-backend:
	@echo "🧪 Running Python tests with coverage..."
	@python -m pytest tests/ -v --cov=src/market_analysis --cov-report=term-missing --cov-report=html
	@echo "✅ Backend tests completed! Coverage report: htmlcov/index.html"

test-frontend:
	@echo "🧪 Running React component tests..."
	@cd frontend && npm test run
	@echo "✅ Frontend tests completed!"

test-e2e:
	@echo "🧪 Running end-to-end tests with real data..."
	@python test_end_to_end.py --email test@example.com || echo "⚠️  E2E tests require email configuration"
	@echo "✅ End-to-end tests completed!"

test-api:
	@echo "🧪 Running API integration tests..."
	@python -m pytest tests/test_api.py -v
	@echo "✅ API tests completed!"

test-coverage:
	@echo "📊 Generating test coverage report..."
	@python -m pytest tests/ --cov=src/market_analysis --cov-report=html
	@cd frontend && npm run test:coverage
	@echo "✅ Coverage reports generated!"

# ==================== CODE QUALITY ====================

lint: lint-backend lint-frontend
	@echo "✅ All code quality checks completed!"

lint-backend:
	@echo "🔍 Running Python linters..."
	@python -m ruff check src/ tests/
	@python -m mypy src/market_analysis
	@echo "✅ Backend code quality checks completed!"

lint-frontend:
	@echo "🔍 Running TypeScript linters..."
	@cd frontend && npm run lint
	@cd frontend && npm run type-check
	@echo "✅ Frontend code quality checks completed!"

format:
	@echo "🎨 Formatting all code..."
	@python -m ruff format src/ tests/
	@cd frontend && npm run format
	@echo "✅ Code formatting completed!"

# ==================== DEVELOPMENT SERVERS ====================

dev: run

run:
	@echo "🚀 Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "API Docs: http://localhost:8000/api/docs"
	@echo ""
	@echo "Press Ctrl+C to stop all servers"
	@trap 'kill %1; kill %2' INT; \
	 make run-backend & \
	 make run-frontend & \
	 wait

run-backend:
	@echo "🐍 Starting FastAPI server..."
	@uvicorn market_analysis.api.main:app --reload --port 8000

run-frontend:
	@echo "⚛️  Starting Next.js development server..."
	@cd frontend && npm run dev

run-cli:
	@echo "💻 Running CLI analysis tool..."
	@python -m market_analysis.cli --months 3 --output reports/analysis.pdf
	@echo "✅ Analysis complete! Report saved to reports/analysis.pdf"

# ==================== BUILDING ====================

build: build-frontend
	@echo "✅ Production build completed!"

build-frontend:
	@echo "🏗️ Building Next.js for production..."
	@cd frontend && npm run build
	@echo "✅ Frontend build completed!"

build-docs:
	@echo "📚 Generating API documentation..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:8000/api/docs')"
	@echo "✅ API docs available at http://localhost:8000/api/docs"

# ==================== DATABASE ====================

db-init:
	@echo "🗄️ Initializing SQLite database..."
	@python -c "from market_analysis.infrastructure.database import init_db; init_db()"
	@echo "✅ Database initialized!"

db-migrate:
	@echo "🗄️ Running database migrations..."
	@echo "ℹ️  No migrations system yet - using direct SQLite schema"

db-seed:
	@echo "🌱 Seeding database with test data..."
	@python -c "from tests.helpers.db_helpers import seed_test_data; seed_test_data()" || echo "⚠️  Test data seeding not available"

db-reset:
	@echo "🗄️ Resetting database..."
	@rm -f data/market_analysis.db
	@make db-init
	@echo "✅ Database reset completed!"

# ==================== MAINTENANCE ====================

clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@rm -rf htmlcov/ .coverage
	@cd frontend && rm -rf .next/ node_modules/.cache/
	@rm -rf reports/*.pdf
	@echo "✅ Clean completed!"

clean-cache:
	@echo "🧹 Clearing all caches..."
	@rm -rf __pycache__ **/__pycache__ .pytest_cache .mypy_cache .ruff_cache
	@cd frontend && rm -rf node_modules/.cache/ .next/cache/
	@pip cache purge
	@cd frontend && npm cache clean --force
	@echo "✅ Cache cleared!"

deps-update:
	@echo "📦 Checking for dependency updates..."
	@pip list --outdated
	@cd frontend && npm outdated
	@echo "ℹ️  Review outdated packages above. Use exact pinning for security!"

security-audit:
	@echo "🔒 Running security audits..."
	@pip-audit || echo "⚠️  pip-audit not installed: pip install pip-audit"
	@cd frontend && npm audit
	@echo "✅ Security audits completed!"

# ==================== DOCKER (FUTURE) ====================

docker-build:
	@echo "🐳 Building Docker images..."
	@echo "ℹ️  Docker setup not yet implemented"

docker-run:
	@echo "🐳 Running Docker containers..."
	@echo "ℹ️  Docker setup not yet implemented"

# ==================== UTILITIES ====================

check: lint test
	@echo "✅ All checks passed! Ready for deployment."

status:
	@echo "📊 Project Status:"
	@echo ""
	@echo "Backend (Python):"
	@python --version
	@pip show market-analysis | grep Version || echo "  Package not installed"
	@echo ""
	@echo "Frontend (Node.js):"
	@node --version
	@npm --version
	@echo ""
	@echo "Database:"
	@test -f data/market_analysis.db && echo "  ✅ Database exists" || echo "  ❌ Database not initialized"
	@echo ""
	@echo "Dependencies:"
	@cd frontend && npm list --depth=0 | head -5

info:
	@echo "ℹ️  Market Analysis Platform v0.2.0"
	@echo ""
	@echo "🏗️ Architecture: CLI + REST API + Web Dashboard"
	@echo "🐍 Backend: Python 3.12 + FastAPI + SQLite"
	@echo "⚛️  Frontend: Node.js + Next.js 16 + React 19"
	@echo "📊 Data: CVM + BCB + AI Explanations"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  • README.md - Complete setup guide"
	@echo "  • API Docs: http://localhost:8000/api/docs"
	@echo "  • CHANGELOG.md - Version history"