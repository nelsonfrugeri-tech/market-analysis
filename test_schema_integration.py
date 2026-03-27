#!/usr/bin/env python3
"""Integration test for the database schema and basic functionality."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from market_analysis.infrastructure.database import DatabaseManager
from market_analysis.domain.models import BCBRecord, CollectionStatus
import sqlite3
from decimal import Decimal
from datetime import date


def test_database_integration():
    """Test complete database integration: schema, seed data, and basic operations."""
    print("🚀 Starting database integration test...")

    # Setup test database
    db_path = Path("integration_test.db")
    if db_path.exists():
        db_path.unlink()

    # Initialize database with schema and seed data
    db_manager = DatabaseManager(db_path=db_path)
    db_manager.initialise()
    print("✅ Database initialized with schema")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Verify all required tables exist
        required_tables = ['bcb_data', 'news_data', 'funds_metadata', 'system_config', 'recipients', 'collection_metadata']

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table in required_tables:
            assert table in existing_tables, f"Missing table: {table}"
        print(f"✅ All {len(required_tables)} tables created successfully")

        # Verify Nu Reserva Planejada seed data
        cursor.execute("SELECT cnpj, name FROM funds_metadata WHERE cnpj = ?", ("43.121.002/0001-41",))
        fund_data = cursor.fetchone()
        assert fund_data is not None, "Nu Reserva Planejada seed data missing"
        assert fund_data[0] == "43.121.002/0001-41"
        print(f"✅ Fund seed data verified: {fund_data[0]}")

        # Test BCB data insertion
        test_data = [
            ("432", "SELIC", "2026-03-27", "13.75"),  # SELIC
            ("4389", "CDI", "2026-03-27", "13.65"),   # CDI
            ("433", "IPCA", "2026-02-01", "4.50"),    # IPCA
        ]

        for series_code, indicator, ref_date, value in test_data:
            cursor.execute("""
                INSERT INTO bcb_data (series_code, indicator, reference_date, value, collected_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (series_code, indicator, ref_date, value))

        # Verify data was inserted correctly
        cursor.execute("SELECT COUNT(*) FROM bcb_data")
        count = cursor.fetchone()[0]
        assert count == 3, f"Expected 3 BCB records, got {count}"
        print(f"✅ BCB data insertion test passed: {count} records")

        # Test news data insertion
        cursor.execute("""
            INSERT INTO news_data (title, link, published_at, description, source, collected_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            "Test Nubank News",
            "https://test.example.com/news/1",
            "2026-03-27",
            "Test news description",
            "Test Source"
        ))

        cursor.execute("SELECT COUNT(*) FROM news_data")
        news_count = cursor.fetchone()[0]
        assert news_count == 1, f"Expected 1 news record, got {news_count}"
        print(f"✅ News data insertion test passed: {news_count} records")

        # Verify WAL mode is enabled (for concurrent access)
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"
        print(f"✅ WAL mode enabled for concurrent access: {journal_mode}")

    # Cleanup
    db_path.unlink()
    print("🎉 Integration test completed successfully!")
    print()
    print("Ready for team handoff:")
    print("- Elliot: BCB/News collectors can use the BaseCollector interface")
    print("- Tyrell: CVM/PDF can use PerformanceReport model and database tables")


if __name__ == "__main__":
    test_database_integration()