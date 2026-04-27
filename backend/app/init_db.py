"""
Database initialization script for Policy QA Agent.
Run: python app\init_db.py  (from backend directory)
"""
import asyncio
import os
import sys

# Project root is parent of backend directory
# When run from backend/, sys.path[0] is the backend dir
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.database import init_db, AsyncSessionLocal
from app.policies.models import User
from app.auth.service import hash_password


async def init_database():
    print("=" * 50)
    print("  Policy QA - Database Initialization")
    print("=" * 50)
    print()

    print("[1/2] Creating database tables...")
    try:
        await init_db()
        print("       [OK] Tables created")
    except Exception as e:
        print(f"       [FAIL] {e}")
        return

    print()
    print("[2/2] Creating admin account...")
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.username == "admin"))
            existing = result.scalar_one_or_none()

            if existing:
                print("       [SKIP] Admin already exists")
                print("              username: admin")
            else:
                admin = User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
                db.add(admin)
                await db.commit()
                print("       [OK] Admin account created")
                print()
                print("  Username: admin")
                print("  Password: admin123")
                print("  Role:     admin")
    except Exception as e:
        print(f"       [FAIL] {e}")
        return

    print()
    print("=" * 50)
    print("  Done!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(init_database())
