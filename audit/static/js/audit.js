/* ===== AUDIT SYSTEM JAVASCRIPT ===== */

// DOM Ready Function
document.addEventListener('DOMContentLoaded', function() {
    initializeAuditFunctions();
    setupAuditEventListeners();
    prefillDateInputs();
    setupAutoRefresh();
});
function initializeAuditFunctions() {
    // Color code badges
    colorCodeBadges();
    
    // Setup mobile menu
    setupMobileMenu();
    
    // Setup sidebar toggle
    setupSidebarToggle();
    
    // Setup responsive sidebar
    setupResponsiveSidebar();
    
    // Setup responsive table - ADD THIS
    setupResponsiveTable();
    
    // Setup filters
    setupFilters();
    
    // Setup export functionality
    setupExportFunctionality();
    
    // Setup performance monitoring
    setupAuditPerformance();
    
    // Check URL parameters
    checkUrlParameters();
}

// ===== BADGE COLORING =====
function colorCodeBadges() {
    const badges = document.querySelectorAll('.badge');
    const colorMap = {
        'create': 'badge-create',
        'update': 'badge-update', 
        'delete': 'badge-delete',
        'approve': 'badge-approve',
        'reject': 'badge-reject',
        'login': 'badge-login',
        'logout': 'badge-logout',
        'view': 'badge-view'
    };
    
    badges.forEach(badge => {
        // Remove existing badge classes
        badge.className = 'badge';
        
        // Get action from data attribute or class
        let action = badge.dataset.action;
        if (!action) {
            const actionClass = Array.from(badge.classList).find(cls => cls.startsWith('badge-'));
            if (actionClass) {
                action = actionClass.replace('badge-', '');
            }
        }
        
        // Apply color class
        if (action && colorMap[action.toLowerCase()]) {
            badge.classList.add(colorMap[action.toLowerCase()]);
            badge.dataset.action = action.toLowerCase();
        }
    });
}

// ===== SIDEBAR TOGGLE FUNCTIONS =====
function setupSidebarToggle() {
    const sidebar = document.getElementById('auditSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleBtn = document.getElementById('mobileFilterToggle');
    
    // If sidebar elements don't exist, return (not on audit page)
    if (!sidebar || !overlay || !toggleBtn) return;
    
    // Toggle sidebar function
    window.toggleSidebar = function(event) {
        if (event) {
            event.stopPropagation();
        }
        sidebar.classList.toggle('show');
        overlay.classList.toggle('show');
        
        // Prevent body scroll when sidebar is open on mobile
        if (sidebar.classList.contains('show') && window.innerWidth <= 991) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    };
    
    // Close sidebar when clicking overlay
    overlay.addEventListener('click', function() {
        window.toggleSidebar();
    });
    
    // Close sidebar on escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && sidebar.classList.contains('show')) {
            window.toggleSidebar();
        }
    });
    
    // Close sidebar when clicking outside (for mobile)
    document.addEventListener('click', function(event) {
        if (sidebar.classList.contains('show') && 
            window.innerWidth <= 991 &&
            !sidebar.contains(event.target) && 
            !toggleBtn.contains(event.target) &&
            !overlay.contains(event.target)) {
            window.toggleSidebar();
        }
    });
    
    // Handle sidebar close button
    const closeBtn = sidebar.querySelector('.sidebar-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function(event) {
            event.stopPropagation();
            window.toggleSidebar();
        });
    }
}

// ===== RESPONSIVE SIDEBAR HANDLING =====
function setupResponsiveSidebar() {
    const sidebar = document.getElementById('auditSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleBtn = document.getElementById('mobileFilterToggle');
    
    // If sidebar elements don't exist, return (not on audit page)
    if (!sidebar || !toggleBtn) return;
    
    // Check screen size and adjust sidebar
    function checkScreenSize() {
        if (window.innerWidth <= 991) {
            // Mobile - ensure sidebar is hidden by default
            sidebar.classList.remove('show');
            if (overlay) overlay.classList.remove('show');
            document.body.style.overflow = '';
            
            // Show mobile toggle button
            toggleBtn.style.display = 'flex';
        } else {
            // Desktop - ensure sidebar is visible
            sidebar.classList.add('show');
            if (overlay) overlay.classList.remove('show');
            document.body.style.overflow = '';
            
            // Hide mobile toggle button
            toggleBtn.style.display = 'none';
        }
    }
    
    // Check on load
    checkScreenSize();
    
    // Check on resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(checkScreenSize, 250);
    });
    
    // Check on orientation change
    window.addEventListener('orientationchange', function() {
        setTimeout(checkScreenSize, 100);
    });
}

