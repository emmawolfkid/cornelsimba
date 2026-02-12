// Sales Module JavaScript
// Pure JavaScript - No Django template tags

(function() {
    'use strict';
    
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeSalesModule();
    });
    
    function initializeSalesModule() {
        setupSidebar();
        setupTouchFeedback();
        setupAutoDismissAlerts();
        setupResponsiveTables();
        setupTooltips();
        setupCurrentPageHighlight();
    }
    
    function setupSidebar() {
        const sidebar = document.querySelector('.sales-sidebar');
        const mainContent = document.getElementById('mainContent');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        const sidebarToggle = document.getElementById('sidebarToggle');
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        const mobileMenuToggleInner = document.getElementById('mobileMenuToggleInner');
        
        if (!sidebar) return;
        
        // Desktop sidebar toggle
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', function() {
                if (window.innerWidth >= 769) {
                    mainContent.classList.toggle('full-width');
                }
            });
        }
        
        // Mobile sidebar functions
        function openSidebar() {
            if (sidebar) sidebar.classList.add('active');
            if (sidebarOverlay) sidebarOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
        
        function closeSidebar() {
            if (sidebar) sidebar.classList.remove('active');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }
        
        // Mobile menu toggle buttons
        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener('click', openSidebar);
        }
        
        if (mobileMenuToggleInner) {
            mobileMenuToggleInner.addEventListener('click', openSidebar);
        }
        
        // Close sidebar when clicking overlay
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeSidebar);
        }
        
        // Close sidebar when clicking ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeSidebar();
            }
        });
        
        // Auto-close sidebar on mobile when clicking a link
        if (window.innerWidth < 769) {
            const sidebarLinks = sidebar.querySelectorAll('.nav-link');
            sidebarLinks.forEach(link => {
                link.addEventListener('click', closeSidebar);
            });
        }
        
        // Handle window resize
        function handleResize() {
            if (window.innerWidth >= 769) {
                closeSidebar();
            }
        }
        
        window.addEventListener('resize', handleResize);
    }
    
    function setupTouchFeedback() {
        const touchButtons = document.querySelectorAll('.btn, .nav-link, .btn-touch');
        touchButtons.forEach(btn => {
            btn.addEventListener('touchstart', function() {
                this.classList.add('active');
            });
            
            btn.addEventListener('touchend', function() {
                this.classList.remove('active');
            });
            
            btn.addEventListener('touchcancel', function() {
                this.classList.remove('active');
            });
        });
    }
    
    function setupAutoDismissAlerts() {
        // Auto-dismiss alerts after 5 seconds
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                if (alert.classList.contains('alert-dismissible')) {
                    const closeButton = alert.querySelector('.btn-close');
                    if (closeButton) {
                        closeButton.click();
                    }
                }
            });
        }, 5000);
    }
    
    function setupResponsiveTables() {
        const tables = document.querySelectorAll('.table-responsive');
        
        function adjustTables() {
            tables.forEach(table => {
                if (window.innerWidth < 768) {
                    table.classList.add('table-sm');
                } else {
                    table.classList.remove('table-sm');
                }
            });
        }
        
        adjustTables();
        window.addEventListener('resize', adjustTables);
    }
    
    function setupTooltips() {
        // Initialize Bootstrap tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    function setupCurrentPageHighlight() {
        // This would normally be handled by Django template
        // Keeping as placeholder for any JS-based highlighting
        console.log('Sales module initialized successfully');
    }
    
    // Export functions if needed
    window.salesModule = {
        initialize: initializeSalesModule,
        setupSidebar: setupSidebar,
        setupTouchFeedback: setupTouchFeedback
    };
})();

