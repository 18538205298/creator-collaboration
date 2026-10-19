/**
 * 通用分页组件#处理分页跳转和定位
 */
class PaginationHandler {
    /**
     * 初始化分页处理器
     * @param {string} paginationSelector - 分页容器选择器
     * @param {string} anchorId - 分页锚点ID
     * @param {string} storageKey - 本地存储键名
     */
    constructor(paginationSelector = '.pagination', anchorId = 'pagination-anchor', storageKey = 'scroll_position') {
        this.paginationSelector = paginationSelector;
        this.anchorId = anchorId;
        this.storageKey = storageKey;
        this.init();
    }
    
    /**
     * 初始化分页组件
     */
    init() {
        this.handlePageLoad();
        this.bindPaginationLinks();
    }
    
    /**
     * 处理页面加载时的滚动定位
     */
    handlePageLoad() {
        if (window.location.hash === `#${this.anchorId}`) {
            const savedPosition = localStorage.getItem(this.storageKey);
            if (savedPosition) {
                setTimeout(() => {
                    window.scrollTo({
                        top: parseInt(savedPosition),
                        behavior: 'instant'
                    });
                    localStorage.removeItem(this.storageKey);
                }, 50);
            } else {
                setTimeout(() => {
                    const paginationAnchor = document.getElementById(this.anchorId);
                    if (paginationAnchor) {
                        window.scrollTo({
                            top: paginationAnchor.offsetTop - 100,
                            behavior: 'smooth'
                        });
                    }
                }, 100);
            }
        }
    }
    
    /**
     * 绑定分页链接点击事件
     */
    bindPaginationLinks() {
        const paginationLinks = document.querySelectorAll(`${this.paginationSelector} .page-link`);
        paginationLinks.forEach(link => {
            if (link.href && !link.href.includes('#')) {
                link.href = `${link.href}#${this.anchorId}`;
                
                link.addEventListener('click', () => {
                    localStorage.setItem(this.storageKey, window.scrollY);
                });
            }
        });
    }
}

// 导出分页处理器
window.PaginationHandler = PaginationHandler; 