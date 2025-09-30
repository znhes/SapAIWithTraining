# app_flask.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import time
import re
import requests
import csv
import io

from database import knowledge_db

app = Flask(__name__)
CORS(app)

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 15

def is_ollama_running():
    """Check if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def is_model_available():
    """Check if deepseek model is downloaded"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = response.json().get("models", [])
        return any("deepseek" in model.get("name", "").lower() for model in models)
    except:
        return False

def ask_ollama(question: str, module: str = "general") -> str:
    """Send question to Ollama with better error handling"""
    
    # Quick local greeting handling
    if re.match(r'^\s*(hi|hello|hey|hiya|yo)[\s!.]*$', question, flags=re.I):
        return "Hello 👋 How can I assist you with Sapience HCM today?"
    
    # Try models in order of preference - CUSTOM MODEL FIRST
    models_to_try = [
        "sapience-hcm-assistant",  # Your custom trained model
        "deepseek-r1:1.5b",        # Original model
        "llama2:3b"                # Fallback model
    ]
    
    for model in models_to_try:
        try:
            print(f"🔄 Trying model: {model}")
            
            # Enhanced system prompt for better responses
            system_prompt = f"""You are Sapience HCM Assistant specialized in {module} module. 
Provide concise, step-by-step answers about HCM processes.
Keep responses under 3 sentences and focus on practical steps.
If you don't know something, say so and suggest contacting support."""

            payload = {
                "model": model,
                "prompt": f"{system_prompt}\n\nUser question: {question}",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 150,  # Limit response length
                    "top_k": 40,
                    "top_p": 0.9,
                    "seed": 42
                }
            }
            
            # Shorter timeout - if it takes more than 8 seconds, try next model
            response = requests.post(OLLAMA_URL, json=payload, timeout=8)
            response.raise_for_status()
            result = response.json()
            answer = (result.get("response") or result.get("text") or "").strip()
            
            # Validate the response
            if (answer and 
                len(answer) > 10 and 
                "error" not in answer.lower() and
                "timeout" not in answer.lower()):
                print(f"✅ Model {model} responded successfully")
                return answer
            else:
                print(f"❌ Model {model} returned invalid response: {answer}")
                continue
                
        except requests.exceptions.Timeout:
            print(f"⏰ Model {model} timeout - trying next model")
            continue
        except requests.exceptions.ConnectionError:
            print(f"🔌 Model {model} connection error - trying next model")
            continue
        except Exception as e:
            print(f"❌ Model {model} error: {str(e)}")
            continue
    
    # If all models fail, use intelligent fallback
    return get_intelligent_fallback(question, module)

def get_intelligent_fallback(question: str, module: str) -> str:
    """Provide intelligent fallback responses when AI is unavailable"""
    question_lower = question.lower()
    
    # Enhanced fallback responses based on your knowledge base
    fallback_responses = {
        "payroll": {
            "keywords": ["payroll", "salary", "payslip", "tax", "deduction", "bonus", "process", "run"],
            "response": "Payroll Process: 1) Go to Payroll → Process Payroll 2) Select employee group 3) Choose pay period 4) Review calculations 5) Approve and process. For specific issues, check Payroll → Error Log."
        },
        "attendance": {
            "keywords": ["attendance", "time", "clock", "present", "absent", "late", "mark", "report"],
            "response": "Attendance: Mark daily attendance in Attendance → Mark Attendance. View reports in Reports → Attendance Analytics. Configure settings in System → Attendance Settings."
        },
        "hr": {
            "keywords": ["employee", "hr", "human resources", "onboarding", "termination", "profile", "add", "new"],
            "response": "HR Management: Add employees in HR → Employee Management → Add New Employee. Onboarding checklist available in HR → Onboarding. Employee profiles in HR → Employee Directory."
        },
        "ess": {
            "keywords": ["self-service", "ess", "profile", "payslip", "leave", "request", "my", "update"],
            "response": "Employee Self-Service: Update personal info in My Profile → Personal Details. View payslips in My Payslips → Select Period. Apply leave in My Leave → Apply New Leave."
        },
        "general": {
            "keywords": ["help", "support", "how to", "what is", "where is", "guide"],
            "response": "I can help you navigate Sapience HCM modules. Please specify if you need assistance with Payroll, Attendance, HR Management, or Employee Self-Service for more specific guidance."
        }
    }
    
    # Check module-specific keywords first
    module_responses = fallback_responses.get(module, fallback_responses["general"])
    for keyword in module_responses["keywords"]:
        if keyword in question_lower:
            return module_responses["response"]
    
    # Check general keywords across all modules
    for mod_name, mod_data in fallback_responses.items():
        if mod_name != module:  # Don't recheck the same module
            for keyword in mod_data["keywords"]:
                if keyword in question_lower:
                    return f"Based on your question about '{keyword}', here's {mod_name} guidance: {mod_data['response']}"
    
    # Default fallback
    return f"I specialize in {module} functionality. For detailed assistance with '{question}', please check the knowledge base or contact your system administrator."