// ===== MOBILE MENU =====
function setupMobileMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (!mobileMenuBtn || !mobileMenu) return;
    
    // Toggle mobile menu
    window.toggleMobileMenu = function(event) {
        if (event) {
            event.stopPropagation();
        }
        mobileMenu.classList.toggle('show');
    };
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (mobileMenu.classList.contains('show') && 
            !mobileMenu.contains(event.target) && 
            !mobileMenuBtn.contains(event.target)) {
            mobileMenu.classList.remove('show');
        }
    });
    
    // Close mobile menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && mobileMenu.classList.contains('show')) {
            mobileMenu.classList.remove('show');
        }
    });
    
    // Handle mobile menu item clicks
    mobileMenu.querySelectorAll('.mobile-menu-item').forEach(item => {
        item.addEventListener('click', () => {
            mobileMenu.classList.remove('show');
        });
    });
}

// ===== FILTER FUNCTIONS =====
function setupFilters() {
    // Set time period filter
    window.setTimePeriod = function(period) {
        const timePeriodInput = document.getElementById('timePeriodInput');
        const dateFromInput = document.getElementById('dateFromInput');
        const dateToInput = document.getElementById('dateToInput');
        
        if (timePeriodInput) {
            timePeriodInput.value = period;
        }
        
        // Clear custom dates when using quick periods
        if (dateFromInput) dateFromInput.value = '';
        if (dateToInput) dateToInput.value = '';
        
        // Update active button state
        document.querySelectorAll('.period-btn, .quick-filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = event?.target;
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
        
        // Submit form
        submitFilterForm();
    };
    
    // Apply custom date range
    window.applyCustomRange = function() {
        const customDateFrom = document.getElementById('customDateFrom');
        const customDateTo = document.getElementById('customDateTo');
        const dateFromInput = document.getElementById('dateFromInput');
        const dateToInput = document.getElementById('dateToInput');
        const timePeriodInput = document.getElementById('timePeriodInput');
        
        if (!customDateFrom || !customDateTo || !customDateFrom.value || !customDateTo.value) {
            alert('Please select both start and end dates');
            return;
        }
        
        // Validate date range
        const fromDate = new Date(customDateFrom.value);
        const toDate = new Date(customDateTo.value);
        
        if (fromDate > toDate) {
            alert('Start date cannot be after end date');
            return;
        }
        
        // Set values
        if (dateFromInput) dateFromInput.value = customDateFrom.value;
        if (dateToInput) dateToInput.value = customDateTo.value;
        if (timePeriodInput) timePeriodInput.value = '';
        
        // Remove active class from quick filter buttons
        document.querySelectorAll('.quick-filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        submitFilterForm();
    };
    
    // Clear all filters
    window.clearAllFilters = function() {
        window.location.href = window.location.pathname;
    };
    
    // Submit filter form
    function submitFilterForm() {
        const form = document.getElementById('filterForm');
        if (form) {
            form.submit();
        }
    }
    
    // Setup filter event listeners
    setupFilterEventListeners();
}

function setupFilterEventListeners() {
    // Enter key in search field submits form
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitFilterForm();
            }
        });
    }
    
    // Date input validation
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        // Set max date to today
        const today = new Date().toISOString().split('T')[0];
        input.max = today;
        
        // Validate on change
        input.addEventListener('change', function() {
            const value = this.value;
            if (value) {
                const selectedDate = new Date(value);
                const todayDate = new Date(today);
                
                if (selectedDate > todayDate) {
                    alert('Date cannot be in the future');
                    this.value = today;
                }
            }
        });
    });
}

