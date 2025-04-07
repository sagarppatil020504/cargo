// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
};

// API Client
class ItemManagementAPI {
    static async handleResponse(response) {
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'API request failed');
        }
        return response.json();
    }

    // Items
    static async addItem(itemData) {
        const response = await fetch(`${API_BASE_URL}/items`, {
            method: 'POST',
            headers,
            body: JSON.stringify(itemData)
        });
        return this.handleResponse(response);
    }

    static async getItems() {
        const response = await fetch(`${API_BASE_URL}/items`, { headers });
        return this.handleResponse(response);
    }

    // Containers
    static async addContainer(containerData) {
        const response = await fetch(`${API_BASE_URL}/containers`, {
            method: 'POST',
            headers,
            body: JSON.stringify(containerData)
        });
        return this.handleResponse(response);
    }

    static async getContainers() {
        const response = await fetch(`${API_BASE_URL}/containers`, { headers });
        return this.handleResponse(response);
    }

    // Placements
    static async runPlacement() {
        const response = await fetch(`${API_BASE_URL}/placements`, {
            method: 'POST',
            headers
        });
        return this.handleResponse(response);
    }

    static async getPlacements() {
        const response = await fetch(`${API_BASE_URL}/placements`, { headers });
        return this.handleResponse(response);
    }
}

// UI Utilities
class ItemManagementUI {
    static showLoader(element) {
        element.innerHTML = '<div class="loader">Loading...</div>';
    }

    static showError(message) {
        alert(`Error: ${message}`);
    }

    static updateList(element, items, templateFn) {
        element.innerHTML = items.map(templateFn).join('');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the page
    loadItems();
    loadContainers();
    loadPlacements();

    // Form submissions
    document.getElementById('itemForm').addEventListener('submit', handleItemSubmit);
    document.getElementById('containerForm').addEventListener('submit', handleContainerSubmit);
    document.getElementById('runPlacement').addEventListener('click', handleRunPlacement);
});

// Handler functions would be defined here...
