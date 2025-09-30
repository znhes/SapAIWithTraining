# database.py
import sqlite3
import json

class KnowledgeDatabase:
    def __init__(self, db_path="knowledge_base.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Knowledge items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                keywords TEXT,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Training data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                output_text TEXT NOT NULL,
                module TEXT DEFAULT 'general',
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Conversation logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                module TEXT DEFAULT 'general',
                source TEXT DEFAULT 'ai_model',
                confidence REAL DEFAULT 0.8,
                response_time REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!")
    
    def add_knowledge_item(self, module, question, answer, keywords=None):
        """Add new knowledge item"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        keywords_json = json.dumps(keywords) if keywords else "[]"
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_items 
            (module, question, answer, keywords)
            VALUES (?, ?, ?, ?)
        ''', (module, question, answer, keywords_json))
        
        conn.commit()
        conn.close()
        print(f"✅ Added knowledge item: {question[:50]}...")
    
    def search_knowledge(self, query, module=None, limit=5):
        """Search knowledge base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if module and query:
            cursor.execute('''
                SELECT * FROM knowledge_items 
                WHERE module = ? AND (question LIKE ? OR answer LIKE ?)
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (module, f'%{query}%', f'%{query}%', limit))
        elif module:
            cursor.execute('''
                SELECT * FROM knowledge_items 
                WHERE module = ?
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (module, limit))
        elif query:
            cursor.execute('''
                SELECT * FROM knowledge_items 
                WHERE question LIKE ? OR answer LIKE ?
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM knowledge_items 
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'module': row[1],
                'question': row[2],
                'answer': row[3],
                'keywords': json.loads(row[4]) if row[4] else [],
                'usage_count': row[5]
            })
        
        conn.close()
        return results
    
    def log_conversation(self, user_id, question, answer, module, source, confidence, response_time):
        """Log conversation for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_logs 
            (user_id, question, answer, module, source, confidence, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, question, answer, module, source, confidence, response_time))
        
        conn.commit()
        conn.close()

# Initialize database
knowledge_db = KnowledgeDatabase()