// ===== EXPORT FUNCTIONALITY =====
function setupExportFunctionality() {
    // Download current filtered view
    window.downloadCurrentFilters = function() {
        if (typeof showLoading === 'function') {
            showLoading('Generating PDF with current filters...');
        }
        
        // Get current URL parameters
        const params = new URLSearchParams(window.location.search);
        params.set('export', 'pdf');
        
        // Add small delay to show loading
        setTimeout(() => {
            window.location.href = window.location.pathname + '?' + params.toString();
        }, 500);
    };
    
    // Download all logs (no filters)
    window.downloadAllLogs = function() {
        if (confirm('Download ALL audit logs? This may include thousands of records.')) {
            if (typeof showLoading === 'function') {
                showLoading('Generating PDF with all logs...');
            }
            
            setTimeout(() => {
                window.location.href = window.location.pathname + '?export=pdf';
            }, 500);
        }
    };
    
    // Export to PDF for detail page
    window.exportToPDF = function() {
        if (typeof showPDFLoading === 'function') {
            showPDFLoading();
        }
        window.location.href = '?download=pdf';
    };
    
    // Show PDF loading for detail page
    window.showPDFLoading = function() {
        const overlay = document.getElementById('loadingOverlay');
        const message = document.getElementById('loadingMessage');
        
        if (overlay) {
            if (message) {
                message.textContent = 'Generating PDF...';
            }
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            
            // Hide overlay after 10 seconds (safety)
            setTimeout(() => {
                if (typeof hideLoading === 'function') {
                    hideLoading();
                }
            }, 10000);
        }
    };
    
    // Print optimization
    setupPrintOptimization();
}

// ===== PRINT OPTIMIZATION =====
function setupPrintOptimization() {
    window.addEventListener('beforeprint', () => {
        // Hide non-essential elements
        document.querySelectorAll('.no-print, .mobile-menu, .export-panel, .mobile-filter-toggle, .audit-sidebar').forEach(el => {
            el.style.display = 'none';
        });
        
        // Show all table columns
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            table.style.width = '100%';
            table.style.minWidth = '0';
        });
    });
    
    window.addEventListener('afterprint', () => {
        // Restore hidden elements
        document.querySelectorAll('.no-print, .mobile-menu, .export-panel, .mobile-filter-toggle, .audit-sidebar').forEach(el => {
            el.style.display = '';
        });
        
        // Restore table widths
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            if (table.classList.contains('audit-table')) {
                table.style.minWidth = '800px';
            }
        });
        
        // Restore sidebar visibility based on screen size
        const sidebar = document.getElementById('auditSidebar');
        const toggleBtn = document.getElementById('mobileFilterToggle');
        if (sidebar && toggleBtn) {
            if (window.innerWidth <= 991) {
                sidebar.style.display = 'none';
                toggleBtn.style.display = 'flex';
            } else {
                sidebar.style.display = 'block';
                toggleBtn.style.display = 'none';
            }
        }
    });
}

// ===== AUDIT DETAIL PAGE FUNCTIONS =====
// IP Lookup function
window.lookupIP = function(ip) {
    const confirmLookup = confirm(`Look up IP address: ${ip}?\nThis will open an external site.`);
    if (confirmLookup) {
        window.open(`https://whatismyipaddress.com/ip/${ip}`, '_blank');
    }
};

// Copy log details to clipboard
window.copyLogDetails = function() {
    const logDetails = `
Audit Log #${document.querySelector('[data-log-id]')?.dataset.logId || 'N/A'}
Timestamp: ${document.querySelector('[data-timestamp]')?.dataset.timestamp || 'N/A'}
User: ${document.querySelector('[data-username]')?.dataset.username || 'System'}
Action: ${document.querySelector('[data-action]')?.dataset.action || 'N/A'}
Module: ${document.querySelector('[data-module]')?.dataset.module || 'N/A'}
Description: ${document.querySelector('[data-description]')?.dataset.description || 'N/A'}
IP: ${document.querySelector('[data-ip]')?.dataset.ip || 'N/A'}
    `.trim();
    
    if (typeof copyToClipboard === 'function') {
        copyToClipboard(logDetails);
    } else {
        navigator.clipboard.writeText(logDetails)
            .then(() => alert('Log details copied to clipboard!'))
            .catch(err => console.error('Copy failed:', err));
    }
};

