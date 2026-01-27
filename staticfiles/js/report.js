// report.js - External JavaScript file for sales reports

class SalesReportCharts {
    constructor(dailyData, salesByTypeData, productData) {
        this.dailyData = dailyData || [];
        this.salesByTypeData = salesByTypeData || [];
        this.productData = productData || [];
        this.charts = {};
    }

    initializeCharts() {
        try {
            console.log("Initializing charts with data:", {
                dailyData: this.dailyData,
                salesByTypeData: this.salesByTypeData,
                productData: this.productData
            });

            this.initializeTrendChart();
            this.initializeSalesTypeChart();
            this.initializeProductChart();

        } catch (error) {
            console.error('Error initializing charts:', error);
        }
    }

    initializeTrendChart() {
        const salesTrendCtx = document.getElementById('salesTrendChart');
        if (!salesTrendCtx) return;

        if (this.dailyData.length === 0) {
            this.showEmptyState(salesTrendCtx, 'No sales trend data available');
            return;
        }

        const trendChart = new Chart(salesTrendCtx, {
            type: 'line',
            data: {
                labels: this.dailyData.map(d => {
                    const date = new Date(d.sale_date);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }),
                datasets: [{
                    label: 'Daily Revenue (Tsh)',
                    data: this.dailyData.map(d => d.total_amount),
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#4f46e5',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return 'Tsh ' + (value / 1000000).toFixed(1) + 'M';
                                } else if (value >= 1000) {
                                    return 'Tsh ' + (value / 1000).toFixed(1) + 'K';
                                }
                                return 'Tsh ' + value;
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Tsh ${context.raw.toLocaleString('en-US')}`;
                            }
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });

        this.charts.trendChart = trendChart;

        const trendChartType = document.getElementById('trendChartType');
        if (trendChartType) {
            trendChartType.addEventListener('change', (e) => {
                trendChart.config.type = e.target.value;
                trendChart.update();
            });
        }
    }

    initializeSalesTypeChart() {
        const salesTypeCtx = document.getElementById('salesTypeChart');
        if (!salesTypeCtx) return;

        if (this.salesByTypeData.length === 0) {
            this.showEmptyState(salesTypeCtx, 'No sales type data available');
            return;
        }

        const typeChart = new Chart(salesTypeCtx, {
            type: 'doughnut',
            data: {
                labels: this.salesByTypeData.map(t => t.sale_type),
                datasets: [{
                    data: this.salesByTypeData.map(t => t.amount),
                    backgroundColor: [
                        '#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#3b82f6',
                        '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1'
                    ],
                    borderWidth: 1,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${context.label}: Tsh ${value.toLocaleString('en-US')} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        this.charts.salesTypeChart = typeChart;
    }

    initializeProductChart() {
        const productDistCtx = document.getElementById('productDistributionChart');
        if (!productDistCtx) return;

        if (this.productData.length === 0) {
            this.showEmptyState(productDistCtx, 'No product revenue data available');
            return;
        }

        const productChart = new Chart(productDistCtx, {
            type: 'bar',
            data: {
                labels: this.productData.map(p => {
                    const name = p.item__name;
                    return name.length > 15 ? name.substring(0, 15) + '...' : name;
                }),
                datasets: [{
                    label: 'Revenue (Tsh)',
                    data: this.productData.map(p => p.total_amount),
                    backgroundColor: '#4f46e5',
                    borderColor: '#4f46e5',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return 'Tsh ' + (value / 1000000).toFixed(1) + 'M';
                                } else if (value >= 1000) {
                                    return 'Tsh ' + (value / 1000).toFixed(1) + 'K';
                                }
                                return 'Tsh ' + value;
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Tsh ${context.raw.toLocaleString('en-US')}`;
                            }
                        }
                    }
                }
            }
        });

        this.charts.productChart = productChart;
    }

    showEmptyState(canvasElement, message) {
        const container = canvasElement.parentElement;
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-bar-chart-line"></i>
                <p>${message}</p>
            </div>
        `;
    }
}

// Utility functions
class ReportUtils {
    static formatCurrencyElements() {
        const currencyElements = document.querySelectorAll('.currency-display');
        currencyElements.forEach(el => {
            const text = el.textContent;
            const amount = text.replace('Tsh ', '').replace(/,/g, '');
            const num = parseFloat(amount);
            if (!isNaN(num)) {
                el.textContent = `Tsh ${num.toLocaleString('en-US', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                })}`;
            }
        });
    }

    static setupDateValidation() {
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        if (!startDate || !endDate) return;

        startDate.addEventListener('change', function() {
            endDate.min = this.value;
        });
        
        endDate.addEventListener('change', function() {
            startDate.max = this.value;
        });
        
        if (startDate.value) {
            endDate.min = startDate.value;
        }
        if (endDate.value) {
            startDate.max = endDate.value;
        }
    }

    static setupQuickPeriod() {
        const quickPeriod = document.getElementById('quickPeriod');
        if (!quickPeriod) return;

        quickPeriod.addEventListener('change', function() {
            const today = new Date();
            let start = new Date();
            let end = new Date();
            
            switch(this.value) {
                case 'today':
                    start.setHours(0, 0, 0, 0);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'yesterday':
                    start.setDate(start.getDate() - 1);
                    start.setHours(0, 0, 0, 0);
                    end.setDate(end.getDate() - 1);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'week':
                    const day = start.getDay();
                    const diff = start.getDate() - day + (day === 0 ? -6 : 1);
                    start.setDate(diff);
                    start.setHours(0, 0, 0, 0);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'month':
                    start.setDate(1);
                    start.setHours(0, 0, 0, 0);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'last_month':
                    start.setMonth(start.getMonth() - 1, 1);
                    start.setHours(0, 0, 0, 0);
                    end.setMonth(end.getMonth(), 0);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'quarter':
                    const quarter = Math.floor(today.getMonth() / 3);
                    start.setMonth(quarter * 3, 1);
                    start.setHours(0, 0, 0, 0);
                    end.setMonth((quarter + 1) * 3, 0);
                    end.setHours(23, 59, 59, 999);
                    break;
                case 'year':
                    start.setMonth(0, 1);
                    start.setHours(0, 0, 0, 0);
                    end.setMonth(11, 31);
                    end.setHours(23, 59, 59, 999);
                    break;
                default:
                    return;
            }
            
            const formatDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            
            const startDateInput = document.getElementById('startDate');
            const endDateInput = document.getElementById('endDate');
            
            if (startDateInput) startDateInput.value = formatDate(start);
            if (endDateInput) endDateInput.value = formatDate(end);
            
            document.getElementById('reportFilterForm').submit();
        });
    }

    static setupPrintButton() {
        const printBtn = document.querySelector('button[onclick="window.print()"]');
        if (!printBtn) return;

        printBtn.addEventListener('click', function() {
            const originalText = this.innerHTML;
            this.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                Preparing...
            `;
            
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 1000);
        });
    }
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    // Setup utility functions
    ReportUtils.formatCurrencyElements();
    ReportUtils.setupDateValidation();
    ReportUtils.setupQuickPeriod();
    ReportUtils.setupPrintButton();

    // Initialize charts if data is available
    if (typeof dailyData !== 'undefined' && typeof salesByTypeData !== 'undefined' && typeof productData !== 'undefined') {
        const chartManager = new SalesReportCharts(dailyData, salesByTypeData, productData);
        
        // Small delay to ensure DOM is fully loaded
        setTimeout(() => {
            chartManager.initializeCharts();
        }, 100);
    }
});