function initializeCustomerDetail() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize notes modal
    const notesModal = document.getElementById('notesModal');
    if (notesModal) {
        notesModal.addEventListener('shown.bs.modal', function() {
            const textarea = this.querySelector('textarea');
            if (textarea) {
                textarea.focus();
                textarea.select();
            }
        });
    }
    
    // Animation for activity items
    const activityItems = document.querySelectorAll('.activity-item');
    activityItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 0.1}s`;
        item.classList.add('animate-fade-in-up');
    });
    
    // Sales table row animation
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.animationDelay = `${index * 0.05}s`;
        row.classList.add('animate-fade-in-up');
    });
    
    // Print functionality
    const printBtn = document.createElement('button');
    printBtn.className = 'btn btn-outline-secondary btn-sm ms-2';
    printBtn.innerHTML = '<i class="bi bi-printer me-1"></i>Print';
    printBtn.addEventListener('click', function() {
        window.print();
    });
    
    // Add print button to header
    const headerActions = document.querySelector('.text-md-end .d-flex');
    if (headerActions) {
        headerActions.appendChild(printBtn);
    }
    
    console.log('Customer detail initialized');
}

// Add to the initializeSalesModule function in sales_module.js
// In your existing sales_module.js, update the initializeSalesModule function:

// Add this inside the existing initializeSalesModule() function:
// if (window.location.pathname.includes('customer_detail')) {
//     initializeCustomerDetail();
// }

/*sales list added js */
function initializeSalesList() {
    // Get the filters form
    const filtersForm = document.getElementById('filtersForm');
    if (!filtersForm) return;
    
    // Date range validation
    filtersForm.addEventListener('submit', function(e) {
        const dateFrom = document.getElementById('dateFromFilter');
        const dateTo = document.getElementById('dateToFilter');
        
        if (dateFrom && dateTo && dateFrom.value && dateTo.value) {
            const fromDate = new Date(dateFrom.value);
            const toDate = new Date(dateTo.value);
            
            if (fromDate > toDate) {
                e.preventDefault();
                alert('Error: "From Date" cannot be later than "To Date"');
                dateFrom.focus();
                return false;
            }
        }
        
        // Optional: Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span> Filtering...';
        }
    });
    
    // Auto-submit for certain filters (optional)
    const autoSubmitFilters = ['statusFilter', 'customerFilter', 'stockOutFilter'];
    autoSubmitFilters.forEach(filterId => {
        const filter = document.getElementById(filterId);
        if (filter) {
            filter.addEventListener('change', function() {
                if (this.value) {
                    filtersForm.submit();
                }
            });
        }
    });
    
    // Clear filters button functionality
    const clearBtn = document.querySelector('a[href*="sale_list"]');
    if (clearBtn && window.location.search) {
        clearBtn.addEventListener('click', function(e) {
            if (window.location.search) {
                // If there are filters, clear them
                const formInputs = filtersForm.querySelectorAll('input, select');
                formInputs.forEach(input => {
                    if (input.type === 'text' || input.type === 'date') {
                        input.value = '';
                    } else if (input.tagName === 'SELECT') {
                        input.selectedIndex = 0;
                    }
                });
            }
        });
    };
    
    // Animation for table rows
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.animationDelay = `${index * 0.05}s`;
        row.classList.add('animate-fade-in-up');
    });
    
    // Mobile card view enhancements
    const mobileCards = document.querySelectorAll('.card.border-0.shadow-sm');
    mobileCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Only navigate if not clicking on a button
            if (!e.target.closest('a, button')) {
                const viewLink = this.querySelector('a[href*="sale_detail"]');
                if (viewLink) {
                    window.location.href = viewLink.href;
                }
            }
        });
    });
    
    console.log('Sales list initialized with', tableRows.length, 'sales');
}

// Add to the existing initializeSalesModule function in sales_module.js
// if (window.location.pathname.includes('sale_list')) {
//     initializeSalesList();
// }
/* ================================
   PROFESSIONAL SALE FORM ENGINE
================================ */
class SaleForm {
    constructor(formId, itemsContainerId, addButtonId) {
        this.form = document.getElementById(formId);
        this.itemsContainer = document.getElementById(itemsContainerId);
        this.addButton = document.getElementById(addButtonId);
        
        // ✅ FIX: More robust selector for TOTAL_FORMS
        this.totalFormsInput = document.querySelector('#id_items-TOTAL_FORMS') || 
                               document.querySelector('[name="items-TOTAL_FORMS"]') ||
                               document.querySelector('[name$="TOTAL_FORMS"]');
        
        this.discountInput = document.getElementById('id_discount_amount');
        
        if (!this.form || !this.itemsContainer || !this.totalFormsInput) {
            console.error("SaleForm initialization failed:", {
                form: this.form,
                itemsContainer: this.itemsContainer,
                totalFormsInput: this.totalFormsInput
            });
            return;
        }
        
        this.init();
    }

    init() {
        this.attachEvents();
        this.calculateAll();
    }

    attachEvents() {
        // Live recalculation
        this.itemsContainer.addEventListener('input', (e) => {
            if (
                e.target.name?.includes('quantity') ||
                e.target.name?.includes('unit_price') ||
                e.target.name?.includes('tax_rate')
            ) {
                this.calculateAll();
            }
        });

        // Discount change
        if (this.discountInput) {
            this.discountInput.addEventListener('input', () => {
                this.calculateAll();
            });
        }

        // Add new item
        if (this.addButton) {
            this.addButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.addForm();
            });
        }

        // Remove item - Use event delegation
        this.itemsContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.remove-item-btn');
            if (btn) {
                e.preventDefault();
                const card = btn.closest('.item-form-card');
                this.removeForm(card);
            }
        });

        // Disable button on submit
        this.form.addEventListener('submit', () => {
            const btn = document.getElementById('submitBtn');
            if (btn) btn.disabled = true;
        });
    }

    addForm() {
        const formCount = parseInt(this.totalFormsInput.value);
        const emptyFormTemplate = document.getElementById('empty-form-template');
        
        if (!emptyFormTemplate) {
            console.error("Missing empty form template.");
            return;
        }

        const newFormHtml = emptyFormTemplate.innerHTML.replace(/__prefix__/g, formCount);
        const wrapper = document.createElement('div');
        wrapper.innerHTML = newFormHtml;
        
        const newForm = wrapper.firstElementChild;
        this.itemsContainer.appendChild(newForm);
        
        this.totalFormsInput.value = formCount + 1;
        this.calculateAll();
    }

    removeForm(formCard) {
        if (!formCard) return;
        
        const deleteInput = formCard.querySelector('input[name$="DELETE"]');
        
        if (deleteInput) {
            // ✅ FIX: Existing form - mark for deletion
            deleteInput.value = 'on';
            deleteInput.checked = true;
            formCard.style.display = 'none';
        } else {
            // ✅ FIX: New form - remove from DOM
            formCard.remove();
            
            // ✅ FIX: Safely update TOTAL_FORMS
            if (this.totalFormsInput) {
                const currentValue = parseInt(this.totalFormsInput.value) || 0;
                this.totalFormsInput.value = Math.max(0, currentValue - 1);
            } else {
                // Fallback - try to find it again
                this.totalFormsInput = document.querySelector('#id_items-TOTAL_FORMS');
                if (this.totalFormsInput) {
                    const currentValue = parseInt(this.totalFormsInput.value) || 0;
                    this.totalFormsInput.value = Math.max(0, currentValue - 1);
                }
            }
        }
        
        this.calculateAll();
    }

    calculateAll() {
        let subtotal = 0;
        let totalTax = 0;

        const forms = this.itemsContainer.querySelectorAll('.item-form-card');
        
        forms.forEach((form) => {
            if (form.style.display === 'none') return;

            const quantityInput = form.querySelector('[name$="quantity"]');
            const unitPriceInput = form.querySelector('[name$="unit_price"]');
            const taxRateInput = form.querySelector('[name$="tax_rate"]');

            const quantity = parseFloat(quantityInput?.value) || 0;
            const unitPrice = parseFloat(unitPriceInput?.value) || 0;
            const taxRate = parseFloat(taxRateInput?.value) || 0;

            const lineTotal = this.round(quantity * unitPrice);
            const taxAmount = this.round(lineTotal * (taxRate / 100));

            subtotal += lineTotal;
            totalTax += taxAmount;

            const totalDisplay = form.querySelector('.item-total');
            if (totalDisplay) {
                totalDisplay.innerText = `Tsh ${this.format(lineTotal)}`;
            }
        });

        const discount = parseFloat(this.discountInput?.value) || 0;
        const grandTotal = this.round(subtotal + totalTax - discount);

        // Update summary display
        const subtotalEl = document.getElementById('subtotal');
        const taxEl = document.getElementById('tax');
        const discountEl = document.getElementById('discount');
        const totalEl = document.getElementById('total');
        
        if (subtotalEl) subtotalEl.innerText = this.format(subtotal);
        if (taxEl) taxEl.innerText = this.format(totalTax);
        if (discountEl) discountEl.innerText = this.format(discount);
        if (totalEl) totalEl.innerText = this.format(grandTotal);
    }

    round(value) {
        return Math.round((value + Number.EPSILON) * 100) / 100;
    }

    format(number) {
        return number.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}