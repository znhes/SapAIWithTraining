// admin_dashboard.js
const API_BASE = 'http://localhost:8000';
let currentKnowledgePage = 1;
const itemsPerPage = 10;
let knowledgeData = [];
let filteredKnowledgeData = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadKnowledgeBase();
    loadTrainingData();
});

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    document.querySelector(`.tab[onclick="switchTab('${tabName}')"]`).classList.add('active');
}

// Alert system
function showAlert(message, type = 'success') {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert alert-${type}`;
    alert.style.display = 'block';
    
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

// Stats loading
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        document.getElementById('apiStatus').textContent = '✅';
        document.getElementById('totalKnowledge').textContent = data.knowledge_base_items || 0;
        
        // Load training data count
        const trainingResponse = await fetch(`${API_BASE}/training?limit=1`);
        const trainingData = await trainingResponse.json();
        document.getElementById('totalTraining').textContent = trainingData.count || 0;
        
        // Count unique modules (simplified)
        document.getElementById('totalModules').textContent = 6; // Fixed for now
        
    } catch (error) {
        document.getElementById('apiStatus').textContent = '❌';
        console.error('Error loading stats:', error);
    }
}

// Knowledge Base Management
async function loadKnowledgeBase() {
    try {
        const response = await fetch(`${API_BASE}/knowledge?query=&limit=1000`);
        knowledgeData = await response.json();
        filteredKnowledgeData = [...knowledgeData];
        renderKnowledgeTable();
        updateKnowledgePagination();
        loadStats(); // Refresh stats
    } catch (error) {
        console.error('Error loading knowledge base:', error);
        showAlert('Failed to load knowledge base', 'error');
    }
}

function renderKnowledgeTable() {
    const tbody = document.getElementById('knowledgeTableBody');
    const startIndex = (currentKnowledgePage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = filteredKnowledgeData.slice(startIndex, endIndex);

    if (pageData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No knowledge items found</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = pageData.map(item => `
        <tr>
            <td>${item.id}</td>
            <td><span class="module-badge">${item.module}</span></td>
            <td>${truncateText(item.question, 50)}</td>
            <td>${truncateText(item.answer, 70)}</td>
            <td>${renderKeywords(item.keywords)}</td>
            <td>${item.usage_count || 0}</td>
            <td class="actions">
                <button class="action-btn edit-btn" onclick="editKnowledgeItem(${item.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="action-btn delete-btn" onclick="deleteKnowledgeItem(${item.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </td>
        </tr>
    `).join('');
}

function renderKeywords(keywords) {
    if (!keywords || keywords.length === 0) return '-';
    return keywords.map(keyword => 
        `<span class="keyword-tag">${keyword}</span>`
    ).join('');
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function searchKnowledge() {
    const query = document.getElementById('searchKnowledge').value.toLowerCase();
    const moduleFilter = document.getElementById('moduleFilter').value;
    
    filteredKnowledgeData = knowledgeData.filter(item => {
        const matchesSearch = !query || 
            item.question.toLowerCase().includes(query) ||
            item.answer.toLowerCase().includes(query) ||
            (item.keywords && item.keywords.some(kw => kw.toLowerCase().includes(query)));
        
        const matchesModule = !moduleFilter || item.module === moduleFilter;
        
        return matchesSearch && matchesModule;
    });
    
    currentKnowledgePage = 1;
    renderKnowledgeTable();
    updateKnowledgePagination();
}

function filterByModule() {
    searchKnowledge(); // Reuse search function
}

function updateKnowledgePagination() {
    const totalPages = Math.ceil(filteredKnowledgeData.length / itemsPerPage);
    const pagination = document.getElementById('knowledgePagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `<button class="page-btn" ${currentKnowledgePage === 1 ? 'disabled' : ''} 
        onclick="changeKnowledgePage(${currentKnowledgePage - 1})">Previous</button>`;
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        paginationHTML += `<button class="page-btn ${i === currentKnowledgePage ? 'active' : ''}" 
            onclick="changeKnowledgePage(${i})">${i}</button>`;
    }
    
    // Next button
    paginationHTML += `<button class="page-btn" ${currentKnowledgePage === totalPages ? 'disabled' : ''} 
        onclick="changeKnowledgePage(${currentKnowledgePage + 1})">Next</button>`;
    
    pagination.innerHTML = paginationHTML;
}

function changeKnowledgePage(page) {
    currentKnowledgePage = page;
    renderKnowledgeTable();
}

// Knowledge Modal Functions
function openKnowledgeModal(itemId = null) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('knowledgeModalTitle');
    const form = document.getElementById('knowledgeForm');
    
    if (itemId) {
        title.textContent = 'Edit Knowledge Item';
        const item = knowledgeData.find(k => k.id === itemId);
        if (item) {
            document.getElementById('knowledgeId').value = item.id;
            document.getElementById('knowledgeModule').value = item.module;
            document.getElementById('knowledgeQuestion').value = item.question;
            document.getElementById('knowledgeAnswer').value = item.answer;
            
            // Clear and repopulate keywords
            const keywordsContainer = document.getElementById('keywordsContainer');
            keywordsContainer.innerHTML = '';
            if (item.keywords) {
                item.keywords.forEach(keyword => {
                    addKeywordToContainer(keyword);
                });
            }
        }
    } else {
        title.textContent = 'Add Knowledge Item';
        form.reset();
        document.getElementById('keywordsContainer').innerHTML = '';
    }
    
    modal.classList.add('active');
}

function closeKnowledgeModal() {
    document.getElementById('knowledgeModal').classList.remove('active');
}

// Keyword management
document.getElementById('keywordInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        const keyword = this.value.trim();
        if (keyword) {
            addKeywordToContainer(keyword);
            this.value = '';
        }
    }
});

function addKeywordToContainer(keyword) {
    const container = document.getElementById('keywordsContainer');
    const keywordElement = document.createElement('div');
    keywordElement.className = 'keyword-tag';
    keywordElement.innerHTML = `
        ${keyword}
        <button type="button" class="remove-keyword" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(keywordElement);
}

function getKeywordsFromContainer() {
    const container = document.getElementById('keywordsContainer');
    return Array.from(container.getElementsByClassName('keyword-tag')).map(tag => 
        tag.textContent.replace('×', '').trim()
    );
}

// Knowledge Form Submission
document.getElementById('knowledgeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        module: document.getElementById('knowledgeModule').value,
        question: document.getElementById('knowledgeQuestion').value,
        answer: document.getElementById('knowledgeAnswer').value,
        keywords: getKeywordsFromContainer()
    };
    
    const itemId = document.getElementById('knowledgeId').value;
    
    try {
        let response;
        if (itemId) {
            // Update existing item (you'll need to implement update endpoint)
            showAlert('Update functionality coming soon!', 'error');
            return;
        } else {
            // Add new item
            response = await fetch(`${API_BASE}/knowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
        }
        
        if (response.ok) {
            showAlert('Knowledge item saved successfully!');
            closeKnowledgeModal();
            loadKnowledgeBase();
        } else {
            throw new Error('Failed to save knowledge item');
        }
    } catch (error) {
        console.error('Error saving knowledge item:', error);
        showAlert('Failed to save knowledge item', 'error');
    }
});

// Edit Knowledge Item
// function editKnowledgeItem(id) {
//     openKnowledgeModal(id);
// }

// Delete Knowledge Item
async function deleteKnowledgeItem(id) {
    if (!confirm('Are you sure you want to delete this knowledge item?')) {
        return;
    }
    
    try {
        // Note: You'll need to implement delete endpoint in your API
        showAlert('Delete functionality coming soon!', 'error');
        // Once implemented:
        // const response = await fetch(`${API_BASE}/knowledge/${id}`, { method: 'DELETE' });
        // if (response.ok) {
        //     showAlert('Knowledge item deleted successfully!');
        //     loadKnowledgeBase();
        // }
    } catch (error) {
        console.error('Error deleting knowledge item:', error);
        showAlert('Failed to delete knowledge item', 'error');
    }
}

function refreshKnowledge() {
    loadKnowledgeBase();
}

// Training Data Management
async function loadTrainingData() {
    try {
        const response = await fetch(`${API_BASE}/training?limit=1000`);
        const data = await response.json();
        renderTrainingTable(data.training_data || []);
    } catch (error) {
        console.error('Error loading training data:', error);
        showAlert('Failed to load training data', 'error');
    }
}

function renderTrainingTable(data) {
    const tbody = document.getElementById('trainingTableBody');
    
    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No training data found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = data.map(item => `
        <tr>
            <td>${item.id || '-'}</td>
            <td>${truncateText(item.input, 60)}</td>
            <td>${truncateText(item.output, 60)}</td>
            <td>${item.module}</td>
            <td>${item.source || 'manual'}</td>
            <td class="actions">
                <button class="action-btn delete-btn" onclick="deleteTrainingData(${item.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </td>
        </tr>
    `).join('');
}

// Training Modal Functions
function openTrainingModal() {
    document.getElementById('trainingModal').classList.add('active');
}

function closeTrainingModal() {
    document.getElementById('trainingModal').classList.remove('active');
    document.getElementById('trainingForm').reset();
}

document.getElementById('trainingForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        input_text: document.getElementById('trainingInput').value,
        output_text: document.getElementById('trainingOutput').value,
        module: document.getElementById('trainingModule').value,
        source: document.getElementById('trainingSource').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/training`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showAlert('Training data added successfully!');
            closeTrainingModal();
            loadTrainingData();
            loadStats();
        } else {
            throw new Error('Failed to add training data');
        }
    } catch (error) {
        console.error('Error adding training data:', error);
        showAlert('Failed to add training data', 'error');
    }
});

async function deleteTrainingData(id) {
    if (!confirm('Are you sure you want to delete this training data?')) {
        return;
    }
    
    try {
        // Note: You'll need to implement delete endpoint for training data
        showAlert('Delete functionality for training data coming soon!', 'error');
    } catch (error) {
        console.error('Error deleting training data:', error);
        showAlert('Failed to delete training data', 'error');
    }
}

function exportTrainingData() {
    // Implementation for exporting training data
    showAlert('Export functionality coming soon!', 'error');
}

// Analytics
function loadAnalytics() {
    // Basic analytics implementation
    document.getElementById('totalConversations').textContent = '0';
    document.getElementById('kbSuccessRate').textContent = '0%';
    document.getElementById('avgResponseTime').textContent = '0ms';
    document.getElementById('topModule').textContent = '-';
    
    showAlert('Analytics data loaded', 'success');
}

// Add these functions to admin_dashboard.js

// Enhanced Knowledge Item Editing
async function editKnowledgeItem(id) {
    try {
        const response = await fetch(`${API_BASE}/knowledge/${id}`);
        const item = await response.json();
        
        openKnowledgeModal(id);
        
        // Populate form with existing data
        document.getElementById('knowledgeId').value = item.id;
        document.getElementById('knowledgeModule').value = item.module;
        document.getElementById('knowledgeQuestion').value = item.question;
        document.getElementById('knowledgeAnswer').value = item.answer;
        
        // Clear and repopulate keywords
        const keywordsContainer = document.getElementById('keywordsContainer');
        keywordsContainer.innerHTML = '';
        if (item.keywords) {
            item.keywords.forEach(keyword => {
                addKeywordToContainer(keyword);
            });
        }
    } catch (error) {
        console.error('Error loading knowledge item:', error);
        showAlert('Failed to load knowledge item for editing', 'error');
    }
}

// Enhanced Knowledge Item Deletion
async function deleteKnowledgeItem(id) {
    if (!confirm('Are you sure you want to delete this knowledge item?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/knowledge/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Knowledge item deleted successfully!');
            loadKnowledgeBase();
        } else {
            throw new Error('Failed to delete knowledge item');
        }
    } catch (error) {
        console.error('Error deleting knowledge item:', error);
        showAlert('Failed to delete knowledge item', 'error');
    }
}

