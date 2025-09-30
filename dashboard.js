// dashboard.js
const { createApp } = Vue;

createApp({
  data() {
    return {
      // API configuration
      API_BASE: "http://localhost:5000",

      // UI state
      activeTab: "chat",
      loading: false,
      trainingStatus: {
        loading: false,
        message: "",
        success: false,
      },

      // Tabs configuration
      tabs: [
        { id: "chat", name: "Chat", icon: "💬" },
        { id: "knowledge", name: "Knowledge Base", icon: "📚" },
        { id: "training", name: "Training", icon: "🎓" },
        { id: "analytics", name: "Analytics", icon: "📊" },
      ],

      // Stats data
      stats: {
        knowledgeCount: 0,
        trainingCount: 0,
        conversationCount: 0,
        aiStatus: false,
      },

      // Chat data
      userInput: "",
      selectedModule: "general",
      messages: [],

      // Knowledge base data
      knowledgeItems: [],
      newKnowledge: {
        module: "payroll",
        question: "",
        answer: "",
        keywords: "",
      },

      // Training data
      trainingData: [],

      // Analytics data
      conversations: [],
      autoDetectModule: true,
    };
  },

  mounted() {
    this.loadInitialData();
    this.setupAutoRefresh();
  },

  methods: {
    // ============ INITIALIZATION METHODS ============

    // Load all initial data
    async loadInitialData() {
      await Promise.all([
        this.loadStats(),
        this.loadKnowledgeItems(),
        this.loadTrainingData(),
        this.loadConversations(),
      ]);
    },

    // Setup auto-refresh for stats
    setupAutoRefresh() {
      setInterval(() => {
        this.loadStats();
      }, 30000); // Refresh every 30 seconds
    },

    // ============ UTILITY METHODS ============

    // Safe fetch with error handling
    async safeFetch(url, options = {}) {
      try {
        const response = await fetch(url, options);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("Response is not JSON");
        }

        return await response.json();
      } catch (error) {
        console.error(`Fetch error for ${url}:`, error);
        throw error;
      }
    },

    // Check Ollama status
    async checkOllamaStatus() {
      try {
        const response = await fetch(`${this.API_BASE}/ollama/status`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
      } catch (error) {
        console.error("Error checking Ollama status:", error);
        return {
          status: "error",
          message: "Cannot connect to Ollama service",
          deepseek_available: false,
        };
      }
    },

    // Show alert message
    showAlert(message, success) {
      // Create a simple toast notification
      const alertDiv = document.createElement("div");
      alertDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                z-index: 1000;
                background: ${success ? "#28a745" : "#dc3545"};
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                animation: slideIn 0.3s ease-out;
            `;
      alertDiv.textContent = message;

      document.body.appendChild(alertDiv);

      // Remove after 3 seconds
      setTimeout(() => {
        alertDiv.style.animation = "slideOut 0.3s ease-in";
        setTimeout(() => {
          if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
          }
        }, 300);
      }, 3000);
    },

    formatTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString();
    },

    // ============ STATS & DASHBOARD METHODS ============

    // Load system statistics
    async loadStats() {
      try {
        const statsData = await this.safeFetch(`${this.API_BASE}/admin/stats`);
        const ollamaStatus = await this.checkOllamaStatus();

        this.stats = {
          knowledgeCount: statsData.knowledge_count || 0,
          trainingCount: statsData.training_count || 0,
          conversationCount: statsData.conversation_count || 0,
          aiStatus:
            ollamaStatus.status === "running" &&
            ollamaStatus.deepseek_available,
        };
      } catch (error) {
        console.error("Error loading stats:", error);
        this.stats = {
          knowledgeCount: 0,
          trainingCount: 0,
          conversationCount: 0,
          aiStatus: false,
        };
      }
    },

    // ============ CHAT METHODS ============

    // Send message to AI
    async sendMessage() {
      if (!this.userInput.trim() || this.loading) return;

      const userMessage = {
        id: Date.now(),
        type: "user",
        sender: "You",
        content: this.userInput.trim(),
      };

      this.messages.push(userMessage);
      this.loading = true;

      const currentInput = this.userInput;
      this.userInput = "";

      try {
        const payload = {
          question: currentInput,
        };

        // Use auto-detection or specified module
        if (this.autoDetectModule) {
          payload.module = "auto";
        } else {
          payload.module = this.selectedModule;
        }

        const response = await fetch(`${this.API_BASE}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        const aiMessage = {
          id: Date.now() + 1,
          type: "ai",
          sender: "AI Assistant",
          content: data.answer,
          source: data.source,
          module: data.module,
          detectedModule: data.detected_module,
          confidence: data.confidence,
        };

        this.messages.push(aiMessage);

        // Scroll to bottom
        this.$nextTick(() => {
          const chatContainer = this.$refs.chatMessages;
          if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
          }
        });

        // Refresh conversations
        this.loadConversations();
      } catch (error) {
        console.error("Error sending message:", error);

        const errorMessage = {
          id: Date.now() + 1,
          type: "ai",
          sender: "System",
          content: "Sorry, I encountered an error. Please try again.",
        };

        this.messages.push(errorMessage);
      } finally {
        this.loading = false;
      }
    },

    // ============ KNOWLEDGE BASE METHODS ============

    // Load knowledge items
    async loadKnowledgeItems() {
      try {
        const response = await fetch(`${this.API_BASE}/knowledge?limit=100`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        this.knowledgeItems = data.results || [];
      } catch (error) {
        console.error("Error loading knowledge items:", error);
        this.knowledgeItems = [];
      }
    },

    // Add new knowledge item
    async addKnowledgeItem() {
      try {
        const payload = {
          module: this.newKnowledge.module,
          question: this.newKnowledge.question,
          answer: this.newKnowledge.answer,
          keywords: this.newKnowledge.keywords
            ? this.newKnowledge.keywords.split(",").map((k) => k.trim())
            : [],
        };

        const response = await fetch(`${this.API_BASE}/knowledge`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          // Reset form
          this.newKnowledge = {
            module: "payroll",
            question: "",
            answer: "",
            keywords: "",
          };

          // Reload items
          await this.loadKnowledgeItems();
          await this.loadStats();

          this.showAlert("Knowledge item added successfully!", true);
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to add knowledge item");
        }
      } catch (error) {
        console.error("Error adding knowledge item:", error);
        this.showAlert("Error adding knowledge item: " + error.message, false);
      }
    },

    // Delete knowledge item
    async deleteItem(id) {
      if (!confirm("Are you sure you want to delete this item?")) return;

      try {
        const response = await fetch(`${this.API_BASE}/knowledge/${id}`, {
          method: "DELETE",
        });

        if (response.ok) {
          await this.loadKnowledgeItems();
          this.showAlert("Item deleted successfully!", true);
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || "Failed to delete item");
        }
      } catch (error) {
        console.error("Error deleting item:", error);
        this.showAlert("Error deleting item: " + error.message, false);
      }
    },

    // Edit knowledge item (placeholder)
    editItem(item) {
      // For now, just log - you can implement edit functionality
      console.log("Edit item:", item);
      this.showAlert("Edit functionality coming soon!", true);
    },

    // ============ TRAINING METHODS ============

    // Generate training data
    async generateTrainingData() {
      this.trainingStatus.loading = true;
      this.trainingStatus.message =
        "Generating training data from knowledge base...";

      try {
        const response = await fetch(`${this.API_BASE}/training/generate`, {
          method: "POST",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || "Failed to generate training data"
          );
        }

        const data = await response.json();

        this.trainingStatus.message = `✅ ${data.message}`;
        this.trainingStatus.success = true;
        await this.loadTrainingData();
      } catch (error) {
        console.error("Error generating training data:", error);
        this.trainingStatus.message = `❌ Error: ${error.message}`;
        this.trainingStatus.success = false;
      } finally {
        this.trainingStatus.loading = false;
      }
    },

    // Train AI model
    async trainModel() {
      this.trainingStatus.loading = true;
      this.trainingStatus.message =
        "Training custom AI model... This may take several minutes.";

      try {
        const response = await fetch(`${this.API_BASE}/train/start`, {
          method: "POST",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || "Training failed");
        }

        const data = await response.json();

        this.trainingStatus.message = `✅ ${data.message}`;
        this.trainingStatus.success = true;
      } catch (error) {
        console.error("Error training model:", error);
        this.trainingStatus.message = `❌ Error: ${error.message}`;
        this.trainingStatus.success = false;
      } finally {
        this.trainingStatus.loading = false;
      }
    },

    // Export training data
    async exportTrainingData() {
      try {
        const response = await fetch(`${this.API_BASE}/training/export`);

        if (!response.ok) {
          throw new Error("Failed to export training data");
        }

        const blob = await response.blob();

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "training_data.csv";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        this.showAlert("Training data exported successfully!", true);
      } catch (error) {
        console.error("Error exporting training data:", error);
        this.showAlert(
          "Error exporting training data: " + error.message,
          false
        );
      }
    },

    // Load training data
    async loadTrainingData() {
      try {
        const response = await fetch(`${this.API_BASE}/training?limit=50`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        this.trainingData = data.training_data || [];
      } catch (error) {
        console.error("Error loading training data:", error);
        this.trainingData = [];
      }
    },

    // ============ ANALYTICS METHODS ============

    // Load conversation logs
    async loadConversations() {
      try {
        const response = await fetch(`${this.API_BASE}/conversations?limit=20`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        this.conversations = data.conversations || [];
      } catch (error) {
        console.error("Error loading conversations:", error);
        this.conversations = [];
      }
    },

    // ============ UI METHODS ============

    formatMessage(content) {
        if (!content) return '';
        
        // If it's already formatted with line breaks, preserve them
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold text
            .replace(/\n/g, '<br>') // Line breaks
            .replace(/(🎯|💰|👥|🖥️|💡|⏰)\s*<strong>(.*?)<\/strong>/g, '<div class="section-header">$1 <strong>$2</strong></div>') // Headers with emojis
            .replace(/(\d+)\.\s*(.*?)(?=<br>|$)/g, '<div class="step-item"><strong>$1.</strong> $2</div>') // Numbered steps
            .replace(/•\s*(.*?)(?=<br>|$)/g, '<div class="tip-item">$1</div>') // Bullet points
            .replace(/\*\*💡 Pro Tips:\*\*<br>(.*?)(?=<br><br>|$)/gs, '<div class="tips-section"><strong>💡 Pro Tips:</strong><br>$1</div>') // Tips section
            .replace(/\*\*✅ Important:\*\*<br>(.*?)(?=<br><br>|$)/gs, '<div class="important-section"><strong>✅ Important:</strong><br>$1</div>') // Important section
            .replace(/📍(.*?)$/, '<div class="footer-note">📍 $1</div>'); // Footer note
        
        return formatted;
    },

    // Switch between tabs
    openTab(tabName) {
      this.activeTab = tabName;
    }, // Add to your Vue methods in dashboard.js
    async testModels() {
      try {
        const prompt = "How do I process employee payroll?";
        const response = await fetch(`${this.API_BASE}/models/test`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt }),
        });

        const data = await response.json();
        console.log("Model test results:", data);

        // Show results in alert
        let message = "Model Test Results:\n";
        Object.entries(data.test_results).forEach(([model, result]) => {
          message += `\n${model}: ${
            result.working ? "✅ Working" : "❌ Failed"
          }\n`;
          message += `Time: ${result.response_time}s\n`;
          if (result.working) {
            message += `Response: ${result.response.substring(0, 100)}...\n`;
          }
        });

        alert(message);
      } catch (error) {
        console.error("Error testing models:", error);
        this.showAlert("Error testing models", false);
      }
    },

    async showAvailableModels() {
      try {
        const response = await fetch(`${this.API_BASE}/models/available`);
        const data = await response.json();

        if (data.status === "success") {
          let message = `Available Models (${data.count}):\n`;
          data.models.forEach((model) => {
            message += `\n• ${model}`;
          });
          alert(message);
        } else {
          this.showAlert("Cannot fetch models: " + data.message, false);
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        this.showAlert("Error fetching available models", false);
      }
    },
  },

  // Vue computed properties
  computed: {
    // Check if we have enough data for training
    canTrainModel() {
      return this.stats.knowledgeCount + this.stats.trainingCount >= 5;
    },

    // Get module breakdown for display
    moduleBreakdown() {
      const breakdown = {};
      this.knowledgeItems.forEach((item) => {
        breakdown[item.module] = (breakdown[item.module] || 0) + 1;
      });
      return breakdown;
    },
  },
}).mount("#app");
