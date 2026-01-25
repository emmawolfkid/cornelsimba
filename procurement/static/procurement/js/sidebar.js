// Sidebar toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebarClose = document.getElementById('sidebarClose');
    
    // Toggle sidebar on mobile
    mobileMenuBtn?.addEventListener('click', function() {
        sidebar.classList.toggle('open');
    });
    
    // Close sidebar on mobile
    sidebarClose?.addEventListener('click', function() {
        sidebar.classList.remove('open');
    });
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 1024) {
            if (!sidebar.contains(event.target) && !mobileMenuBtn.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
    
    // Toggle sidebar on desktop (optional feature)
    const toggleSidebarDesktop = localStorage.getItem('sidebarClosed') === 'true';
    if (toggleSidebarDesktop && window.innerWidth > 1024) {
        document.body.classList.add('sidebar-closed');
    }
    
    // Add toggle button for desktop (optional)
    const toggleBtn = document.createElement('button');
    toggleBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    toggleBtn.className = 'sidebar-toggle-desktop';
    toggleBtn.style.cssText = `
        position: fixed;
        top: 20px;
        left: var(--sidebar-width);
        z-index: 1001;
        background: var(--primary);
        color: white;
        border: none;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        cursor: pointer;
        display: none;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
    `;
    
    if (window.innerWidth > 1024) {
        document.body.appendChild(toggleBtn);
        toggleBtn.style.display = 'flex';
        
        toggleBtn.addEventListener('click', function() {
            const isClosed = document.body.classList.toggle('sidebar-closed');
            localStorage.setItem('sidebarClosed', isClosed);
            
            if (isClosed) {
                toggleBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
                toggleBtn.style.left = '20px';
            } else {
                toggleBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
                toggleBtn.style.left = 'var(--sidebar-width)';
            }
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 1024) {
            sidebar.classList.remove('open');
        }
    });
});