#!/usr/bin/env python3
"""
Script to make a user an admin.
Usage: python make_admin.py <username>
"""
import sys
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User

def make_admin(username: str) -> bool:
    """Make a user an admin."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()

        if not user:
            print(f"❌ User '{username}' not found")
            return False

        if user.is_admin:
            print(f"ℹ️  User '{username}' is already an admin")
            return True

        user.is_admin = True
        db.commit()
        print(f"✅ User '{username}' is now an admin!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def list_admins():
    """List all admin users."""
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.is_admin == True).all()

        if not admins:
            print("ℹ️  No admin users found")
            return

        print(f"\n👥 Admin Users ({len(admins)}):")
        print("─" * 50)
        for admin in admins:
            print(f"  • {admin.username} ({admin.email})")
        print("─" * 50)

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python make_admin.py <username>  - Make a user admin")
        print("  python make_admin.py --list      - List all admins")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_admins()
    else:
        username = sys.argv[1]
        success = make_admin(username)
        sys.exit(0 if success else 1)
