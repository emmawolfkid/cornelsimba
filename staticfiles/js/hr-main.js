// ============================================
// HR SYSTEM MAIN JAVASCRIPT
// Modern, Attractive, Non-Boring HR Interface
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initSidebar();
    initNotifications();
    initMobileMenu();
    initPagination();
    initFormValidation();
});

// ===== SIDEBAR FUNCTIONALITY =====
function initSidebar() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    // Set active nav item based on current URL
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && currentPath.includes(href.split('/')[1] || href)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Add hover effects
    navItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateX(5px)';
            }
        });
        
        item.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateX(0)';
            }
        });
    });
}

// ===== NOTIFICATION SYSTEM =====
function initNotifications() {
    // Convert Django messages to notifications
    const djangoMessages = document.querySelectorAll('.alert');
    djangoMessages.forEach(message => {
        const type = message.classList.contains('alert-success') ? 'success' :
                    message.classList.contains('alert-warning') ? 'warning' :
                    message.classList.contains('alert-danger') ? 'error' : 'info';
        
        const text = message.textContent.replace('×', '').trim();
        showNotification(text, type);
        message.remove();
    });
    
    // Close buttons for alerts
    document.querySelectorAll('.close-alert').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').style.display = 'none';
        });
    });
}

function showNotification(message, type = 'info', title = null) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification-toast ${type}`;
    
    const icons = {
        success: 'fas fa-check-circle',
        warning: 'fas fa-exclamation-triangle',
        error: 'fas fa-times-circle',
        info: 'fas fa-info-circle'
    };
    
    const titles = {
        success: 'Success',
        warning: 'Warning',
        error: 'Error',
        info: 'Information'
    };
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="${icons[type]}"></i>
        </div>
        <div class="notification-content">
            <div class="notification-title">${title || titles[type]}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
        <div class="notification-progress">
            <div class="notification-progress-bar"></div>
        </div>
    `;
    
    container.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Setup close button
    notification.querySelector('.notification-close').addEventListener('click', function() {
        hideNotification(notification);
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        hideNotification(notification);
    }, 5000);
}

function hideNotification(notification) {
    notification.classList.add('hide');
    setTimeout(() => {
        notification.remove();
    }, 300);
}

// ===== MOBILE MENU =====
function initMobileMenu() {
    const mobileToggle = document.createElement('button');
    mobileToggle.className = 'mobile-menu-toggle';
    mobileToggle.innerHTML = '<i class="fas fa-bars"></i>';
    mobileToggle.style.display = 'none';
    
    document.body.appendChild(mobileToggle);
    
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    
    document.body.appendChild(overlay);
    
    // Toggle sidebar
    mobileToggle.addEventListener('click', function() {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
    });
    
    // Close sidebar when clicking overlay
    overlay.addEventListener('click', function() {
        sidebar.classList.remove('mobile-open');
        this.classList.remove('active');
    });
    
    // Show/hide mobile toggle based on screen size
    function checkMobile() {
        if (window.innerWidth <= 767) {
            mobileToggle.style.display = 'flex';
        } else {
            mobileToggle.style.display = 'none';
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        }
    }
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
}

// ===== PAGINATION =====
function initPagination() {
    // Add active class to current page
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    paginationLinks.forEach(link => {
        if (link.textContent.trim() === document.querySelector('.pagination .active')?.textContent?.trim()) {
            link.classList.add('active');
        }
    });
}

// ===== FORM VALIDATION =====
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    
                    // Add error message
                    if (!field.nextElementSibling?.classList.contains('error-message')) {
                        const errorMsg = document.createElement('div');
                        errorMsg.className = 'error-message text-danger mt-1';
                        errorMsg.textContent = 'This field is required';
                        field.parentNode.appendChild(errorMsg);
                    }
                } else {
                    field.classList.remove('error');
                    const errorMsg = field.parentNode.querySelector('.error-message');
                    if (errorMsg) errorMsg.remove();
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showNotification('Please fill in all required fields', 'error');
            }
        });
    });
    
    // Remove error class on input
    document.addEventListener('input', function(e) {
        if (e.target.hasAttribute('required')) {
            e.target.classList.remove('error');
            const errorMsg = e.target.parentNode.querySelector('.error-message');
            if (errorMsg) errorMsg.remove();
        }
    });
}

// ===== HELPER FUNCTIONS =====
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function confirmAction(message) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'confirmation-modal';
        modal.innerHTML = `
            <div class="confirmation-content">
                <h3 style="margin-bottom: 20px; color: var(--dark);">
                    <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                    Confirm Action
                </h3>
                <p style="margin-bottom: 25px; color: var(--gray-dark);">${message}</p>
                <div class="form-actions">
                    <button class="btn btn-danger" id="confirm-yes">
                        <i class="fas fa-check me-2"></i> Yes, Continue
                    </button>
                    <button class="btn btn-outline" id="confirm-no">
                        <i class="fas fa-times me-2"></i> Cancel
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('#confirm-yes').addEventListener('click', function() {
            modal.remove();
            resolve(true);
        });
        
        modal.querySelector('#confirm-no').addEventListener('click', function() {
            modal.remove();
            resolve(false);
        });
        
        // Close on overlay click
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.remove();
                resolve(false);
            }
        });
    });
}

// ===== EXPORT FUNCTIONS =====
window.HRSystem = {
    showNotification,
    confirmAction,
    formatDate,
    formatCurrency
};