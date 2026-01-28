// 代码高亮和编辑器功能
class CodeHighlighter {
    constructor() {
        this.init();
    }
    
    init() {
        this.highlightCodeBlocks();
        this.setupCodeEditor();
    }
    
    highlightCodeBlocks() {
        document.querySelectorAll('pre code').forEach((block) => {
            Prism.highlightElement(block);
        });
    }
    
    setupCodeEditor() {
        // 简单的代码编辑器
        const codeAreas = document.querySelectorAll('.code-textarea');
        codeAreas.forEach(area => {
            area.addEventListener('input', this.debounce(() => {
                this.updatePreview(area);
            }, 300));
        });
    }
    
    updatePreview(textarea) {
        const preview = textarea.parentElement.querySelector('.code-preview');
        if (preview) {
            const code = textarea.value;
            const language = textarea.dataset.language || 'javascript';
            preview.innerHTML = `<pre><code class="language-${language}">${this.escapeHtml(code)}</code></pre>`;
            this.highlightCodeBlocks();
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// 现代化UI组件
class ModernUI {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupAnimations();
        this.setupToasts();
        this.setupModals();
        this.setupTheme();
    }
    
    setupAnimations() {
        // 添加微交互动画
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn') || e.target.classList.contains('action-btn')) {
                this.addRippleEffect(e);
            }
        });
    }
    
    addRippleEffect(e) {
        const button = e.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
    
    setupToasts() {
        this.toastContainer = document.getElementById('toast-container') || this.createToastContainer();
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 13000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(container);
        return container;
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${this.getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
        `;
        
        this.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    getToastIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }
    
    setupModals() {
        // 模态框增强
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                this.closeModal(e.target);
            }
            if (e.target.classList.contains('modal-close')) {
                this.closeModal(e.target.closest('.modal-overlay'));
            }
        });
    }
    
    showModal(content) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay show';
        overlay.innerHTML = `
            <div class="modal">
                <div class="modal-content">
                    ${content}
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }
    
    closeModal(overlay) {
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        }
    }
    
    setupTheme() {
        // 主题切换
        this.currentTheme = localStorage.getItem('theme') || 'dark';
        this.applyTheme(this.currentTheme);
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
    }
    
    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
    }
}

// 性能优化
class PerformanceOptimizer {
    constructor() {
        this.init();
    }
    
    init() {
        this.lazyLoadImages();
        this.setupVirtualScroll();
        this.optimizeAnimations();
    }
    
    lazyLoadImages() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
    
    setupVirtualScroll() {
        // 虚拟滚动实现
        const containers = document.querySelectorAll('.virtual-scroll');
        containers.forEach(container => {
            this.implementVirtualScroll(container);
        });
    }
    
    implementVirtualScroll(container) {
        const itemHeight = 60;
        const visibleCount = Math.ceil(container.clientHeight / itemHeight);
        const buffer = 5;
        
        container.addEventListener('scroll', this.debounce(() => {
            const scrollTop = container.scrollTop;
            const startIndex = Math.floor(scrollTop / itemHeight);
            const endIndex = Math.min(startIndex + visibleCount + buffer, container.children.length);
            
            // 更新可见项
            for (let i = 0; i < container.children.length; i++) {
                const child = container.children[i];
                if (i >= startIndex - buffer && i <= endIndex) {
                    child.style.display = 'block';
                    child.style.transform = `translateY(${i * itemHeight}px)`;
                } else {
                    child.style.display = 'none';
                }
            }
        }, 16));
    }
    
    optimizeAnimations() {
        // 使用 CSS transforms 而不是 top/left
        const animatedElements = document.querySelectorAll('.animate');
        animatedElements.forEach(el => {
            el.style.willChange = 'transform';
        });
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.codeHighlighter = new CodeHighlighter();
    window.modernUI = new ModernUI();
    window.performanceOptimizer = new PerformanceOptimizer();
});