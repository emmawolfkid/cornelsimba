// Touch swipe for mobile
document.addEventListener('DOMContentLoaded', function() {
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const sidebar = document.getElementById('sidebar');
        
        if (touchStartX - touchEndX > swipeThreshold) {
            // Swipe left - close sidebar if open
            if (sidebar && sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
                const toggleBtn = document.getElementById('mobileNavToggle');
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<i class="fas fa-bars"></i> Browse Modules';
                }
            }
        } else if (touchEndX - touchStartX > swipeThreshold) {
            // Swipe right - open sidebar
            if (sidebar && !sidebar.classList.contains('active')) {
                sidebar.classList.add('active');
                const toggleBtn = document.getElementById('mobileNavToggle');
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<i class="fas fa-times"></i> Close Modules';
                }
            }
        }
    }
    
    // Adjust module cards for mobile
    function adjustForMobile() {
        const isMobile = window.innerWidth <= 768;
        const moduleCards = document.querySelectorAll('.module-card');
        const leaveCards = document.querySelectorAll('.leave-card');
        
        if (isMobile) {
            moduleCards.forEach(card => {
                card.style.padding = '20px';
                const desc = card.querySelector('.module-description');
                if (desc) desc.style.minHeight = 'auto';
            });
            
            leaveCards.forEach(card => {
                card.style.padding = '20px';
            });
        }
    }
    
    // Run on load and resize
    adjustForMobile();
    window.addEventListener('resize', adjustForMobile);
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        const sidebar = document.getElementById('sidebar');
        const toggleBtn = document.getElementById('mobileNavToggle');
        
        if (window.innerWidth <= 768 && 
            sidebar && sidebar.classList.contains('active') &&
            !sidebar.contains(event.target) && 
            toggleBtn && !toggleBtn.contains(event.target)) {
            sidebar.classList.remove('active');
            toggleBtn.innerHTML = '<i class="fas fa-bars"></i> Browse Modules';
        }
    });
});