# app.py (Compatible with older versions)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import uvicorn
import sqlite3
import json
import time
import re
import csv
import io


from database import knowledge_db

app = FastAPI(
    title="Sapience HCM AI Help Desk API",
    description="AI-powered help desk for Sapience HCM",
    version="1.0.0"
)

# CORS Support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatRequest(BaseModel):
    question: str
    module: str = "general"
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    source: str
    module: str
    confidence: float
    response_time: float

class KnowledgeItemRequest(BaseModel):
    module: str
    question: str
    answer: str
    keywords: Optional[List[str]] = None

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"

def is_ollama_running():
    """Check if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def ask_ollama(question: str, module: str = "general") -> str:
    """Send question to Ollama - try custom model first"""
    
    # Quick local greeting handling
    if re.match(r'^\s*(hi|hello|hey|hiya|yo)[\s!.]*$', question, flags=re.I):
        return "Hello 👋 How can I assist you with Sapience HCM today?"
    
    # Try custom model first, then fallback
    models_to_try = ["sapience-hcm-assistant", "deepseek-r1:1.5b"]
    
    for model in models_to_try:
        try:
            system_prompt = f"You are Sapience HCM Assistant specialized in {module} module. Provide concise, step-by-step answers about HCM processes."
            
            payload = {
                "model": model,
                "prompt": f"{system_prompt}\n\nUser question: {question}",
                "stream": False
            }
            
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            answer = (result.get("response") or result.get("text") or "").strip()
            
            if answer and "error" not in answer.lower():
                return answer
                
        except Exception:
            continue  # Try next model
    
    return "I apologize, but I'm having trouble processing your request right now."
# API Routes
@app.get("/")
async def root():
    return {"message": "Sapience HCM AI Help Desk API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Check system health"""
    ollama_connected = is_ollama_running()
    
    return {
        "status": "healthy",
        "ollama_connected": ollama_connected,
        "message": "API is running"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with AI help desk"""
    start_time = time.time()
    
    # 1. Search knowledge base first
    kb_results = knowledge_db.search_knowledge(request.question, request.module, limit=3)
    
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
            request.user_id, request.question, best_match['answer'],
            request.module, "knowledge_base", 0.95, response_time
        )
        
        return ChatResponse(
            answer=best_match['answer'],
            source="knowledge_base",
            module=request.module,
            confidence=0.95,
            response_time=response_time
        )
    
    # 2. Use Ollama for complex questions
    if is_ollama_running():
        ai_answer = ask_ollama(request.question, request.module)
        response_time = time.time() - start_time
        
        knowledge_db.log_conversation(
            request.user_id, request.question, ai_answer,
            request.module, "ai_model", 0.80, response_time
        )
        
        return ChatResponse(
            answer=ai_answer,
            source="ai_model",
            module=request.module,
            confidence=0.80,
            response_time=response_time
        )
    else:
        response_time = time.time() - start_time
        fallback_answer = "I can help with HCM questions. Try asking about payroll, attendance, or employee self-service."
        
        knowledge_db.log_conversation(
            request.user_id, request.question, fallback_answer,
            request.module, "fallback", 0.50, response_time
        )
        
        return ChatResponse(
            answer=fallback_answer,
            source="fallback",
            module=request.module,
            confidence=0.50,
            response_time=response_time
        )

@app.post("/knowledge")
async def add_knowledge_item(request: KnowledgeItemRequest):
    """Add new item to knowledge base"""
    knowledge_db.add_knowledge_item(
        request.module, 
        request.question, 
        request.answer, 
        request.keywords
    )
    return {"message": "Knowledge item added successfully", "status": "success"}

@app.get("/knowledge")
async def search_knowledge(query: str = "", module: Optional[str] = None, limit: int = 10):
    """Search knowledge base"""
    results = knowledge_db.search_knowledge(query, module, limit)
    return {"results": results, "count": len(results)}


if __name__ == "__main__":
    print("🚀 Starting Sapience HCM AI Help Desk API...")
    print("🌐 Web server: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)