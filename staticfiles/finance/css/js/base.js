// ===== INTEGRATED BASE JAVASCRIPT =====
// cornelsimba/finance/static/finance/js/base.js

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing finance system...');
    
    // Initialize all modules
    initSidebar();
    initNotifications();
    initUserDropdown();
    initGlobalSearch();
    initCurrencyFormatting();
    initFormValidation();
    initPrintFunctionality();
    initTableFeatures();
    initKeyboardShortcuts();
    
    // Add any dashboard-specific features
    if (isDashboardPage()) {
        addDashboardFeatures();
    }
});

// ===== SIDEBAR FUNCTIONS =====
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.getElementById('sidebarToggleMobile');
    const overlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !toggleBtn || !overlay) {
        console.warn('Sidebar elements missing');
        return;
    }

    // OPEN sidebar
    toggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();

        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    });

    // CLOSE when clicking overlay
    overlay.addEventListener('click', function () {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    });

    // CLOSE when clicking a menu item (mobile)
    sidebar.querySelectorAll('.menu-item a').forEach(link => {
        link.addEventListener('click', function () {
            if (window.innerWidth < 992) {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // SAFETY: reset on resize
    window.addEventListener('resize', function () {
        if (window.innerWidth >= 992) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
    // ===== SIDEBAR FUNCTIONS =====
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.getElementById('sidebarToggleMobile');
    const overlay = document.getElementById('sidebarOverlay');

    if (!sidebar || !toggleBtn || !overlay) {
        console.warn('Sidebar elements missing');
        return;
    }

    // OPEN sidebar on mobile toggle click
    toggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();

        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    });

    // CLOSE when clicking overlay
    overlay.addEventListener('click', function () {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    });

    // CLOSE when clicking the X button in sidebar header (mobile)
    const closeSidebar = function() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    };
    
    // Add close button event if using CSS pseudo-element
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && 
            sidebar.classList.contains('active') &&
            e.target.closest('.sidebar-header')) {
            const headerRect = document.querySelector('.sidebar-header').getBoundingClientRect();
            // Check if click is in the close button area (top-right corner)
            if (e.clientX > headerRect.right - 50 && e.clientY < headerRect.top + 50) {
                closeSidebar();
            }
        }
    });

    // CLOSE when clicking a menu item (mobile)
    sidebar.querySelectorAll('.menu-item a').forEach(link => {
        link.addEventListener('click', function () {
            if (window.innerWidth < 992) {
                closeSidebar();
            }
        });
    });

    // SAFETY: reset on resize
    window.addEventListener('resize', function () {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    });
    
    // ESC key to close sidebar
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('active')) {
            closeSidebar();
        }
    });
}
}


// ===== NOTIFICATION SYSTEM =====
function initNotifications() {
    const notifications = document.querySelectorAll('.notification');
    const notificationCloseBtns = document.querySelectorAll('.notification-close');
    
    // Auto-hide notifications after 5 seconds
    notifications.forEach(notification => {
        setTimeout(() => {
            fadeOutNotification(notification);
        }, 5000);
    });
    
    // Close notification on button click
    notificationCloseBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const notification = this.closest('.notification');
            fadeOutNotification(notification);
        });
    });
    
    // Close notification when clicking anywhere on it
    notifications.forEach(notification => {
        notification.addEventListener('click', function(e) {
            if (!e.target.closest('.notification-close')) {
                fadeOutNotification(this);
            }
        });
    });
    
    // Auto-hide function
    const autoHideNotifications = function() {
        document.querySelectorAll('.notification').forEach(notification => {
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 500);
            }, 5000);
        });
    };
    
    // Run auto-hide on page load
    autoHideNotifications();
}

function fadeOutNotification(notification) {
    if (!notification) return;
    
    notification.style.opacity = '0';
    notification.style.transform = 'translateX(100%)';
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 500);
}

// Global function to show notifications
window.showNotification = function(message, type = 'info') {
    const notificationContainer = document.querySelector('.notification-container');
    
    if (!notificationContainer) {
        // Create notification container if not exists
        const container = document.createElement('div');
        container.className = 'notification-container';
        document.body.insertBefore(container, document.body.firstChild);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Icons based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    else if (type === 'error' || type === 'danger') icon = 'exclamation-circle';
    else if (type === 'warning') icon = 'exclamation-triangle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    notificationContainer.appendChild(notification);
    
    // Initialize close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => fadeOutNotification(notification));
    
    // Auto-remove
    setTimeout(() => fadeOutNotification(notification), 5000);
    
    return notification;
};

// ===== USER DROPDOWN =====
function initUserDropdown() {
    const userBtn = document.getElementById('userBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userBtn && userDropdown) {
        userBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!userBtn.contains(e.target) && !userDropdown.contains(e.target)) {
                userDropdown.classList.remove('show');
            }
        });
        
        // Prevent dropdown from closing when clicking inside it
        userDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

