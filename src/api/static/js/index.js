// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add active state to nav links
const currentPage = window.location.pathname;
document.querySelectorAll('a[href]').forEach(link => {
    if (link.getAttribute('href') === currentPage) {
        link.style.fontWeight = 'bold';
        link.style.borderBottom = '2px solid var(--accent-color)';
    }
});