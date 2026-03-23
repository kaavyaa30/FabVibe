/**
 * FabVibe - Lightweight effects (heavy animations removed for performance)
 */

// Scroll reveal animation only
const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

document.addEventListener('DOMContentLoaded', function() {
    // Only apply fade-in to section containers, NOT individual product cards
    // (product cards are already visible on load and should not start at opacity:0)
    const sections = document.querySelectorAll('.featured-categories, .new-arrivals');
    sections.forEach(section => {
        section.classList.add('fade-in-section');
        observer.observe(section);
    });
});

const style = document.createElement('style');
style.textContent = `
    .fade-in-section {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.4s ease, transform 0.4s ease;
    }
    .fade-in-section.is-visible {
        opacity: 1;
        transform: translateY(0);
    }
`;
document.head.appendChild(style);