// ===== GLOBAL SEARCH =====
function initGlobalSearch() {
    const globalSearch = document.getElementById('globalSearch');
    
    if (globalSearch) {
        globalSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && this.value.trim()) {
                const searchTerm = this.value.trim();
                const currentPath = window.location.pathname;
                
                // Context-aware search redirection
                let redirectUrl = '';
                if (currentPath.includes('/income/') || currentPath.includes('/finance/income')) {
                    redirectUrl = '/finance/income/?search=' + encodeURIComponent(searchTerm);
                } else if (currentPath.includes('/expenses/') || currentPath.includes('/finance/expenses')) {
                    redirectUrl = '/finance/expenses/?search=' + encodeURIComponent(searchTerm);
                } else if (currentPath.includes('/payroll/') || currentPath.includes('/finance/payroll')) {
                    redirectUrl = '/finance/payroll/?search=' + encodeURIComponent(searchTerm);
                } else {
                    // Default to finance dashboard with search
                    redirectUrl = '/finance/?search=' + encodeURIComponent(searchTerm);
                }
                
                window.location.href = redirectUrl;
            }
        });
        
        // Add clear button functionality
        const searchContainer = globalSearch.parentElement;
        const clearBtn = document.createElement('button');
        clearBtn.className = 'search-clear';
        clearBtn.innerHTML = '<i class="fas fa-times"></i>';
        clearBtn.style.display = 'none';
        searchContainer.appendChild(clearBtn);
        
        globalSearch.addEventListener('input', function() {
            clearBtn.style.display = this.value ? 'block' : 'none';
        });
        
        clearBtn.addEventListener('click', function() {
            globalSearch.value = '';
            this.style.display = 'none';
            globalSearch.focus();
        });
    }
}

// ===== CURRENCY FORMATTING =====
function initCurrencyFormatting() {
    // Format all currency elements on page load
    formatAllCurrencyElements();
    
    // Format currency inputs
    document.querySelectorAll('.currency-input').forEach(input => {
        formatCurrencyInput(input);
    });
}

function formatAllCurrencyElements() {
    document.querySelectorAll('.tsh-amount').forEach(element => {
        const text = element.textContent;
        const amount = text.replace(/[^\d.-]/g, '');
        
        if (amount && !isNaN(parseFloat(amount))) {
            const num = parseFloat(amount);
            const isNegative = num < 0;
            const absNum = Math.abs(num);
            const formatted = absNum.toLocaleString('en-US', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            });
            
            element.textContent = `${isNegative ? '-Tsh ' : 'Tsh '}${formatted}`;
            
            // Add data attribute with raw value
            element.setAttribute('data-raw-value', num);
        }
    });
}

function formatCurrencyInput(input) {
    input.addEventListener('input', function() {
        let value = this.value.replace(/[^\d.]/g, '');
        
        if (value) {
            // Store raw value in data attribute
            this.setAttribute('data-raw-value', value);
            
            // Format for display
            const formatted = parseFloat(value).toLocaleString();
            this.value = formatted;
            
            // Move cursor to end
            setTimeout(() => {
                this.selectionStart = this.selectionEnd = 10000;
            }, 0);
        }
    });
    
    // Clean value before submit
    if (input.form) {
        input.form.addEventListener('submit', function() {
            const rawValue = input.getAttribute('data-raw-value');
            if (rawValue) {
                input.value = rawValue;
            }
        });
    }
    
    // Focus formatting
    input.addEventListener('focus', function() {
        const rawValue = this.getAttribute('data-raw-value');
        if (rawValue) {
            this.value = rawValue;
        }
    });
    
    // Blur formatting
    input.addEventListener('blur', function() {
        let value = this.value.replace(/[^\d.]/g, '');
        if (value) {
            this.setAttribute('data-raw-value', value);
            this.value = parseFloat(value).toLocaleString();
        }
    });
}