# ============ BASIC ENDPOINTS ============

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "Sapience HCM AI Help Desk API", 
        "version": "1.0.0"
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Check system health"""
    ollama_connected = is_ollama_running()
    
    return jsonify({
        "status": "healthy",
        "ollama_connected": ollama_connected,
        "message": "API is running"
    })

@app.route("/chat", methods=["POST"])
def chat():
    """Chat with AI help desk"""
    data = request.get_json()
    
    if not data or 'question' not in data:
        return jsonify({"error": "Missing question"}), 400
    
    question = data['question']
    module = data.get('module', 'general')
    user_id = data.get('user_id')
    
    start_time = time.time()
    
    # 1. Search knowledge base first
    kb_results = knowledge_db.search_knowledge(question, module, limit=3)
    
    if kb_results:
        best_match = kb_results[0]
        response_time = time.time() - start_time
        
        # Update usage count
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE knowledge_items SET usage_count = usage_count + 1 WHERE id = ?",
            (best_match['id'],)
        )
        conn.commit()
        conn.close()
        
        # Log conversation
        knowledge_db.log_conversation(
            user_id, question, best_match['answer'],
            module, "knowledge_base", 0.95, response_time
        )
        
        return jsonify({
            "answer": best_match['answer'],
            "source": "knowledge_base",
            "module": module,
            "confidence": 0.95,
            "response_time": response_time
        })
    
    # 2. Use Ollama for complex questions
    if is_ollama_running():
        ai_answer = ask_ollama(question, module)
        response_time = time.time() - start_time
        
        knowledge_db.log_conversation(
            user_id, question, ai_answer,
            module, "ai_model", 0.80, response_time
        )
        
        return jsonify({
            "answer": ai_answer,
            "source": "ai_model",
            "module": module,
            "confidence": 0.80,
            "response_time": response_time
        })
    else:
        response_time = time.time() - start_time
        fallback_answer = "I can help with HCM questions. Try asking about payroll, attendance, or employee self-service."
        
        knowledge_db.log_conversation(
            user_id, question, fallback_answer,
            module, "fallback", 0.50, response_time
        )
        
        return jsonify({
            "answer": fallback_answer,
            "source": "fallback",
            "module": module,
            "confidence": 0.50,
            "response_time": response_time
        })

# ============ KNOWLEDGE BASE ENDPOINTS ============

@app.route("/knowledge", methods=["POST"])
def add_knowledge_item():
    """Add new item to knowledge base"""
    data = request.get_json()
    
    if not data or 'module' not in data or 'question' not in data or 'answer' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    module = data['module']
    question = data['question']
    answer = data['answer']
    keywords = data.get('keywords')
    
    knowledge_db.add_knowledge_item(module, question, answer, keywords)
    
    return jsonify({"message": "Knowledge item added successfully", "status": "success"})

@app.route("/knowledge", methods=["GET"])
def search_knowledge():
    """Search knowledge base"""
    query = request.args.get('query', '')
    module = request.args.get('module')
    limit = int(request.args.get('limit', 10))
    
    results = knowledge_db.search_knowledge(query, module, limit)
    
    return jsonify({"results": results, "count": len(results)})

@app.route("/knowledge/<int:item_id>", methods=["DELETE"])
def delete_knowledge_item(item_id):
    """Delete knowledge item"""
    try:
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Knowledge item not found"}), 404
        
        conn.close()
        return jsonify({"message": "Knowledge item deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ TRAINING ENDPOINTS ============

@app.route("/training", methods=["GET"])
def get_training_data():
    """Get training data"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect(knowledge_db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, input_text, output_text, module, source, created_at 
        FROM training_data 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    training_data = []
    for row in cursor.fetchall():
        training_data.append({
            "id": row[0],
            "input_text": row[1],
            "output_text": row[2],
            "module": row[3],
            "source": row[4],
            "created_at": row[5]
        })
    
    conn.close()
    
    return jsonify({"training_data": training_data, "count": len(training_data)})

