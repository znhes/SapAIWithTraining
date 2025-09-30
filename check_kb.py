# check_kb.py
import sqlite3

def check_knowledge_base():
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    
    print("📚 KNOWLEDGE BASE CONTENTS:")
    print("=" * 50)
    
    cursor.execute("SELECT id, module, question, answer FROM knowledge_items ORDER BY id")
    
    for id, module, question, answer in cursor.fetchall():
        print(f"ID: {id}")
        print(f"Module: {module}")
        print(f"Question: '{question}'")
        print(f"Answer: '{answer}'")
        print("-" * 30)
    
    conn.close()

if __name__ == "__main__":
    check_knowledge_base()