// Enhanced Training Data Deletion
async function deleteTrainingData(id) {
    if (!confirm('Are you sure you want to delete this training data?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/training/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Training data deleted successfully!');
            loadTrainingData();
            loadStats();
        } else {
            throw new Error('Failed to delete training data');
        }
    } catch (error) {
        console.error('Error deleting training data:', error);
        showAlert('Failed to delete training data', 'error');
    }
}

// Enhanced Knowledge Form Submission
document.getElementById('knowledgeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        module: document.getElementById('knowledgeModule').value,
        question: document.getElementById('knowledgeQuestion').value,
        answer: document.getElementById('knowledgeAnswer').value,
        keywords: getKeywordsFromContainer()
    };
    
    const itemId = document.getElementById('knowledgeId').value;
    
    try {
        let response;
        if (itemId) {
            // Update existing item
            response = await fetch(`${API_BASE}/knowledge/${itemId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
        } else {
            // Add new item
            response = await fetch(`${API_BASE}/knowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
        }
        
        if (response.ok) {
            showAlert(`Knowledge item ${itemId ? 'updated' : 'saved'} successfully!`);
            closeKnowledgeModal();
            loadKnowledgeBase();
        } else {
            throw new Error(`Failed to ${itemId ? 'update' : 'save'} knowledge item`);
        }
    } catch (error) {
        console.error('Error saving knowledge item:', error);
        showAlert(`Failed to ${itemId ? 'update' : 'save'} knowledge item`, 'error');
    }
});

