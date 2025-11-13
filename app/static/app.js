class ProductImporter {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.currentTab = 'upload';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.showTab('upload');
        this.loadProducts();
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.showTab(e.target.dataset.tab);
            });
        });

        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        // Bulk delete
        document.getElementById('bulkDeleteBtn').addEventListener('click', () => {
            this.bulkDeleteProducts();
        });

        // Product form
        document.getElementById('productForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveProduct();
        });

        // Filters
        document.getElementById('applyFilters').addEventListener('click', () => {
            this.currentPage = 1;
            this.loadProducts();
        });

        document.getElementById('clearFilters').addEventListener('click', () => {
            document.querySelectorAll('.filter-input').forEach(input => {
                input.value = '';
            });
            this.currentPage = 1;
            this.loadProducts();
        });

        // Webhook form
        document.getElementById('webhookForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveWebhook();
        });
    }

    showTab(tabName) {
        // Update tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

        this.currentTab = tabName;

        if (tabName === 'products') {
            this.loadProducts();
        } else if (tabName === 'webhooks') {
            this.loadWebhooks();
        }
    }

    async handleFileUpload(file) {
        if (!file.name.endsWith('.csv')) {
            this.showAlert('Please upload a CSV file', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        this.showUploadProgress(0, 'Starting upload...');

        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result = await response.json();
            this.monitorUploadProgress(result.task_id, result.job_id);
            
        } catch (error) {
            this.showAlert('Upload failed: ' + error.message, 'error');
            this.hideUploadProgress();
        }
    }

    async monitorUploadProgress(taskId, jobId) {
        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/tasks/${taskId}`);
                const data = await response.json();

                if (data.state === 'PROGRESS' || data.state === 'SUCCESS') {
                    const progress = (data.current / data.total) * 100;
                    this.showUploadProgress(progress, data.status);

                    if (data.state === 'SUCCESS') {
                        this.showAlert('File imported successfully!', 'success');
                        this.hideUploadProgress();
                        this.loadProducts(); // Refresh product list
                    } else {
                        setTimeout(checkProgress, 1000);
                    }
                } else if (data.state === 'FAILURE') {
                    this.showAlert('Import failed: ' + data.status, 'error');
                    this.hideUploadProgress();
                } else {
                    setTimeout(checkProgress, 1000);
                }
            } catch (error) {
                this.showAlert('Error checking progress: ' + error.message, 'error');
                this.hideUploadProgress();
            }
        };

        checkProgress();
    }

    showUploadProgress(percent, status) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const uploadProgress = document.getElementById('uploadProgress');

        progressFill.style.width = percent + '%';
        progressText.textContent = status;
        uploadProgress.classList.remove('hidden');
    }

    hideUploadProgress() {
        document.getElementById('uploadProgress').classList.add('hidden');
    }

    async loadProducts() {
        const skuFilter = document.getElementById('filterSku').value;
        const nameFilter = document.getElementById('filterName').value;
        const activeFilter = document.getElementById('filterActive').value;
        const descFilter = document.getElementById('filterDescription').value;

        let url = `/api/products/?skip=${(this.currentPage - 1) * this.pageSize}&limit=${this.pageSize}`;
        
        if (skuFilter) url += `&sku=${encodeURIComponent(skuFilter)}`;
        if (nameFilter) url += `&name=${encodeURIComponent(nameFilter)}`;
        if (activeFilter !== '') url += `&active=${activeFilter}`;
        if (descFilter) url += `&description=${encodeURIComponent(descFilter)}`;

        try {
            const response = await fetch(url);
            const products = await response.json();
            this.renderProducts(products);
            this.updatePagination();
        } catch (error) {
            this.showAlert('Error loading products: ' + error.message, 'error');
        }
    }

    renderProducts(products) {
        const tbody = document.getElementById('productsTable');
        tbody.innerHTML = '';

        products.forEach(product => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${product.sku}</td>
                <td>${product.name}</td>
                <td>${product.description || '-'}</td>
                <td>
                    <span class="status-badge ${product.active ? 'status-completed' : 'status-failed'}">
                        ${product.active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>${new Date(product.created_at).toLocaleDateString()}</td>
                <td class="action-buttons">
                    <button class="btn btn-sm" onclick="app.editProduct(${product.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="app.deleteProduct(${product.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updatePagination() {
        // Simplified pagination - in real app, you'd get total count from API
        const pagination = document.getElementById('pagination');
        pagination.innerHTML = '';

        for (let i = 1; i <= 5; i++) {
            const button = document.createElement('button');
            button.className = `page-btn ${i === this.currentPage ? 'active' : ''}`;
            button.textContent = i;
            button.addEventListener('click', () => {
                this.currentPage = i;
                this.loadProducts();
            });
            pagination.appendChild(button);
        }
    }

    async bulkDeleteProducts() {
        if (!confirm('Are you sure you want to delete all products? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/products/', {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Bulk delete failed');
            }

            const result = await response.json();
            this.showAlert(`Successfully deleted ${result.deleted_count} products`, 'success');
            this.loadProducts(); // Refresh list
        } catch (error) {
            this.showAlert('Bulk delete failed: ' + error.message, 'error');
        }
    }

    async saveProduct() {
        const form = document.getElementById('productForm');
        const formData = new FormData(form);
        const productId = form.dataset.editingId;

        const productData = {
            sku: formData.get('sku'),
            name: formData.get('name'),
            description: formData.get('description'),
            active: formData.get('active') === 'on'
        };

        try {
            let response;
            if (productId) {
                response = await fetch(`/api/products/${productId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData)
                });
            } else {
                response = await fetch('/api/products/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData)
                });
            }

            if (!response.ok) {
                throw new Error('Save failed');
            }

            this.showAlert(`Product ${productId ? 'updated' : 'created'} successfully!`, 'success');
            form.reset();
            delete form.dataset.editingId;
            document.getElementById('formTitle').textContent = 'Create Product';
            this.loadProducts();
        } catch (error) {
            this.showAlert('Save failed: ' + error.message, 'error');
        }
    }

    async editProduct(productId) {
        try {
            const response = await fetch(`/api/products/${productId}`);
            const product = await response.json();

            document.getElementById('sku').value = product.sku;
            document.getElementById('name').value = product.name;
            document.getElementById('description').value = product.description || '';
            document.getElementById('active').checked = product.active;

            document.getElementById('productForm').dataset.editingId = productId;
            document.getElementById('formTitle').textContent = 'Edit Product';
            
            this.showTab('manage');
        } catch (error) {
            this.showAlert('Error loading product: ' + error.message, 'error');
        }
    }

    async deleteProduct(productId) {
    if (!confirm('Are you sure you want to delete this product?')) {
        return;
    }

    try {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Delete failed');
        }

        const result = await response.json();
        this.showAlert(result.message, 'success');
        this.loadProducts(); // Refresh the list
    } catch (error) {
        this.showAlert('Delete failed: ' + error.message, 'error');
    }
}

