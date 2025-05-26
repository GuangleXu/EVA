import sqlite3


def get_recent_conversations(limit=5):
    connection = sqlite3.connect("memory/conversation.db")
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM conversation_memory ORDER BY timestamp DESC LIMIT ?", (limit,)
    )
    conversations = cursor.fetchall()
    connection.close()
    return conversations
