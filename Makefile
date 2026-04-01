# Market Analysis Platform - Development Automation
# Usage: make <command>

.PHONY: help install test lint run build clean dev setup compile compile-backend compile-frontend kill-dev

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
	@echo "  make test-api       - Run API integration tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint           - Run all linters and formatters"
	@echo "  make lint-backend   - Run ruff + mypy on Python code"
	@echo "  make lint-frontend  - Run Biome on TypeScript code"
	@echo "  make format         - Format all code (auto-fix)"
	@echo ""
	@echo "🏗️ Build & Compile:"
	@echo "  make compile        - Build production version (backend + frontend)"
	@echo "  make compile-backend - Build Python application"
	@echo "  make compile-frontend - Build Next.js for production"
	@echo ""
	@echo "🏃 Running:"
	@echo "  make run            - Start both backend and frontend"
	@echo "  make run-backend    - Start FastAPI server only"
	@echo "  make run-frontend   - Start Next.js dev server only"
	@echo "  make run-cli        - Run CLI analysis tool"
	@echo "  make kill-dev       - Stop all development processes"
	@echo ""
	@echo "🗄️ Database:"
	@echo "  make db-init        - Initialize SQLite database"
	@echo "  make db-reset       - Reset database (drop + recreate)"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean          - Clean all build artifacts"
	@echo "  make security-audit - Run security vulnerability scans"

# ==================== SETUP AND INSTALLATION ====================

setup: install db-init
	@echo "✅ Project setup complete! Run 'make dev' to start development."

install: install-backend install-frontend
	@echo "✅ All dependencies installed successfully!"

install-backend:
	@echo "📦 Installing Python dependencies..."
	@if [ ! -d ".venv" ]; then /opt/homebrew/bin/python3.12 -m venv .venv; fi
	@.venv/bin/pip install -e .
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
	@.venv/bin/python -m pytest tests/ -v --cov=src/market_analysis --cov-report=term-missing --cov-report=html
	@echo "✅ Backend tests completed! Coverage report: htmlcov/index.html"

test-frontend:
	@echo "🧪 Running React component tests..."
	@cd frontend && npm test run
	@echo "✅ Frontend tests completed!"

test-api:
	@echo "🧪 Running API integration tests..."
	@.venv/bin/python -m pytest tests/test_api.py -v
	@echo "✅ API tests completed!"

# ==================== CODE QUALITY ====================

lint: lint-backend lint-frontend
	@echo "✅ All code quality checks completed!"

lint-backend:
	@echo "🔍 Running Python linters..."
	@.venv/bin/python -m ruff check src/ tests/
	@.venv/bin/python -m mypy src/market_analysis
	@echo "✅ Backend code quality checks completed!"

lint-frontend:
	@echo "🔍 Running TypeScript linters..."
	@cd frontend && npm run lint
	@cd frontend && npm run type-check
	@echo "✅ Frontend code quality checks completed!"

format:
	@echo "🎨 Formatting all code..."
	@.venv/bin/python -m ruff format src/ tests/
	@cd frontend && npm run format
	@echo "✅ Code formatting completed!"

# ==================== BUILD & COMPILE ====================

compile: compile-backend compile-frontend
	@echo "✅ Production build completed!"

compile-backend:
	@echo "🏗️ Building Python application..."
	@.venv/bin/python -m compileall src/market_analysis/
	@echo "✅ Backend build completed!"

compile-frontend:
	@echo "🏗️ Building Next.js for production..."
	@cd frontend && npm run build
	@echo "✅ Frontend build completed!"

# ==================== DEVELOPMENT SERVERS ====================

dev: run

run: kill-dev
	@echo "🚀 Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3001"
	@echo "API Docs: http://localhost:8000/api/docs"
	@echo ""
	@echo "Press Ctrl+C to stop all servers"
	@trap 'kill %1; kill %2' INT; \
	 make run-backend & \
	 make run-frontend & \
	 wait

kill-dev:
	@echo "🧹 Cleaning up running processes..."
	@pkill -f "uvicorn" || true
	@pkill -f "next dev" || true
	@pkill -f "make dev" || true
	@lsof -ti :8000 | xargs -r kill -9 2>/dev/null || true
	@lsof -ti :3001 | xargs -r kill -9 2>/dev/null || true
	@sleep 1
	@echo "✅ Ports 8000 and 3001 cleaned!"

run-backend:
	@echo "🐍 Starting FastAPI server..."
	@.venv/bin/uvicorn market_analysis.api.main:app --reload --port 8000

run-frontend:
	@echo "⚛️  Starting Next.js development server..."
	@cd frontend && npm run dev

run-cli:
	@echo "💻 Running CLI analysis tool..."
	@.venv/bin/python -m market_analysis.cli --months 3 --output reports/analysis.pdf
	@echo "✅ Analysis complete! Report saved to reports/analysis.pdf"

# ==================== DATABASE ====================

db-init:
	@echo "🗄️ Initializing SQLite database..."
	@.venv/bin/python -c "from market_analysis.infrastructure.database import get_database; get_database()"
	@echo "✅ Database initialized!"

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

security-audit:
	@echo "🔒 Running security audits..."
	@cd frontend && npm audit
	@echo "✅ Security audits completed!"

# ==================== UTILITIES ====================

status:
	@echo "📊 Project Status:"
	@echo ""
	@echo "Backend (Python):"
	@python3 --version 2>/dev/null || echo "  Python not found"
	@echo ""
	@echo "Frontend (Node.js):"
	@node --version 2>/dev/null || echo "  Node.js not found"
	@npm --version 2>/dev/null || echo "  npm not found"
	@echo ""
	@echo "Database:"
	@test -f data/market_analysis.db && echo "  ✅ Database exists" || echo "  ❌ Database not initialized"