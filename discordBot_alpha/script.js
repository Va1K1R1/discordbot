/**
 * Discord Bot Portfolio Website JavaScript
 * Adds interactivity to the portfolio website
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all interactive elements
    initNavigation();
    initSmoothScrolling();
    initCodeBlocks();
    initActiveNavLinks();
    hljs.highlightAll(); // Initialize syntax highlighting
});

/**
 * Mobile Navigation Menu Toggle
 */
function initNavigation() {
    const menuToggle = document.getElementById('menu-toggle');
    const navLinks = document.getElementById('nav-links');
    
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!event.target.closest('#main-nav')) {
                navLinks.classList.remove('active');
            }
        });
        
        // Close menu when a link is clicked
        const links = navLinks.querySelectorAll('a');
        links.forEach(link => {
            link.addEventListener('click', function() {
                navLinks.classList.remove('active');
            });
        });
    }
}

/**
 * Smooth Scrolling for Navigation Links
 */
function initSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                // Smooth scroll to target
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL hash without jumping
                history.pushState(null, null, targetId);
            }
        });
    });
}

/**
 * Code Block Interactivity
 */
function initCodeBlocks() {
    const codeBlocks = document.querySelectorAll('.code-example');
    
    codeBlocks.forEach(block => {
        // Add copy button to code blocks
        const codeElement = block.querySelector('pre code');
        if (codeElement) {
            const copyButton = document.createElement('button');
            copyButton.className = 'copy-button';
            copyButton.innerHTML = '<i class="fas fa-copy"></i>';
            copyButton.title = 'Copy to clipboard';
            
            // Insert button before the pre element
            const preElement = block.querySelector('pre');
            preElement.parentNode.insertBefore(copyButton, preElement);
            
            // Add copy functionality
            copyButton.addEventListener('click', function() {
                const code = codeElement.textContent;
                navigator.clipboard.writeText(code).then(() => {
                    // Show success feedback
                    copyButton.innerHTML = '<i class="fas fa-check"></i>';
                    copyButton.classList.add('success');
                    
                    // Reset after 2 seconds
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                        copyButton.classList.remove('success');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy code: ', err);
                    copyButton.innerHTML = '<i class="fas fa-times"></i>';
                    copyButton.classList.add('error');
                    
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                        copyButton.classList.remove('error');
                    }, 2000);
                });
            });
        }
    });
}

/**
 * Highlight Active Navigation Link
 */
function initActiveNavLinks() {
    const sections = document.querySelectorAll('.section');
    const navLinks = document.querySelectorAll('#nav-links a');
    
    // Update active link on scroll
    window.addEventListener('scroll', function() {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            
            // 100px offset to trigger slightly before reaching the section
            if (pageYOffset >= (sectionTop - 100)) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
}

/**
 * Add CSS styles for JavaScript-added elements
 */
function addDynamicStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .copy-button {
            position: absolute;
            right: 10px;
            top: 10px;
            background-color: var(--bg-light);
            border: none;
            border-radius: var(--radius-sm);
            color: var(--text-normal);
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all var(--transition-fast);
            z-index: 10;
        }
        
        .copy-button:hover {
            background-color: var(--discord-primary);
            color: var(--text-bright);
        }
        
        .copy-button.success {
            background-color: var(--discord-success);
            color: var(--text-bright);
        }
        
        .copy-button.error {
            background-color: var(--discord-error);
            color: var(--text-bright);
        }
        
        .code-example pre {
            position: relative;
            padding-top: 2.5rem;
        }
    `;
    document.head.appendChild(style);
}

// Add dynamic styles when DOM is loaded
document.addEventListener('DOMContentLoaded', addDynamicStyles);

/**
 * Lazy Load Images
 */
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const image = entry.target;
                    image.src = image.dataset.src;
                    image.removeAttribute('data-src');
                    imageObserver.unobserve(image);
                }
            });
        });
        
        images.forEach(image => {
            imageObserver.observe(image);
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        images.forEach(image => {
            image.src = image.dataset.src;
            image.removeAttribute('data-src');
        });
    }
}

// Initialize lazy loading when DOM is loaded
document.addEventListener('DOMContentLoaded', lazyLoadImages);

/**
 * Add animation to elements when they come into view
 */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.tech-highlight, .table-item, .timeline-item, .challenge-item');
    
    if ('IntersectionObserver' in window) {
        const animationObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate');
                    animationObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });
        
        animatedElements.forEach(element => {
            element.classList.add('pre-animation');
            animationObserver.observe(element);
        });
    }
}

// Initialize scroll animations when DOM is loaded
document.addEventListener('DOMContentLoaded', initScrollAnimations);

// Add animation styles
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .pre-animation {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }
        
        .animate {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
});