// Global currency formatter
window.formatCurrency = function(amount, includeSymbol = true) {
    const num = parseFloat(amount) || 0;
    const formatted = Math.abs(num).toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
    
    if (includeSymbol) {
        return `${num < 0 ? '-Tsh ' : 'Tsh '}${formatted}`;
    }
    return formatted;
};

// ===== FORM VALIDATION =====
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        let formChanged = false;
        
        // Mark form as changed
        form.addEventListener('change', function() {
            formChanged = true;
        });
        
        form.addEventListener('input', function() {
            formChanged = true;
        });
        
        // Clear changed flag on submit
        form.addEventListener('submit', function() {
            formChanged = false;
        });
        
        // Warn before leaving with unsaved changes
        window.addEventListener('beforeunload', function(e) {
            if (formChanged) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
                return 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
        
        // Validate on submit
        form.addEventListener('submit', function(e) {
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            let firstErrorField = null;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error-input');
                    
                    // Create error message if not exists
                    if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('error-message')) {
                        const errorMsg = document.createElement('div');
                        errorMsg.className = 'error-message';
                        errorMsg.textContent = field.getAttribute('data-error') || 'This field is required';
                        errorMsg.style.color = 'var(--danger-color)';
                        errorMsg.style.fontSize = '0.85rem';
                        errorMsg.style.marginTop = '5px';
                        field.parentNode.insertBefore(errorMsg, field.nextSibling);
                    }
                    
                    if (!firstErrorField) {
                        firstErrorField = field;
                    }
                } else {
                    field.classList.remove('error-input');
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg && errorMsg.classList.contains('error-message')) {
                        errorMsg.remove();
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showNotification('Please fill all required fields', 'error');
                
                // Scroll to first error
                if (firstErrorField) {
                    firstErrorField.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                    firstErrorField.focus();
                }
            }
        });
    });
}

// ===== PRINT FUNCTIONALITY =====
function initPrintFunctionality() {
    window.printDashboard = function() {
        // Hide elements that shouldn't be printed
        const elementsToHide = [
            '.header-actions',
            '.filter-form',
            '.action-buttons',
            '.notification-container',
            '.sidebar',
            '.navbar',
            '.breadcrumb'
        ];
        
        const originalDisplay = {};
        
        elementsToHide.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                originalDisplay[selector] = el.style.display;
                el.style.display = 'none';
            });
        });
        
        // Print
        window.print();
        
        // Restore elements
        elementsToHide.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.style.display = originalDisplay[selector];
            });
        });
    };
}

// ===== TABLE FEATURES =====
function initTableFeatures() {
    // Table row selection and click handling
    document.querySelectorAll('table tbody tr').forEach(row => {
        // Make rows clickable if they have a view link
        const viewLink = row.querySelector('a[href*="detail"], a[href*="view"], a.btn-view');
        if (viewLink) {
            row.style.cursor = 'pointer';
            
            row.addEventListener('click', function(e) {
                // Don't trigger if clicking on links, buttons, or form elements
                if (!e.target.closest('a') && 
                    !e.target.closest('button') && 
                    !e.target.closest('input') &&
                    !e.target.closest('select') &&
                    !e.target.closest('.action-buttons')) {
                    window.location.href = viewLink.href;
                }
            });
        }
        
        // Row selection
        row.addEventListener('dblclick', function(e) {
            if (!e.target.closest('a') && !e.target.closest('button')) {
                this.classList.toggle('selected');
            }
        });
    });
    
    // Sortable tables
    document.querySelectorAll('table thead th[data-sortable="true"]').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            const table = this.closest('table');
            const columnIndex = Array.from(this.parentElement.children).indexOf(this);
            sortTable(table, columnIndex);
        });
    });
}

function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = table.getAttribute('data-sort-direction') !== 'asc';
    
    rows.sort((a, b) => {
        const aText = a.children[columnIndex].textContent.trim();
        const bText = b.children[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // Otherwise sort as text
        return isAscending ? 
            aText.localeCompare(bText) : 
            bText.localeCompare(aText);
    });
    
    // Clear and re-append rows
    rows.forEach(row => tbody.appendChild(row));
    
    // Update sort direction
    table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
}

