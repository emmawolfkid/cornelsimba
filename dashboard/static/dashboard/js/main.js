// cornelsimba/static/js/main.js

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
        });
    } else if (viewType === 'compact') {
        moduleGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
        moduleGrid.querySelectorAll('.module-card').forEach(card => {
            card.style.padding = '20px';
            card.querySelector('.module-description').style.display = 'none';
        });
    } else {
        moduleGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(250px, 1fr))';
        moduleGrid.querySelectorAll('.module-card').forEach(card => {
            card.style.display = 'block';
            card.style.padding = '30px';
            card.querySelector('.module-description').style.display = 'block';
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
    
    // Update pagination
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
    // Add your page change logic here
}