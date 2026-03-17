/**
 * FabVibe - Modern Interactive UI
 * All animations and effects DISABLED per user request
 */

document.addEventListener('DOMContentLoaded', function() {
    // All modern UI features disabled
    console.log('Modern UI animations disabled');
});

function initModernUI() {
    // All features disabled
    return;
}

// Smooth Scroll - DISABLED
function initSmoothScroll() {
    return;
}

// Parallax Effects - DISABLED
function initParallaxEffects() {
    return;
}

// Advanced Card Animations - DISABLED
function initCardAnimations() {
    // All card animations disabled for cleaner user experience
    return;
}

// Magnetic Button Effect (Disabled)
function initMagneticButtons() {
    // Magnetic button effect disabled - too distracting
    return;
}

// Custom Cursor Effects (Disabled)
function initCursorEffects() {
    // Custom cursor disabled for better user experience
    return;
}

// Scroll Reveal Animations - DISABLED
function initScrollReveal() {
    return;
}

// Image Hover Effects - DISABLED
function initImageHoverEffects() {
    return;
}

// Navbar Effects - DISABLED
function initNavbarEffects() {
    return;
}

// Loading Animations - DISABLED
function initLoadingAnimations() {
    // Just mark as loaded without animations
    document.body.classList.add('loaded');
}

// Price Counter Animation - DISABLED
// Prices now display as static text without animation
// function animateValue(element, start, end, duration) {
//     let startTimestamp = null;
//     const step = (timestamp) => {
//         if (!startTimestamp) startTimestamp = timestamp;
//         const progress = Math.min((timestamp - startTimestamp) / duration, 1);
//         const value = Math.floor(progress * (end - start) + start);
//         element.textContent = '₹' + value.toLocaleString();
//         if (progress < 1) {
//             window.requestAnimationFrame(step);
//         }
//     };
//     window.requestAnimationFrame(step);
// }

// Initialize price animations when visible - DISABLED
// const priceObserver = new IntersectionObserver((entries) => {
//     entries.forEach(entry => {
//         if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
//             const priceText = entry.target.textContent.replace(/[₹,]/g, '');
//             const price = parseInt(priceText);
//             if (!isNaN(price)) {
//                 animateValue(entry.target, 0, price, 1000);
//                 entry.target.classList.add('animated');
//             }
//         }
//     });
// });

// document.querySelectorAll('.product-price').forEach(price => {
//     priceObserver.observe(price);
// });

// Ripple effect - DISABLED
// All button animations disabled

console.log('Modern UI animations disabled');
