# create_sample_data.py
from database import KnowledgeDatabase

def create_sample_data():
    print("🚀 Creating sample data...")
    
    db = KnowledgeDatabase()
    
    # Sample knowledge items
    samples = [
        {
            "module": "payroll",
            "question": "How to process payroll?",
            "answer": "Go to Payroll → Process Payroll → Select employee group → Choose pay period → Review calculations → Approve and process.",
            "keywords": ["payroll", "process", "salary"]
        },
        {
            "module": "payroll", 
            "question": "Generate employee payslips",
            "answer": "Navigate to Payroll → Payslip Management → Select employees → Choose pay period → Generate PDF/Email payslips.",
            "keywords": ["payslip", "generate", "pdf"]
        },
        {
            "module": "attendance",
            "question": "Mark employee attendance",
            "answer": "Go to Attendance → Mark Attendance → Select date → Choose employees → Mark present/absent/half-day → Save.",
            "keywords": ["attendance", "mark", "present"]
        },
        {
            "module": "attendance",
            "question": "View attendance report",
            "answer": "Access Reports → Attendance Reports → Select date range → Choose department/employee → Generate report.",
            "keywords": ["report", "attendance", "analytics"]
        },
        {
            "module": "ess",
            "question": "How to apply for leave?",
            "answer": "Login to Employee Self-Service → My Leave → Apply New Leave → Select leave type → Choose dates → Submit for approval.",
            "keywords": ["self-service", "leave", "apply"]
        }
    ]
    
    # Add to knowledge base
    for item in samples:
        db.add_knowledge_item(
            item["module"],
            item["question"], 
            item["answer"],
            item["keywords"]
        )
    
    print(f"✅ Created {len(samples)} sample knowledge items")
    
    # Add some training data
    import sqlite3
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    
    training_samples = [
        ("how to run payroll", "Go to Payroll → Process Payroll → Select employee group → Choose pay period → Review calculations → Approve and process.", "payroll", "sample"),
        ("create payslips", "Navigate to Payroll → Payslip Management → Select employees → Choose pay period → Generate PDF/Email payslips.", "payroll", "sample"),
        ("mark attendance", "Go to Attendance → Mark Attendance → Select date → Choose employees → Mark present/absent/half-day → Save.", "attendance", "sample"),
    ]
    
    for input_text, output_text, module, source in training_samples:
        cursor.execute('''
            INSERT INTO training_data (input_text, output_text, module, source)
            VALUES (?, ?, ?, ?)
        ''', (input_text, output_text, module, source))
    
    conn.commit()
    conn.close()
    print("✅ Created sample training data")
    
    # Verify data
    conn = sqlite3.connect('knowledge_base.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM knowledge_items")
    kb_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM training_data")
    training_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Knowledge Base: {kb_count} items")
    print(f"📚 Training Data: {training_count} items")
    print("🎉 Sample data creation completed!")

if __name__ == "__main__":
    create_sample_data()