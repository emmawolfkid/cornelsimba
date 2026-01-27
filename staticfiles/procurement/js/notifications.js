// Notification system
class NotificationSystem {
    static show(message, type = 'info', duration = 5000) {
        const container = document.querySelector('.messages-container') || this.createContainer();
        const notification = document.createElement('div');
        
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close"><i class="fas fa-times"></i></button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            this.removeNotification(notification);
        }, duration);
        
        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.removeNotification(notification);
        });
    }
    
    static getIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    static createContainer() {
        const container = document.createElement('div');
        container.className = 'messages-container';
        const mainContent = document.querySelector('.main-content');
        const header = mainContent.querySelector('.header');
        header.after(container);
        return container;
    }
    
    static removeNotification(notification) {
        notification.style.animation = 'slideDown 0.4s ease reverse';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 400);
    }
}

// Expose to global scope
window.NotificationSystem = NotificationSystem;

// Auto-hide Django messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.alert');
    messages.forEach(msg => {
        setTimeout(() => {
            if (msg.parentNode) {
                msg.style.animation = 'slideDown 0.4s ease reverse';
                setTimeout(() => {
                    if (msg.parentNode) {
                        msg.parentNode.removeChild(msg);
                    }
                }, 400);
            }
        }, 5000);
        
        // Add close button to Django messages
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.className = 'notification-close';
        closeBtn.style.cssText = `
            margin-left: auto;
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            opacity: 0.7;
        `;
        closeBtn.addEventListener('click', function() {
            msg.style.animation = 'slideDown 0.4s ease reverse';
            setTimeout(() => {
                if (msg.parentNode) {
                    msg.parentNode.removeChild(msg);
                }
            }, 400);
        });
        msg.appendChild(closeBtn);
    });
});