// Calculate page load stats for detail page
function setupAuditPerformance() {
    const pageLoadTime = document.getElementById('pageLoadTime');
    const dataSize = document.getElementById('dataSize');
    
    if (pageLoadTime || dataSize) {
        // Calculate load time
        if (window.performance && pageLoadTime) {
            const timing = window.performance.timing;
            const loadTime = timing.domContentLoadedEventEnd - timing.navigationStart;
            pageLoadTime.textContent = `Loaded in ${loadTime}ms`;
        }
        
        // Calculate data size
        if (dataSize) {
            const htmlSize = new Blob([document.documentElement.outerHTML]).size;
            const sizeInKB = (htmlSize / 1024).toFixed(1);
            dataSize.textContent = `${sizeInKB} KB`;
        }
    }
}

// ===== URL PARAMETER HANDLING =====
function checkUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Handle export parameter
    if (urlParams.get('export') === 'pdf') {
        // Remove the export parameter from URL without reloading
        urlParams.delete('export');
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState({}, document.title, newUrl);
        
        // Hide loading overlay
        if (typeof hideLoading === 'function') {
            setTimeout(hideLoading, 1000);
        }
    }
    
    // Handle download parameter
    if (urlParams.get('download') === 'pdf') {
        // Remove the download parameter from URL without reloading
        urlParams.delete('download');
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState({}, document.title, newUrl);
        
        // Hide loading overlay
        if (typeof hideLoading === 'function') {
            setTimeout(hideLoading, 1000);
        }
    }
    
    // Highlight active time period button
    const timePeriod = urlParams.get('time_period');
    if (timePeriod) {
        document.querySelectorAll('.period-btn, .quick-filter-btn').forEach(btn => {
            if (btn.textContent.toLowerCase().includes(timePeriod) || 
                btn.dataset.period === timePeriod) {
                btn.classList.add('active');
            }
        });
    }
}

// ===== DATE HANDLING =====
function prefillDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    
    // Set max date for all date inputs
    document.querySelectorAll('input[type="date"]').forEach(input => {
        input.max = today;
    });
    
    // Pre-fill custom range inputs with current filter dates
    const dateFromInput = document.getElementById('dateFromInput');
    const dateToInput = document.getElementById('dateToInput');
    const customDateFrom = document.getElementById('customDateFrom');
    const customDateTo = document.getElementById('customDateTo');
    
    if (dateFromInput && dateFromInput.value && customDateFrom) {
        customDateFrom.value = dateFromInput.value;
    }
    
    if (dateToInput && dateToInput.value && customDateTo) {
        customDateTo.value = dateToInput.value;
    }
}

// ===== AUTO REFRESH =====
function setupAutoRefresh() {
    // Only auto-refresh if on audit logs page
    if (!window.location.pathname.includes('/audit/')) return;
    
    let autoRefreshEnabled = true;
    let refreshInterval = 300000; // 5 minutes
    
    // Check if user is active
    let userActivityTimeout;
    
    function resetUserActivity() {
        clearTimeout(userActivityTimeout);
        userActivityTimeout = setTimeout(() => {
            autoRefreshEnabled = false;
            console.log('Auto-refresh paused due to inactivity');
        }, 600000); // 10 minutes of inactivity
    }
    
    // Reset activity timer on user interaction
    ['click', 'mousemove', 'keypress', 'scroll'].forEach(event => {
        document.addEventListener(event, resetUserActivity);
    });
    
    // Start auto-refresh
    function startAutoRefresh() {
        if (autoRefreshEnabled && !document.hidden) {
            setTimeout(() => {
                if (autoRefreshEnabled && !document.hidden) {
                    window.location.reload();
                }
            }, refreshInterval);
        }
    }
    
    // Initial setup
    resetUserActivity();
    startAutoRefresh();
    
    // Listen for page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            autoRefreshEnabled = true;
            resetUserActivity();
            startAutoRefresh();
        } else {
            autoRefreshEnabled = false;
        }
    });
}

// ===== EVENT LISTENERS SETUP =====
function setupAuditEventListeners() {
    // Session timeout warning
    let inactivityTime = 0;
    const warningTime = 300000; // 5 minutes
    
    function resetInactivityTimer() {
        inactivityTime = 0;
    }
    
    setInterval(() => {
        inactivityTime += 1000;
        if (inactivityTime > warningTime) {
            if (confirm('You have been inactive for 5 minutes. Stay logged in?')) {
                resetInactivityTimer();
            }
        }
    }, 1000);
    
    // Reset timer on user activity
    ['click', 'touchstart', 'keypress'].forEach(event => {
        document.addEventListener(event, resetInactivityTimer);
    });
    
    // Handle page visibility for loading overlay and sidebar
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            if (typeof hideLoading === 'function') {
                hideLoading();
            }
            
            // Close sidebar when page becomes visible again (mobile only)
            const sidebar = document.getElementById('auditSidebar');
            if (sidebar && sidebar.classList.contains('show') && window.innerWidth <= 991) {
                if (typeof toggleSidebar === 'function') {
                    toggleSidebar();
                }
            }
        }
    });
    
    // Add data attributes for easier JavaScript access
    addDataAttributes();
}

