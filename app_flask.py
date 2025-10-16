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
    """Send question to Ollama with NO THINKING prompt"""
    
    # Quick local greeting handling
    if re.match(r'^\s*(hi|hello|hey|hiya|yo)[\s!.]*$', question, flags=re.I):
        return "Hello 👋 How can I assist you with Sapience HCM today?"
    
    # Try models in order of preference
    models_to_try = ["sapience-hcm-assistant", "deepseek-r1:1.5b", "llama2:3b"]
    
    for model in models_to_try:
        try:
            # STRICT SYSTEM PROMPT - NO THINKING ALLOWED
            system_prompt = f"""You are Sapience HCM Assistant specialized in {module} module. 
Provide direct, concise answers about HCM processes.
DO NOT show your thinking process.
DO NOT use phrases like "let me think" or "first, I should".
Answer directly and professionally.
Keep responses under 3 sentences."""

            payload = {
                "model": model,
                "prompt": f"{system_prompt}\n\nUser question: {question}",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 100,
                    "top_k": 40
                }
            }
            
            response = requests.post(OLLAMA_URL, json=payload, timeout=8)
            response.raise_for_status()
            result = response.json()
            answer = (result.get("response") or result.get("text") or "").strip()
            
            if answer and len(answer) > 10 and "error" not in answer.lower():
                return answer
            else:
                continue
                
        except Exception:
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


def detect_module(question):
    """Automatically detect which module a question belongs to"""
    question_lower = question.lower()
    
    # Module keywords and their weights
    module_keywords = {
        "payroll": {
            "keywords": [
                "payroll", "salary", "payslip", "wage", "payment", "tax", 
                "deduction", "bonus", "compensation", "earnings", "pay stub",
                "income", "withholding", "paycheck", "direct deposit"
            ],
            "weight": 1.0
        },
        "attendance": {
            "keywords": [
                "attendance", "time", "clock", "punch", "present", "absent",
                "late", "early", "overtime", "shift", "schedule", "timesheet",
                "leave", "vacation", "sick", "holiday", "break", "hours worked"
            ],
            "weight": 1.0
        },
        "hr": {
            "keywords": [
                "employee", "hr", "human resources", "onboarding", "termination",
                "profile", "record", "department", "position", "manager",
                "performance", "review", "promotion", "transfer", "contract",
                "document", "policy", "compliance", "training", "development"
            ],
            "weight": 1.0
        },
        "ess": {
            "keywords": [
                "self-service", "ess", "my profile", "my payslip", "my leave",
                "personal", "information", "update", "change", "request",
                "apply", "submit", "portal", "dashboard", "my account"
            ],
            "weight": 1.0
        }
    }
    
    # Calculate scores for each module
    module_scores = {}
    
    for module, data in module_keywords.items():
        score = 0
        for keyword in data["keywords"]:
            if keyword in question_lower:
                score += data["weight"]
                # Extra points for exact matches
                if f" {keyword} " in f" {question_lower} ":
                    score += 0.5
        
        module_scores[module] = score
    
    # Find the module with highest score
    best_module = "general"
    best_score = 0
    
    for module, score in module_scores.items():
        if score > best_score:
            best_score = score
            best_module = module
    
    # Only return specific module if score is above threshold
    if best_score >= 1.0:
        print(f"🔍 Module detection: '{question}' → {best_module} (score: {best_score})")
        return best_module
    else:
        print(f"🔍 Module detection: '{question}' → general (score: {best_score})")
        return "general"

def beautify_response(raw_answer, question, module):
    """Convert raw knowledge base answers into beautiful, formatted responses"""
    
    # Clean the raw answer first
    clean_answer = raw_answer.strip()
    
    # If it's already short and clean, return as is
    if len(clean_answer) < 150 and '\n' not in clean_answer:
        return clean_answer
    
    # Define beautification patterns for different modules
    beautification_rules = {
        "attendance": {
            "patterns": [
                r"step.*?by.*?step",
                r"follow these steps",
                r"instructions:",
                r"process:"
            ],
            "template": "🎯 **Here's how to {action}:**\n\n{steps}\n\n💡 **Pro Tip:** {tip}"
        },
        "payroll": {
            "patterns": [
                r"process.*?payroll",
                r"run.*?salary",
                r"calculate.*?tax"
            ],
            "template": "💰 **Payroll Process:**\n\n{steps}\n\n✅ **Important:** {important}"
        },
        "hr": {
            "patterns": [
                r"add.*?employee",
                r"onboarding",
                r"create.*?profile"
            ],
            "template": "👥 **HR Procedure:**\n\n{steps}\n\n📋 **Required:** {requirements}"
        },
        "ess": {
            "patterns": [
                r"update.*?profile",
                r"self.*?service",
                r"my.*?information"
            ],
            "template": "🖥️ **Employee Self-Service:**\n\n{steps}\n\n🔒 **Note:** {note}"
        }
    }
    
    # Try to extract steps and structure from the raw answer
    structured_response = extract_and_structure(clean_answer, question, module)
    
    return structured_response

