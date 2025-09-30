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
        """Search knowledge base with improved matching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean the query for better matching
        clean_query = query.strip().lower()
        
        print(f"🔍 Searching for: '{clean_query}' in module: '{module}'")
        
        if module and clean_query:
            # More flexible search
            cursor.execute('''
                SELECT *, 
                       (CASE 
                        WHEN question LIKE ? THEN 3
                        WHEN question LIKE ? THEN 2
                        WHEN answer LIKE ? THEN 1
                        ELSE 0
                       END) as relevance
                FROM knowledge_items 
                WHERE module = ? AND (question LIKE ? OR answer LIKE ? OR keywords LIKE ?)
                ORDER BY relevance DESC, usage_count DESC
                LIMIT ?
            ''', (
                f'%{clean_query}%',      # Exact match in question
                f'{clean_query}%',       # Starts with query
                f'%{clean_query}%',      # Anywhere in answer
                module,
                f'%{clean_query}%',      # Basic search
                f'%{clean_query}%', 
                f'%{clean_query}%', 
                limit
            ))
        elif module:
            cursor.execute('''
                SELECT * FROM knowledge_items 
                WHERE module = ?
                ORDER BY usage_count DESC
                LIMIT ?
            ''', (module, limit))
        elif clean_query:
            cursor.execute('''
                SELECT *, 
                       (CASE 
                        WHEN question LIKE ? THEN 2
                        WHEN answer LIKE ? THEN 1
                        ELSE 0
                       END) as relevance
                FROM knowledge_items 
                WHERE question LIKE ? OR answer LIKE ? OR keywords LIKE ?
                ORDER BY relevance DESC, usage_count DESC
                LIMIT ?
            ''', (
                f'{clean_query}%',       # Starts with query
                f'%{clean_query}%',      # Anywhere in answer
                f'%{clean_query}%', 
                f'%{clean_query}%', 
                f'%{clean_query}%', 
                limit
            ))
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
                'usage_count': row[5],
                'relevance': row[6] if len(row) > 6 else 0
            })
        
        conn.close()
        
        print(f"✅ Found {len(results)} matches")
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
    
    def get_training_data(self, limit=100):
        """Get training data for model training"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT input_text, output_text, module, source 
            FROM training_data 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'input_text': row[0],
                'output_text': row[1],
                'module': row[2],
                'source': row[3]
            })
        
        conn.close()
        return results
    
    def get_knowledge_stats(self):
        """Get statistics about knowledge base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total knowledge items
        cursor.execute("SELECT COUNT(*) FROM knowledge_items")
        total_items = cursor.fetchone()[0]
        
        # Items by module
        cursor.execute("SELECT module, COUNT(*) FROM knowledge_items GROUP BY module")
        module_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total training data
        cursor.execute("SELECT COUNT(*) FROM training_data")
        training_count = cursor.fetchone()[0]
        
        # Total conversations
        cursor.execute("SELECT COUNT(*) FROM conversation_logs")
        conversation_count = cursor.fetchone()[0]
        
        # Most used knowledge items
        cursor.execute("SELECT question, usage_count FROM knowledge_items ORDER BY usage_count DESC LIMIT 5")
        top_questions = [{"question": row[0], "usage_count": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_knowledge_items": total_items,
            "module_breakdown": module_stats,
            "training_data_count": training_count,
            "conversation_count": conversation_count,
            "top_questions": top_questions
        }
    
    def delete_knowledge_item(self, item_id):
        """Delete knowledge item by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted
    
    def update_knowledge_item(self, item_id, module=None, question=None, answer=None, keywords=None):
        """Update existing knowledge item"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        if module is not None:
            update_fields.append("module = ?")
            update_values.append(module)
        
        if question is not None:
            update_fields.append("question = ?")
            update_values.append(question)
        
        if answer is not None:
            update_fields.append("answer = ?")
            update_values.append(answer)
        
        if keywords is not None:
            keywords_json = json.dumps(keywords)
            update_fields.append("keywords = ?")
            update_values.append(keywords_json)
        
        if not update_fields:
            conn.close()
            return False
        
        update_values.append(item_id)
        
        query = f"UPDATE knowledge_items SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, update_values)
        conn.commit()
        
        updated = cursor.rowcount > 0
        conn.close()
        
        return updated
    
    def get_all_knowledge_items(self, limit=1000):
        """Get all knowledge items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, module, question, answer, keywords, usage_count, created_at
            FROM knowledge_items 
            ORDER BY created_at DESC 
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
                'usage_count': row[5],
                'created_at': row[6]
            })
        
        conn.close()
        return results
    
    def clear_conversation_logs(self):
        """Clear all conversation logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversation_logs")
        conn.commit()
        
        deleted_count = cursor.rowcount
        conn.close()
        
        return deleted_count
    
    def export_knowledge_base(self):
        """Export knowledge base as list of dictionaries"""
        return self.get_all_knowledge_items()
    
    def import_knowledge_base(self, knowledge_items):
        """Import knowledge items from list of dictionaries"""
        success_count = 0
        error_count = 0
        
        for item in knowledge_items:
            try:
                self.add_knowledge_item(
                    module=item.get('module', 'general'),
                    question=item.get('question', ''),
                    answer=item.get('answer', ''),
                    keywords=item.get('keywords', [])
                )
                success_count += 1
            except Exception as e:
                print(f"Error importing item: {e}")
                error_count += 1
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "total_processed": success_count + error_count
        }

# Initialize database
knowledge_db = KnowledgeDatabase()