async bulkDeleteProducts() {
    if (!confirm('Are you sure you want to delete ALL products? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/products/', {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Bulk delete failed');
        }

        const result = await response.json();
        
        if (result.task_id) {
            // Large dataset - async processing
            this.showAlert('Bulk delete started! Processing in background...', 'success');
            this.monitorBulkDeleteProgress(result.task_id);
        } else {
            // Small dataset - immediate completion
            this.showAlert(`Successfully deleted ${result.deleted_count} products!`, 'success');
            this.loadProducts(); // Refresh immediately
        }
        
    } catch (error) {
        this.showAlert('Bulk delete failed: ' + error.message, 'error');
    }
}

async monitorBulkDeleteProgress(taskId) {
    const checkProgress = async () => {
        try {
            const response = await fetch(`/api/tasks/bulk-delete/${taskId}`);
            const data = await response.json();

            if (data.state === 'PROGRESS') {
                this.showUploadProgress(
                    (data.current / data.total) * 100, 
                    data.status
                );
                setTimeout(checkProgress, 1000);
            } else if (data.state === 'SUCCESS') {
                this.showUploadProgress(100, 'Completed successfully!');
                this.showAlert(`Bulk delete completed! Deleted ${data.deleted_count} products.`, 'success');
                setTimeout(() => {
                    this.hideUploadProgress();
                    this.loadProducts(); // Refresh product list
                }, 2000);
            } else if (data.state === 'FAILURE') {
                this.showAlert('Bulk delete failed: ' + data.status, 'error');
                this.hideUploadProgress();
            } else {
                setTimeout(checkProgress, 1000);
            }
        } catch (error) {
            this.showAlert('Error checking bulk delete progress: ' + error.message, 'error');
            this.hideUploadProgress();
        }
    };

    checkProgress();
}

    async loadWebhooks() {
        try {
            const response = await fetch('/api/webhooks/');
            const webhooks = await response.json();
            this.renderWebhooks(webhooks);
        } catch (error) {
            this.showAlert('Error loading webhooks: ' + error.message, 'error');
        }
    }

    renderWebhooks(webhooks) {
        const tbody = document.getElementById('webhooksTable');
        tbody.innerHTML = '';

        webhooks.forEach(webhook => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${webhook.url}</td>
                <td>${webhook.event_type}</td>
                <td>
                    <span class="status-badge ${webhook.enabled ? 'status-completed' : 'status-failed'}">
                        ${webhook.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </td>
                <td>${new Date(webhook.created_at).toLocaleDateString()}</td>
                <td class="action-buttons">
                    <button class="btn btn-sm btn-danger" onclick="app.deleteWebhook(${webhook.id})">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async saveWebhook() {
        const form = document.getElementById('webhookForm');
        const formData = new FormData(form);

        const webhookData = {
            url: formData.get('url'),
            event_type: formData.get('event_type'),
            enabled: formData.get('enabled') === 'on'
        };

        try {
            const response = await fetch('/api/webhooks/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(webhookData)
            });

            if (!response.ok) {
                throw new Error('Save failed');
            }

            this.showAlert('Webhook created successfully!', 'success');
            form.reset();
            this.loadWebhooks();
        } catch (error) {
            this.showAlert('Save failed: ' + error.message, 'error');
        }
    }

    async deleteWebhook(webhookId) {
        if (!confirm('Are you sure you want to delete this webhook?')) {
            return;
        }

        try {
            const response = await fetch(`/api/webhooks/${webhookId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Delete failed');
            }

            this.showAlert('Webhook deleted successfully!', 'success');
            this.loadWebhooks();
        } catch (error) {
            this.showAlert('Delete failed: ' + error.message, 'error');
        }
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.textContent = message;

        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);

        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// Initialize application
const app = new ProductImporter();