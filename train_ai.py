# train_model.py
import sqlite3
import json
import requests
import subprocess
import os

class ModelTrainer:
    def __init__(self, db_path: str = "knowledge_base.db"):
        self.db_path = db_path
    
    def prepare_training_data(self):
        """Prepare training data from knowledge base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get knowledge items
        cursor.execute("SELECT question, answer, module FROM knowledge_items")
        knowledge_items = cursor.fetchall()
        
        # Get training data
        cursor.execute("SELECT input_text, output_text, module FROM training_data")
        training_items = cursor.fetchall()
        
        conn.close()
        
        all_data = knowledge_items + training_items
        print(f"📊 Prepared {len(all_data)} training examples")
        return all_data
    
    def create_modelfile(self, training_data):
        """Create Modelfile for Ollama"""
        
        system_prompt = """You are Sapience HCM Assistant, an AI expert in Human Capital Management software.
You provide accurate, concise, and helpful answers about payroll, attendance, HR management, and employee self-service.

Key Guidelines:
- Be professional, friendly, and solution-oriented
- Provide step-by-step instructions when asked for procedures
- Keep answers concise but comprehensive
- Focus only on Sapience HCM functionality"""

        modelfile = f'''FROM deepseek-r1:1.5b

# System prompt for Sapience HCM Assistant
SYSTEM """{system_prompt}"""

'''
        
        # Add training examples
        print("📝 Adding training examples...")
        for i, (input_text, output_text, module) in enumerate(training_data[:50]):  # Limit to 50 examples
            modelfile += f'\n# Example {i+1} from {module} module'
            modelfile += f'\nMESSAGE user "{input_text}"'
            modelfile += f'\nMESSAGE assistant "{output_text}"'
        
        return modelfile
    
    def train_model(self, model_name: str = "sapience-hcm-assistant"):
        """Train the custom model"""
        try:
            print("🚀 Starting model training...")
            
            # Check if Ollama is running
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=10)
                if response.status_code != 200:
                    print("❌ Ollama is not running. Please start Ollama first.")
                    return False
            except:
                print("❌ Cannot connect to Ollama. Please ensure it's installed and running.")
                return False
            
            # Prepare data
            training_data = self.prepare_training_data()
            
            if len(training_data) < 5:
                print("❌ Not enough training data. Need at least 5 examples.")
                return False
            
            # Create Modelfile
            modelfile_content = self.create_modelfile(training_data)
            
            # Save Modelfile
            with open("Modelfile", "w", encoding="utf-8") as f:
                f.write(modelfile_content)
            print("✅ Modelfile created")
            
            # Create model
            print("🔄 Creating model (this may take a few minutes)...")
            result = subprocess.run([
                "ollama", "create", model_name, "-f", "Modelfile"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Model '{model_name}' trained successfully!")
                
                # Clean up
                if os.path.exists("Modelfile"):
                    os.remove("Modelfile")
                
                return True
            else:
                print(f"❌ Training failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Training error: {str(e)}")
            return False

def main():
    print("=" * 50)
    print("Sapience HCM Model Trainer")
    print("=" * 50)
    
    trainer = ModelTrainer()
    
    # Check training data
    conn = sqlite3.connect("knowledge_base.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM knowledge_items")
    kb_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM training_data")
    training_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Knowledge Base: {kb_count} items")
    print(f"📚 Training Data: {training_count} items")
    print(f"📈 Total: {kb_count + training_count} training examples")
    
    if kb_count + training_count < 5:
        print("\n❌ Not enough training data. Please add more knowledge items first.")
        return
    
    # Train model
    model_name = "sapience-hcm-assistant"
    success = trainer.train_model(model_name)
    
    if success:
        print(f"\n🎉 Training completed!")
        print(f"💡 You can now use the custom model: {model_name}")
        print(f"🤖 The AI will now use your custom trained model!")
    else:
        print(f"\n💥 Training failed. Using base model for now.")

if __name__ == "__main__":
    main()