// Enhanced Stats Loading
async function loadStats() {
    try {
        const healthResponse = await fetch(`${API_BASE}/health`);
        const healthData = await healthResponse.json();
        
        const statsResponse = await fetch(`${API_BASE}/stats`);
        const statsData = await statsResponse.json();
        
        document.getElementById('apiStatus').textContent = '✅';
        document.getElementById('totalKnowledge').textContent = healthData.knowledge_base_items || 0;
        document.getElementById('totalTraining').textContent = healthData.training_data_items || 0;
        document.getElementById('totalModules').textContent = Object.keys(statsData.module_breakdown || {}).length;
        
        // Analytics tab stats
        document.getElementById('totalConversations').textContent = statsData.total_conversations || 0;
        document.getElementById('kbSuccessRate').textContent = `${Math.round((statsData.kb_success_rate || 0) * 100)}%`;
        document.getElementById('avgResponseTime').textContent = '150ms'; // Placeholder
        document.getElementById('topModule').textContent = getTopModule(statsData.module_breakdown);
        
    } catch (error) {
        document.getElementById('apiStatus').textContent = '❌';
        console.error('Error loading stats:', error);
    }
}

function getTopModule(moduleBreakdown) {
    if (!moduleBreakdown) return '-';
    const modules = Object.entries(moduleBreakdown);
    if (modules.length === 0) return '-';
    return modules.sort((a, b) => b[1] - a[1])[0][0];
}