"""
数据库迁移脚本：为 chat_sessions 表创建表结构并迁移现有数据。
运行一次即可：cd backend && python -m app.migrate_sessions
"""
import asyncio
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "policy_qa.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_sessions'")
    if cursor.fetchone():
        print("[migrate] chat_sessions 表已存在，跳过。")
        conn.close()
        return

    print("[migrate] 迁移开始...")

    cursor.execute("""
        CREATE TABLE chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT NOT NULL DEFAULT '新会话',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id)")

    cursor.execute("PRAGMA table_info(chat_logs)")
    columns = {row[1] for row in cursor.fetchall()}

    if "session_id" in columns:
        print("[migrate] 迁移现有 chat_logs 数据到 chat_sessions...")
        cursor.execute("""
            SELECT DISTINCT session_id, user_id
            FROM chat_logs
            WHERE session_id IS NOT NULL
        """)
        count = 0
        for row in cursor.fetchall():
            session_id, user_id = row
            if session_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO chat_sessions (id, user_id, name, created_at, updated_at)
                    SELECT
                        ?,
                        ?,
                        COALESCE(
                            (SELECT SUBSTR(question, 1, 50) FROM chat_logs WHERE session_id = ? ORDER BY created_at ASC LIMIT 1),
                            '新会话'
                        ),
                        COALESCE(
                            (SELECT MIN(created_at) FROM chat_logs WHERE session_id = ?),
                            CURRENT_TIMESTAMP
                        ),
                        COALESCE(
                            (SELECT MAX(created_at) FROM chat_logs WHERE session_id = ?),
                            CURRENT_TIMESTAMP
                        )
                """, (session_id, user_id, session_id, session_id, session_id))
                count += 1
        print(f"[migrate] 迁移了 {count} 条会话记录。")

    conn.commit()
    conn.close()
    print("[migrate] 完成。")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[migrate] 错误：找不到数据库文件 {DB_PATH}")
        sys.exit(1)
    migrate()
