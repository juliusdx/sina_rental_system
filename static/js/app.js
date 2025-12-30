/* Sidebar Toggle Logic */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
}

// Auto-close on mobile when link clicked
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            closeSidebar();
        }
    });
});

console.log('Rental System Loaded');