@app.route("/training/generate", methods=["POST"])
def generate_training_data():
    """Generate training data from knowledge base"""
    try:
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        
        # Get all knowledge items
        cursor.execute("SELECT question, answer, module FROM knowledge_items")
        knowledge_items = cursor.fetchall()
        
        generated_count = 0
        for question, answer, module in knowledge_items:
            # Create variations
            variations = [
                question,
                question + "?",
                f"How to {question}",
                f"Steps to {question}",
                f"Explain {question}"
            ]
            
            for variation in variations:
                cursor.execute('''
                    INSERT OR IGNORE INTO training_data 
                    (input_text, output_text, module, source)
                    VALUES (?, ?, ?, ?)
                ''', (variation, answer, module, "generated"))
                generated_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": f"Generated {generated_count} training examples",
            "status": "success",
            "count": generated_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/training/export", methods=["GET"])
def export_training_data():
    """Export training data as CSV"""
    conn = sqlite3.connect(knowledge_db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT input_text, output_text, module, source, created_at 
        FROM training_data 
        ORDER BY created_at DESC
    ''')
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['input_text', 'output_text', 'module', 'source', 'created_at'])
    
    for row in cursor.fetchall():
        writer.writerow(row)
    
    conn.close()
    
    # Return CSV file
    response = app.response_class(
        response=output.getvalue(),
        status=200,
        mimetype='text/csv'
    )
    response.headers['Content-Disposition'] = 'attachment; filename=training_data.csv'
    return response

@app.route("/train/start", methods=["POST"])
def start_training():
    """Start model training"""
    try:
        # Check if we have enough training data
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM training_data")
        training_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_items")
        knowledge_count = cursor.fetchone()[0]
        
        conn.close()
        
        total_examples = training_count + knowledge_count
        
        if total_examples < 5:
            return jsonify({
                "error": f"Not enough training data. Need at least 5 examples, but only have {total_examples}."
            }), 400
        
        return jsonify({
            "message": f"Model training started with {total_examples} examples.",
            "status": "success",
            "training_examples": total_examples
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ CONVERSATIONS ENDPOINT ============

@app.route("/conversations", methods=["GET"])
def get_conversations():
    """Get conversation logs"""
    limit = request.args.get('limit', 20, type=int)
    
    conn = sqlite3.connect(knowledge_db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, question, answer, module, source, confidence, 
               response_time, created_at 
        FROM conversation_logs 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    conversations = []
    for row in cursor.fetchall():
        conversations.append({
            "id": row[0],
            "user_id": row[1],
            "question": row[2],
            "answer": row[3],
            "module": row[4],
            "source": row[5],
            "confidence": row[6],
            "response_time": row[7],
            "created_at": row[8]
        })
    
    conn.close()
    
    return jsonify({"conversations": conversations, "count": len(conversations)})

# ============ ADMIN STATS ENDPOINT ============

@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    """Get detailed statistics for admin dashboard"""
    try:
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        
        # Count knowledge items
        cursor.execute("SELECT COUNT(*) FROM knowledge_items")
        knowledge_count = cursor.fetchone()[0]
        
        # Count knowledge items by module
        cursor.execute("SELECT module, COUNT(*) FROM knowledge_items GROUP BY module")
        module_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count training data
        cursor.execute("SELECT COUNT(*) FROM training_data")
        training_count = cursor.fetchone()[0]
        
        # Count conversations
        cursor.execute("SELECT COUNT(*) FROM conversation_logs")
        conversation_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "knowledge_count": knowledge_count,
            "knowledge_by_module": module_stats,
            "training_count": training_count,
            "conversation_count": conversation_count,
            "ollama_connected": is_ollama_running()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ OLLAMA STATUS ENDPOINT ============

@app.route("/ollama/status", methods=["GET"])
def ollama_status():
    """Get detailed Ollama status"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model.get("name", "") for model in models]
            
            return jsonify({
                "status": "running",
                "models": model_names,
                "deepseek_available": any("deepseek" in name.lower() for name in model_names)
            })
        else:
            return jsonify({"status": "error", "message": "Ollama API returned error"})
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "not_running", "message": "Ollama service not found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/ollama/test", methods=["POST"])
def test_ollama():
    """Test Ollama with a simple question"""
    try:
        payload = {
            "model": "deepseek-r1:1.5b",
            "prompt": "Say 'Hello, Ollama is working!' in one sentence.",
            "stream": False
        }
        
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        answer = result.get("response", "").strip()
        
        return jsonify({
            "status": "success",
            "response": answer,
            "working": True
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "working": False
        })

@app.route("/models/test", methods=["POST"])
def test_models():
    """Test all available models"""
    data = request.get_json()
    test_prompt = data.get('prompt', 'What is HCM?')
    
    models_to_test = ["sapience-hcm-assistant", "deepseek-r1:1.5b"]
    results = {}
    
    for model in models_to_test:
        try:
            payload = {
                "model": model,
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.3
                }
            }
            
            start_time = time.time()
            response = requests.post(OLLAMA_URL, json=payload, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "").strip()
                results[model] = {
                    "status": "success",
                    "response": answer,
                    "response_time": round(response_time, 2),
                    "working": len(answer) > 5
                }
            else:
                results[model] = {
                    "status": "error", 
                    "error": f"HTTP {response.status_code}",
                    "response_time": round(response_time, 2),
                    "working": False
                }
                
        except Exception as e:
            results[model] = {
                "status": "error",
                "error": str(e),
                "response_time": 0,
                "working": False
            }
    
    return jsonify({"test_results": results})

@app.route("/models/available", methods=["GET"])
def get_available_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return jsonify({
                "status": "success",
                "models": [model.get("name", "") for model in models],
                "count": len(models)
            })
        else:
            return jsonify({"status": "error", "message": "Cannot fetch models"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ============ DEBUG ENDPOINT ============

@app.route("/debug/routes", methods=["GET"])
def debug_routes():
    """Show all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                "endpoint": rule.rule,
                "methods": list(rule.methods)
            })
    return jsonify({"routes": routes})

if __name__ == "__main__":
    print("🚀 Starting Sapience HCM AI Help Desk API (Flask)...")
    print("🌐 Web server: http://localhost:5000")
    print("")
    print("📋 Available Endpoints:")
    print("  GET  /health          - System health check")
    print("  POST /chat            - Chat with AI")
    print("  GET  /knowledge       - Search knowledge base")
    print("  POST /knowledge       - Add knowledge item")
    print("  GET  /training        - Get training data")
    print("  POST /training/generate - Generate training data")
    print("  GET  /conversations   - Get conversation logs")
    print("  GET  /admin/stats     - Get system statistics")
    print("  GET  /ollama/status   - Check Ollama status")
    print("  POST /ollama/test     - Test Ollama connection")
    print("  GET  /debug/routes    - Show all routes")
    print("")
    
    app.run(host="0.0.0.0", port=5000, debug=True)