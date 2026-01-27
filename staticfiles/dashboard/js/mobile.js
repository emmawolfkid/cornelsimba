// cornelsimba/static/js/mobile.js

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
        
        if (isMobile) {
            moduleCards.forEach(card => {
                card.style.padding = '20px';
                card.querySelector('.module-description').style.minHeight = 'auto';
            });
        }
    }
    
    // Run on load and resize
    adjustForMobile();
    window.addEventListener('resize', adjustForMobile);
});