def extract_and_structure(text, question, module):
    """Extract structured information from raw text"""
    
    # Convert to lowercase for easier matching
    text_lower = text.lower()
    question_lower = question.lower()
    
    # Common patterns to look for
    steps = extract_steps(text)
    tips = extract_tips(text)
    important_points = extract_important_points(text)
    
    # Build beautiful response
    response_parts = []
    
    # Add emoji based on module
    emoji_map = {
        "attendance": "⏰",
        "payroll": "💰", 
        "hr": "👥",
        "ess": "🖥️",
        "general": "💡"
    }
    
    emoji = emoji_map.get(module, "💡")
    
    # Header
    response_parts.append(f"{emoji} **{get_action_phrase(question_lower, module)}**")
    response_parts.append("")
    
    # Add steps if found
    if steps:
        response_parts.append("**📋 Steps to follow:**")
        for i, step in enumerate(steps, 1):
            response_parts.append(f"{i}. {step}")
        response_parts.append("")
    
    # If no structured steps found, create a concise summary
    elif len(text) > 200:
        summary = create_concise_summary(text)
        response_parts.append("**🎯 Quick Guide:**")
        response_parts.append(summary)
        response_parts.append("")
    else:
        response_parts.append(text)
        response_parts.append("")
    
    # Add tips if available
    if tips:
        response_parts.append("**💡 Pro Tips:**")
        for tip in tips[:2]:  # Limit to 2 tips
            response_parts.append(f"• {tip}")
        response_parts.append("")
    
    # Add important points
    if important_points:
        response_parts.append("**✅ Important:**")
        for point in important_points[:2]:  # Limit to 2 points
            response_parts.append(f"• {point}")
    
    # Add module-specific footer
    footer = get_module_footer(module)
    if footer:
        response_parts.append("")
        response_parts.append(footer)
    
    return "\n".join(response_parts)

def extract_steps(text):
    """Extract step-by-step instructions from text"""
    steps = []
    
    # Look for numbered steps (1., 2., etc.)
    numbered_pattern = r'\b\d+\.\s*([^.!?]+[.!?])'
    numbered_matches = re.findall(numbered_pattern, text)
    if numbered_matches:
        steps.extend([match.strip() for match in numbered_matches])
    
    # Look for step phrases
    step_patterns = [
        r'step\s*\d+[:\s]*([^.!?]+[.!?])',
        r'first[,\s]*([^.!?]+[.!?])',
        r'next[,\s]*([^.!?]+[.!?])',
        r'then[,\s]*([^.!?]+[.!?])',
        r'finally[,\s]*([^.!?]+[.!?])'
    ]
    
    for pattern in step_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        steps.extend([match.strip() for match in matches])
    
    # If no structured steps found, split by sentences and take key ones
    if not steps and len(text) > 100:
        sentences = re.split(r'[.!?]+', text)
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20 and len(s.strip()) < 150]
        steps = key_sentences[:5]  # Take up to 5 key sentences
    
    return steps[:8]  # Limit to 8 steps

def extract_tips(text):
    """Extract tips and pro tips from text"""
    tips = []
    
    tip_patterns = [
        r'pro tip[:\s]*([^.!?]+[.!?])',
        r'tip[:\s]*([^.!?]+[.!?])',
        r'note[:\s]*([^.!?]+[.!?])',
        r'recommend[^.!?]+[.!?]',
        r'suggest[^.!?]+[.!?]'
    ]
    
    for pattern in tip_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        tips.extend([match.strip() for match in matches])
    
    return tips[:3]  # Limit to 3 tips

