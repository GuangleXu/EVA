import sqlite3


def initialize_database():
    connection = sqlite3.connect("memory/conversation_memory.db")
    cursor = connection.cursor()

    # 创建存储对话记录的表格，添加 memory_type 列
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            memory_type BOOLEAN NOT NULL DEFAULT 0,  -- 用于标记是否为回忆内容
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    connection.commit()
    connection.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
