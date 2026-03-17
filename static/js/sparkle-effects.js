/**
 * FabVibe - Professional Sparkle and Animation Effects
 */

// Create sparkle effect on mouse move
document.addEventListener('DOMContentLoaded', function() {
    let sparkleTimeout;
    
    // Sparkle on mouse move
    document.addEventListener('mousemove', function(e) {
        clearTimeout(sparkleTimeout);
        sparkleTimeout = setTimeout(() => {
            createSparkle(e.pageX, e.pageY);
        }, 50);
    });
    
    // Create floating particles
    createFloatingParticles();
    
    // Add shimmer effect to cards
    addShimmerEffect();
    
    // Add pulse effect to buttons
    addPulseEffect();
});

// Create sparkle at position
function createSparkle(x, y) {
    const sparkle = document.createElement('div');
    sparkle.className = 'sparkle';
    sparkle.style.left = x + 'px';
    sparkle.style.top = y + 'px';
    sparkle.style.animationDelay = Math.random() * 0.3 + 's';
    
    document.body.appendChild(sparkle);
    
    setTimeout(() => {
        sparkle.remove();
    }, 3000);
}

// Create floating particles
function createFloatingParticles() {
    const particleCount = 20;
    
    for (let i = 0; i < particleCount; i++) {
        setTimeout(() => {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (15 + Math.random() * 10) + 's';
            particle.style.animationDelay = Math.random() * 5 + 's';
            
            document.body.appendChild(particle);
        }, i * 200);
    }
}

// Add shimmer effect to cards on hover
function addShimmerEffect() {
    const cards = document.querySelectorAll('.card, .product-card, .category-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.animation = 'shimmer 0.6s ease';
        });
        
        card.addEventListener('animationend', function() {
            this.style.animation = '';
        });
    });
}

// Add pulse effect to buttons
function addPulseEffect() {
    const buttons = document.querySelectorAll('.btn-primary, .hero-btn');
    
    buttons.forEach(button => {
        // Add subtle pulse animation
        setInterval(() => {
            button.style.animation = 'pulse 2s ease-in-out';
            setTimeout(() => {
                button.style.animation = '';
            }, 2000);
        }, 5000);
    });
}

// Shimmer animation
const style = document.createElement('style');
style.textContent = `
    @keyframes shimmer {
        0% {
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
        }
        50% {
            box-shadow: 0 8px 30px rgba(59, 130, 246, 0.4), 0 0 20px rgba(96, 165, 250, 0.3);
        }
        100% {
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }
        50% {
            box-shadow: 0 4px 25px rgba(59, 130, 246, 0.6), 0 0 30px rgba(96, 165, 250, 0.4);
        }
    }
    
    /* Glow effect on hover */
    .card:hover,
    .product-card:hover,
    .category-card:hover {
        animation: glow 1.5s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from {
            box-shadow: 0 12px 35px rgba(59, 130, 246, 0.25);
        }
        to {
            box-shadow: 0 12px 35px rgba(59, 130, 246, 0.4), 0 0 30px rgba(96, 165, 250, 0.2);
        }
    }
    
    /* Smooth scroll reveal */
    .fade-in-section {
        opacity: 0;
        transform: translateY(30px);
        transition: opacity 0.6s ease, transform 0.6s ease;
    }
    
    .fade-in-section.is-visible {
        opacity: 1;
        transform: translateY(0);
    }
`;
document.head.appendChild(style);

// Scroll reveal animation
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
        }
    });
}, observerOptions);

// Observe sections
document.addEventListener('DOMContentLoaded', function() {
    const sections = document.querySelectorAll('.featured-categories, .new-arrivals, .product-card, .category-card');
    sections.forEach(section => {
        section.classList.add('fade-in-section');
        observer.observe(section);
    });
});

// Add ripple effect on click
document.addEventListener('click', function(e) {
    const target = e.target.closest('.btn, .card, a');
    if (target) {
        const ripple = document.createElement('span');
        const rect = target.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            left: ${x}px;
            top: ${y}px;
            pointer-events: none;
            animation: ripple 0.6s ease-out;
        `;
        
        const rippleStyle = document.createElement('style');
        rippleStyle.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(2);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(rippleStyle);
        
        if (target.style.position !== 'absolute' && target.style.position !== 'relative') {
            target.style.position = 'relative';
        }
        target.style.overflow = 'hidden';
        target.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    }
});

// Parallax effect on scroll (disabled for navbar to keep it fixed)
window.addEventListener('scroll', function() {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll('.hero-carousel');
    
    parallaxElements.forEach(element => {
        const speed = 0.5;
        element.style.transform = `translateY(${scrolled * speed}px)`;
    });
});

console.log('✨ FabVibe sparkle effects loaded!');