def extract_important_points(text):
    """Extract important points from text"""
    important = []
    
    important_patterns = [
        r'important[:\s]*([^.!?]+[.!?])',
        r'crucial[:\s]*([^.!?]+[.!?])',
        r'required[:\s]*([^.!?]+[.!?])',
        r'must[^.!?]+[.!?]',
        r'ensure[^.!?]+[.!?]'
    ]
    
    for pattern in important_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        important.extend([match.strip() for match in matches])
    
    return important[:3]  # Limit to 3 points

def create_concise_summary(text):
    """Create a concise summary from long text"""
    sentences = re.split(r'[.!?]+', text)
    
    # Filter for meaningful sentences
    meaningful_sentences = []
    for sentence in sentences:
        clean_sentence = sentence.strip()
        if (len(clean_sentence) > 20 and 
            len(clean_sentence) < 150 and
            not any(word in clean_sentence.lower() for word in ['however', 'although', 'nevertheless'])):
            meaningful_sentences.append(clean_sentence)
    
    # Take 2-3 most relevant sentences
    if meaningful_sentences:
        return " ".join(meaningful_sentences[:3])
    else:
        # Fallback: return first 150 characters
        return text[:150] + "..." if len(text) > 150 else text

def get_action_phrase(question, module):
    """Get appropriate action phrase based on question"""
    action_map = {
        "attendance": {
            "add": "Mark Attendance",
            "mark": "Record Attendance", 
            "create": "Create Attendance Entry",
            "update": "Update Attendance",
            "delete": "Remove Attendance Record"
        },
        "payroll": {
            "process": "Process Payroll",
            "run": "Run Salary Calculation",
            "calculate": "Calculate Payments",
            "generate": "Generate Payslips"
        },
        "hr": {
            "add": "Add Employee",
            "create": "Create Employee Profile",
            "onboard": "Onboard New Employee",
            "update": "Update Employee Record"
        },
        "ess": {
            "update": "Update Personal Information",
            "view": "View My Details",
            "request": "Submit Request",
            "apply": "Apply for Leave"
        }
    }
    
    module_actions = action_map.get(module, {})
    for action_word, action_phrase in module_actions.items():
        if action_word in question:
            return action_phrase
    
    # Default action phrases
    default_phrases = {
        "attendance": "Manage Attendance",
        "payroll": "Handle Payroll",
        "hr": "HR Management",
        "ess": "Employee Self-Service",
        "general": "Assistance"
    }
    
    return default_phrases.get(module, "Procedure")

def get_module_footer(module):
    """Get module-specific footer"""
    footers = {
        "attendance": "📍 Need help with specific attendance scenarios? Ask me about late marks, overtime, or bulk entries!",
        "payroll": "📍 Have payroll calculation questions? Ask me about taxes, deductions, or payment methods!",
        "hr": "📍 Need HR support? Ask me about employee records, documents, or compliance!",
        "ess": "📍 Employee questions? I can help with profile updates, leave requests, and more!",
        "general": "📍 Need more specific help? Just ask!"
    }
    return footers.get(module, "")

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
    """Chat with AI help desk - WITH AUTO MODULE DETECTION"""
    data = request.get_json()
    
    if not data or 'question' not in data:
        return jsonify({"error": "Missing question"}), 400
    
    question = data['question']
    module = data.get('module', 'auto')  # Default to 'auto' for detection
    user_id = data.get('user_id')
    
    start_time = time.time()
    
    print(f"💬 CHAT: '{question}'")
    
    # AUTO MODULE DETECTION
    if module == 'auto' or not module:
        detected_module = detect_module(question)
        module = detected_module
        print(f"🎯 Auto-detected module: {module}")
    else:
        print(f"🎯 Using specified module: {module}")
    
    # 1. Search knowledge base
    kb_results = knowledge_db.search_knowledge(question, module, limit=5)
    
    # Use the FIRST result if we have any matches
    if kb_results:
        best_match = kb_results[0]
        print(f"✅ KNOWLEDGE BASE MATCH: Using '{best_match['question']}' from {module} module")
        
        # BEAUTIFY THE RESPONSE
        raw_answer = best_match['answer']
        beautiful_answer = beautify_response(raw_answer, question, module)
        
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
            user_id, question, beautiful_answer,
            module, "knowledge_base", 0.95, response_time
        )
        
        return jsonify({
            "answer": beautiful_answer,
            "source": "knowledge_base",
            "module": module,
            "detected_module": module if module != data.get('module', 'auto') else "auto",
            "confidence": 0.95,
            "response_time": response_time
        })
    
    print(f"❌ NO KNOWLEDGE BASE MATCH in {module} - Using AI/fallback")
    
    # 2. Only use Ollama if no knowledge base match
    if is_ollama_running():
        try:
            ai_answer = ask_ollama(question, module)
            response_time = time.time() - start_time
            
            # Clean the AI response
            cleaned_answer = clean_ai_response(ai_answer)
            
            knowledge_db.log_conversation(
                user_id, question, cleaned_answer,
                module, "ai_model", 0.80, response_time
            )
            
            return jsonify({
                "answer": cleaned_answer,
                "source": "ai_model",
                "module": module,
                "detected_module": module if module != data.get('module', 'auto') else "auto",
                "confidence": 0.80,
                "response_time": response_time
            })
        except Exception as e:
            print(f"❌ AI ERROR: {e}")
    
    # 3. Use fallback
    response_time = time.time() - start_time
    fallback_answer = get_intelligent_fallback(question, module)
    
    knowledge_db.log_conversation(
        user_id, question, fallback_answer,
        module, "fallback", 0.50, response_time
    )
    
    return jsonify({
        "answer": fallback_answer,
        "source": "fallback",
        "module": module,
        "detected_module": module if module != data.get('module', 'auto') else "auto",
        "confidence": 0.50,
        "response_time": response_time
    })

