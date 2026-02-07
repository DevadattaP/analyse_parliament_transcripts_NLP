// Make upload endpoint clickable on home page
document.addEventListener('DOMContentLoaded', function() {
    const uploadEndpoint = document.getElementById('upload-endpoint');
    if (uploadEndpoint) {
        uploadEndpoint.addEventListener('click', function() {
            window.location.href = '/upload';
        });
        
        // Add hover effect
        uploadEndpoint.style.cursor = 'pointer';
        uploadEndpoint.style.transition = 'background-color 0.3s ease';
        
        uploadEndpoint.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f0f9f0';
        });
        
        uploadEndpoint.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
        });
    }
    
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

});