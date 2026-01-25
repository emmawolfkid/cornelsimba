// View change functionality
function changeView(viewType) {
    const moduleGrid = document.getElementById('moduleGrid');
    const viewBtns = document.querySelectorAll('.view-btn');
    
    // Update active button
    viewBtns.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Change grid layout
    if (viewType === 'list') {
        moduleGrid.style.gridTemplateColumns = '1fr';
        moduleGrid.querySelectorAll('.module-card').forEach(card => {
            card.style.display = 'flex';
            card.style.alignItems = 'center';
            card.style.gap = '20px';
            card.style.padding = '20px';
        });
    } else if (viewType === 'compact') {
        moduleGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
        moduleGrid.querySelectorAll('.module-card').forEach(card => {
            card.style.padding = '15px';
            card.querySelector('.module-description').style.display = 'none';
        });
    } else {
        moduleGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(250px, 1fr))';
        moduleGrid.querySelectorAll('.module-card').forEach(card => {
            card.style.display = 'block';
            card.style.padding = '30px';
            const desc = card.querySelector('.module-description');
            if (desc) desc.style.display = 'block';
        });
    }
}

// Items per page
function changeItemsPerPage(count) {
    const moduleGrid = document.getElementById('moduleGrid');
    const modules = moduleGrid.querySelectorAll('.module-card');
    const pagination = document.getElementById('pagination');
    
    // Show/hide modules
    modules.forEach((module, index) => {
        module.classList.toggle('hidden-module', index >= count);
    });
    
    // Update pagination if needed
    updatePagination(Math.ceil(modules.length / count));
}

// Pagination update
function updatePagination(totalPages) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = 'page-btn';
        pageBtn.textContent = i;
        pageBtn.onclick = () => goToPage(i);
        pagination.appendChild(pageBtn);
    }
}

function goToPage(page) {
    const pageBtns = document.querySelectorAll('.page-btn');
    pageBtns.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Calculate which modules to show
    const itemsPerPage = document.querySelector('.items-per-page select').value;
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + parseInt(itemsPerPage);
    
    const modules = document.querySelectorAll('.module-card');
    modules.forEach((module, index) => {
        module.classList.toggle('hidden-module', index < startIndex || index >= endIndex);
    });
}

// Notification system
function showNotification(message, type = 'info') {
    const notificationCenter = document.getElementById('notificationCenter');
    if (!notificationCenter) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    else if (type === 'warning') icon = 'exclamation-triangle';
    else if (type === 'error') icon = 'times-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    notificationCenter.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Mobile Navigation Toggle
    const mobileNavToggle = document.getElementById('mobileNavToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (mobileNavToggle && sidebar) {
        mobileNavToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            this.innerHTML = sidebar.classList.contains('active') 
                ? '<i class="fas fa-times"></i> Close Modules' 
                : '<i class="fas fa-bars"></i> Browse Modules';
        });
    }
    
    // Populate sidebar modules
    const sidebarModules = document.getElementById('sidebarModules');
    if (sidebarModules) {
        const modules = [
            {name: 'HR', icon: 'fa-users', color: '#e74c3c', url: '/hr/'},
            {name: 'Finance', icon: 'fa-money-bill-wave', color: '#27ae60', url: '/finance/'},
            {name: 'Inventory', icon: 'fa-boxes', color: '#f39c12', url: '/inventory/'},
            {name: 'Procurement', icon: 'fa-shopping-cart', color: '#9b59b6', url: '/procurement/'},
            {name: 'Sales', icon: 'fa-chart-line', color: '#2ecc71', url: '/sales/'},
            {name: 'Audit', icon: 'fa-shield-alt', color: '#34495e', url: '/audit/'}
        ];
        
        modules.forEach(module => {
            const moduleEl = document.createElement('div');
            moduleEl.className = 'sidebar-module';
            moduleEl.innerHTML = `
                <i class="fas ${module.icon}" style="color: ${module.color}; margin-bottom: 5px;"></i><br>
                ${module.name}
            `;
            moduleEl.onclick = () => {
                window.location.href = module.url;
            };
            sidebarModules.appendChild(moduleEl);
        });
    }
    
    // Show welcome notification
    setTimeout(() => {
        showNotification('Welcome to Cornel Simba Dashboard!', 'info');
    }, 1000);
    
    // Initialize pagination
    updatePagination(1);
});