// ===== DATA ATTRIBUTES =====
function addDataAttributes() {
    // Add data attributes to log rows for JavaScript access
    const logRows = document.querySelectorAll('.audit-table tbody tr');
    logRows.forEach((row, index) => {
        const logId = row.querySelector('a[href*="/detail/"]')?.href?.match(/\d+/)?.[0];
        if (logId) {
            row.dataset.logId = logId;
            row.dataset.rowIndex = index;
        }
    });
    
    // Add data attributes to detail page elements
    const logIdElement = document.querySelector('[data-log-id]');
    if (logIdElement && !logIdElement.dataset.logId) {
        const logId = window.location.pathname.match(/\d+/)?.[0];
        if (logId) {
            logIdElement.dataset.logId = logId;
        }
    }
}

// ===== KEYBOARD SHORTCUTS (Audit-specific) =====
document.addEventListener('keydown', function(e) {
    // Ctrl + D for download current (audit logs page)
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        if (typeof downloadCurrentFilters === 'function') {
            downloadCurrentFilters();
        }
    }
    
    // Ctrl + A for download all (audit logs page)
    if (e.ctrlKey && e.key === 'a') {
        e.preventDefault();
        if (typeof downloadAllLogs === 'function') {
            downloadAllLogs();
        }
    }
    
    // Ctrl + F to focus search field
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Ctrl + / to toggle sidebar
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        if (typeof toggleSidebar === 'function') {
            toggleSidebar();
        }
    }
    
    // Escape to close sidebar
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('auditSidebar');
        if (sidebar && sidebar.classList.contains('show')) {
            e.preventDefault();
            if (typeof toggleSidebar === 'function') {
                toggleSidebar();
            }
        }
    }
    
    // Arrow keys for table navigation (if on audit logs page)
    if (document.querySelector('.audit-table')) {
        const rows = document.querySelectorAll('.audit-table tbody tr');
        let currentIndex = -1;
        
        // Find currently focused row
        rows.forEach((row, index) => {
            if (row.classList.contains('focused')) {
                currentIndex = index;
            }
        });
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (currentIndex < rows.length - 1) {
                rows[currentIndex]?.classList.remove('focused');
                rows[currentIndex + 1].classList.add('focused');
                rows[currentIndex + 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (currentIndex > 0) {
                rows[currentIndex]?.classList.remove('focused');
                rows[currentIndex - 1].classList.add('focused');
                rows[currentIndex - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        if (e.key === 'Enter' && currentIndex >= 0) {
            const link = rows[currentIndex].querySelector('a');
            if (link) link.click();
        }
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        colorCodeBadges,
        setTimePeriod,
        downloadCurrentFilters,
        downloadAllLogs,
        lookupIP,
        copyLogDetails
    };
}

// ===== RESPONSIVE TABLE HANDLING =====
function setupResponsiveTable() {
    const tableWrapper = document.querySelector('.table-wrapper');
    const auditTable = document.querySelector('.audit-table');
    
    if (!tableWrapper || !auditTable) return;
    
    function checkTableFit() {
        const containerWidth = tableWrapper.clientWidth;
        const tableWidth = auditTable.scrollWidth;
        
        if (tableWidth > containerWidth) {
            tableWrapper.style.overflowX = 'auto';
        } else {
            tableWrapper.style.overflowX = 'visible';
        }
    }
    
    // Check on load
    checkTableFit();
    
    // Check on resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(checkTableFit, 100);
    });
    
    // Check on sidebar toggle
    const sidebar = document.getElementById('auditSidebar');
    if (sidebar) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    setTimeout(checkTableFit, 300); // Wait for animation
                }
            });
        });
        
        observer.observe(sidebar, { attributes: true });
    }
}