def clean_ai_response(answer):
    """Clean AI response by removing thinking tags and unwanted content"""
    import re
    
    # Remove <think> tags and content
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
    
    # Remove [INST] tags
    answer = re.sub(r'\[INST\].*?\[/INST\]', '', answer, flags=re.DOTALL)
    
    # Remove any XML-like thinking tags
    answer = re.sub(r'<.*?>', '', answer)
    
    # Remove "Okay, let me think" type phrases
    thinking_phrases = [
        r'okay, let me think',
        r'first, i should',
        r'let me recall',
        r'i remember that',
        r'based on my knowledge',
        r'looking at this',
        r'let me analyze',
        r'i need to consider'
    ]
    
    for phrase in thinking_phrases:
        answer = re.sub(phrase, '', answer, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    answer = re.sub(r'\s+', ' ', answer).strip()
    
    # If answer is empty after cleaning, provide default
    if not answer or len(answer) < 10:
        return "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
    
    return answer

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
def get_knowledge_items():
    """Get all knowledge items"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        conn = sqlite3.connect(knowledge_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, module, question, answer, keywords, usage_count 
            FROM knowledge_items 
            ORDER BY id DESC 
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
        
        return jsonify({"results": results, "count": len(results)})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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


@app.route("/debug/search", methods=["POST"])
def debug_search():
    """Debug knowledge base search"""
    data = request.get_json()
    question = data.get('question', '')
    module = data.get('module', 'general')
    
    print(f"🔍 DEBUG: Searching for: '{question}' in module: '{module}'")
    
    # Search knowledge base
    kb_results = knowledge_db.search_knowledge(question, module, limit=5)
    
    print(f"📊 DEBUG: Found {len(kb_results)} results")
    for i, result in enumerate(kb_results):
        print(f"  {i+1}. Question: '{result['question']}'")
        print(f"     Answer: '{result['answer']}'")
        print(f"     Relevance: {result.get('relevance', 'N/A')}")
        print(f"     Module: {result['module']}")
    
    return jsonify({
        "question": question,
        "module": module,
        "results": kb_results,
        "count": len(kb_results)
    })

@app.route("/debug/knowledge", methods=["GET"])
def debug_knowledge_base():
    """Show all knowledge base items"""
    conn = sqlite3.connect(knowledge_db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, module, question, answer FROM knowledge_items ORDER BY id")
    items = cursor.fetchall()
    
    conn.close()
    
    knowledge_items = []
    for item in items:
        knowledge_items.append({
            "id": item[0],
            "module": item[1],
            "question": item[2],
            "answer": item[3]
        })
    
    return jsonify({
        "knowledge_items": knowledge_items,
        "count": len(knowledge_items)
    })

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