// ===== KEYBOARD SHORTCUTS =====
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to save forms
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const form = document.querySelector('form');
            if (form) {
                if (form.checkValidity()) {
                    form.submit();
                    showNotification('Form saved successfully', 'success');
                } else {
                    form.reportValidity();
                }
            }
        }
        
        // Ctrl/Cmd + F to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('globalSearch') || 
                               document.querySelector('input[name="search"]') ||
                               document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Escape to close modals/dropdowns
        if (e.key === 'Escape') {
            // Close dropdowns
            document.querySelectorAll('.show').forEach(el => {
                el.classList.remove('show');
            });
            
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                document.querySelector('.sidebar')?.classList.remove('active');
                document.querySelector('.sidebar-overlay')?.classList.remove('active');
            }
            
            // Close notifications
            document.querySelectorAll('.notification').forEach(notification => {
                fadeOutNotification(notification);
            });
        }
        
        // Ctrl/Cmd + P to print
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            window.printDashboard();
        }
    });
}

// ===== DASHBOARD-SPECIFIC FEATURES =====
function isDashboardPage() {
    return window.location.pathname === '/finance/' || 
           window.location.pathname === '/finance' ||
           window.location.pathname.includes('/finance/dashboard');
}

function addDashboardFeatures() {
    // Add print button
    const contentHeader = document.querySelector('.content-header');
    if (contentHeader) {
        const printBtn = document.createElement('button');
        printBtn.className = 'btn btn-warning ml-2';
        printBtn.innerHTML = '<i class="fas fa-print"></i> Print Report';
        printBtn.onclick = window.printDashboard;
        contentHeader.appendChild(printBtn);
    }
    
    // Add refresh button
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn btn-info ml-2';
    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
    refreshBtn.onclick = function() {
        window.location.reload();
    };
    contentHeader.appendChild(refreshBtn);
    
    // Initialize dashboard charts if any
    initDashboardCharts();
}

function initDashboardCharts() {
    // Placeholder for chart initialization
    // You can integrate Chart.js or other charting libraries here
    console.log('Dashboard charts initialized');
}

// ===== HELPER FUNCTIONS =====
window.confirmAction = function(message, callback) {
    if (confirm(message)) {
        if (typeof callback === 'function') {
            callback();
        }
        return true;
    }
    return false;
};

window.loading = function(show = true, message = 'Loading...') {
    const loadingEl = document.getElementById('loadingOverlay');
    
    if (show) {
        if (!loadingEl) {
            const overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            
            const spinner = document.createElement('div');
            spinner.style.cssText = `
                background: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            `;
            
            spinner.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">${message}</p>
            `;
            
            overlay.appendChild(spinner);
            document.body.appendChild(overlay);
        }
    } else {
        if (loadingEl) {
            loadingEl.remove();
        }
    }
};

// Initialize on window load for good measure
window.addEventListener('load', function() {
    // Ensure currency formatting is applied after all content loads
    setTimeout(formatAllCurrencyElements, 100);
});

// Add this to your base.js after all other code
document.addEventListener('DOMContentLoaded', function() {
    // Force light theme
    document.documentElement.setAttribute('data-theme', 'light');
    document.body.classList.add('finance-body');
    
    // Remove any dark theme classes
    document.body.classList.remove('dark', 'dark-mode', 'theme-dark');
    
    // Fix sidebar positioning on desktop
    function fixSidebarPosition() {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (window.innerWidth >= 992) {
            // Desktop: show sidebar, add margin to main content
            if (sidebar) {
                sidebar.classList.add('active');
                sidebar.style.transform = 'translateX(0)';
            }
            if (mainContent) {
                mainContent.style.marginLeft = '280px';
            }
        } else {
            // Mobile: hide sidebar, no margin
            if (sidebar) {
                sidebar.classList.remove('active');
                sidebar.style.transform = 'translateX(-100%)';
            }
            if (mainContent) {
                mainContent.style.marginLeft = '0';
            }
        }
    }
    
    // Run on load and resize
    fixSidebarPosition();
    window.addEventListener('resize', fixSidebarPosition);
    
    // Ensure all text is visible (fix dark text on dark background)
    document.querySelectorAll('.stat-card, .card, .alert, .notification, .table').forEach(element => {
        element.style.color = '#2d3748';
        element.style.backgroundColor = 'white';
    });
    
    // Fix button colors
    document.querySelectorAll('.btn').forEach(btn => {
        if (btn.classList.contains('btn-outline')) {
            btn.style.color = '#4a5568';
            btn.style.backgroundColor = 'transparent';
        } else {
            btn.style.color = 'white';
        }
    });
});