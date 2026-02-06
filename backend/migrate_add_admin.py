#!/usr/bin/env python3
"""
Database migration script to add is_admin column to existing users table.
Run this once to upgrade your existing database.
"""
import sys
from sqlalchemy import text

from app.database import engine, SessionLocal
from app.models.base import Base

def migrate():
    """Add is_admin column to users table if it doesn't exist."""
    print("🔄 Running migration: Add is_admin column to users table")

    with engine.connect() as conn:
        # Check if column already exists
        try:
            result = conn.execute(text("SELECT is_admin FROM users LIMIT 1"))
            print("✓ is_admin column already exists, skipping migration")
            return
        except:
            # Column doesn't exist, add it
            pass

        try:
            # Add the column with default value
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
            print("✓ Successfully added is_admin column to users table")
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
