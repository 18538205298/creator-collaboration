/**
 * 通用任务详情模态框组件
 * 用于显示广告任务的详细信息
 */

class TaskDetailModal {
    constructor() {
        this.modalId = 'taskDetailModal';
        this.createModal();
        this.registerEvents();
        this.addModalStyles();
    }

    /**
     * 创建模态框HTML结构并添加到body
     */
    createModal() {
        // 检查模态框是否已存在
        if (document.getElementById(this.modalId)) return;

        const modalHTML = `
        <div class="modal fade" id="${this.modalId}" tabindex="-1" aria-labelledby="taskDetailModalLabel" aria-hidden="true" style="display: none;">
            <div class="modal-dialog modal-lg modal-dialog-centered" style="max-width: 1500px; margin: 1.75rem auto;">
                <div class="modal-content" style="border-radius: 12px; overflow: hidden;">
                    <div class="modal-header profile-inner-card-header" style="border-bottom: none; padding-bottom: 0; padding: 20px 25px 10px;">
                        <div class="profile-inner-card-icon">
                            <i class="bi bi-file-earmark-text"></i>
                        </div>
                        <h5 class="profile-inner-card-title" id="taskDetailModalLabel">任务详情</h5>
                    </div>
                    <div class="modal-body" style="padding: 15px 25px 20px;">
                        <div class="profile-inner-card" style="box-shadow: none; margin-bottom: 20px; background: #f8f9fc; border-radius: 8px; padding: 15px;">
                            <div class="profile-inner-card-header">
                                <div class="profile-inner-card-icon">
                                    <i class="bi bi-info-circle"></i>
                                </div>
                                <h5 class="profile-inner-card-title">基本信息</h5>
                            </div>
                            <div class="profile-inner-card-content" id="taskBasicInfo">
                                <!-- 基本信息内容将通过JS动态添加 -->
                            </div>
                        </div>
                        
                        <div class="profile-inner-card" style="box-shadow: none; margin-bottom: 0; background: #f8f9fc; border-radius: 8px; padding: 15px;">
                            <div class="profile-inner-card-header">
                                <div class="profile-inner-card-icon">
                                    <i class="bi bi-gear"></i>
                                </div>
                                <h5 class="profile-inner-card-title">内容要求</h5>
                            </div>
                            <div class="profile-inner-card-content" id="taskRequirements">
                                <!-- 内容要求内容将通过JS动态添加 -->
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer" style="border-top: none; justify-content: center; padding: 0 0 25px 0;">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" style="min-width: 120px; border-radius: 6px;">关闭</button>
                    </div>
                </div>
            </div>
        </div>`;

        // 将模态框添加到body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * 添加自定义样式到head
     */
    addModalStyles() {
        const styleId = 'taskDetailModalStyles';
        
        // 检查样式是否已存在
        if (document.getElementById(styleId)) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = styleId;
        styleElement.textContent = `
            .modal-open .modal {
                display: flex !important;
                align-items: center;
                justify-content: center;
            }
            .modal-backdrop {
                opacity: 0.6;
            }
            #${this.modalId} .modal-dialog {
                transform: none;
                transition: transform 0.3s ease-out;
                max-width: 1500px;
            }
            #${this.modalId}.show .modal-dialog {
                transform: translateY(0);
                transition: transform 0.3s ease-out;
            }
            @media (max-width: 1500px) {
                #${this.modalId} .modal-dialog {
                    max-width: 100%;
                    margin: 1rem auto;
                }
            }
            @media (max-width: 1500px) {
                #${this.modalId} .modal-dialog {
                    max-width: 100%;
                    margin: 0.5rem auto;
                }
            }
        `;
        
        document.head.appendChild(styleElement);
    }

    /**
     * 注册全局事件监听器
     */
    registerEvents() {
        // 使用事件委托监听所有查看详情按钮的点击事件
        document.addEventListener('click', (event) => {
            const viewButton = event.target.closest('.request-card-view-btn');
            if (viewButton) {
                event.preventDefault();
                const taskId = viewButton.dataset.taskId || 
                              viewButton.closest('.request-card').querySelector('[data-task-id]')?.dataset.taskId;
                
                if (taskId) {
                    this.loadTaskDetails(taskId);
                } else {
                    console.error('未找到任务ID');
                }
            }
        });
    }

    /**
     * 加载任务详情
     * @param {string} taskId - 任务ID
     */
    loadTaskDetails(taskId) {
        // 显示加载状态
        this.showLoading();
        
        // 发送请求获取任务详情
        fetch(`/api/task_details/${taskId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应不正常');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    this.renderTaskDetails(data.task);
                } else {
                    this.showError(data.message || '获取任务详情失败');
                }
            })
            .catch(error => {
                console.error('获取任务详情出错:', error);
                this.showError('获取任务详情时发生错误，请稍后再试');
            });
    }

    /**
     * 显示加载状态
     */
    showLoading() {
        const basicInfoEl = document.getElementById('taskBasicInfo');
        const requirementsEl = document.getElementById('taskRequirements');
        
        if (basicInfoEl) basicInfoEl.innerHTML = '<div class="text-center py-3"><i class="bi bi-hourglass-split me-2"></i>加载中...</div>';
        if (requirementsEl) requirementsEl.innerHTML = '';
        
        // 显示模态框
        const modalEl = document.getElementById(this.modalId);
        
        // 先销毁可能存在的实例
        try {
            const existingModal = bootstrap.Modal.getInstance(modalEl);
            if (existingModal) {
                existingModal.dispose();
            }
        } catch (e) {
            console.log('无现有模态框实例');
        }
        
        // 创建新实例并显示
        const bsModal = new bootstrap.Modal(modalEl, {
            backdrop: 'static',
            keyboard: false,
            focus: true
        });
        bsModal.show();
        
        // 手动添加居中类
        modalEl.style.display = 'flex';
        modalEl.style.alignItems = 'center';
        modalEl.style.justifyContent = 'center';
    }

    /**
     * 显示错误信息
     * @param {string} message - 错误信息
     */
    showError(message) {
        const basicInfoEl = document.getElementById('taskBasicInfo');
        if (basicInfoEl) {
            basicInfoEl.innerHTML = `
                <div class="alert alert-danger" role="alert" style="margin-bottom: 0;">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>${message}
                </div>
            `;
        }
    }

    /**
     * 渲染任务详情
     * @param {Object} task - 任务详情数据
     */
    renderTaskDetails(task) {
        // 渲染基本信息
        const basicInfoEl = document.getElementById('taskBasicInfo');
        if (basicInfoEl) {
            basicInfoEl.innerHTML = `
                <div class="mb-3">
                    <div class="profile-info-item">
                        <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">任务标题</span>
                        <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.title || '暂无'}</span>
                    </div>
                </div>
                <div class="mb-3">
                    <div class="profile-info-item">
                        <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">任务描述</span>
                        <p class="mt-1" style="margin-bottom: 0;">${task.description || '暂无描述'}</p>
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">预算金额</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">¥${task.budget || '0'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">截止日期</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.deadline || '暂无'}</span>
                        </div>
                    </div>
                </div>
                <div class="row mb-0">
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">创建时间</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.created_at || '暂无'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">当前状态</span>
                            <span class="profile-info-value">${this.getStatusText(task.status)}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 渲染内容要求
        const requirementsEl = document.getElementById('taskRequirements');
        if (requirementsEl) {
            requirementsEl.innerHTML = `
                <div class="row mb-3">
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">目标受众</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.target_audience || '未指定'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">平台要求</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.platform_requirements || '未指定'}</span>
                        </div>
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">内容格式</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.content_format || '未指定'}</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="profile-info-item">
                            <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">内容风格</span>
                            <span class="profile-info-value" style="color: #343a40; font-size: 16px; font-weight: 600;">${task.content_style || '未指定'}</span>
                        </div>
                    </div>
                </div>
                <div class="mb-0">
                    <div class="profile-info-item">
                        <span class="profile-info-label" style="color: #6c757d; font-size: 14px; display: block; margin-bottom: 4px;">详细要求</span>
                        <p class="mt-1" style="margin-bottom: 0;">${task.requirements || '暂无详细要求'}</p>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 获取状态文本
     * @param {string} status - 状态代码
     * @returns {string} 状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'published': '<span class="badge bg-info">已发布</span>',
            'in_progress': '<span class="badge bg-primary">进行中</span>',
            'completed': '<span class="badge bg-success">已完成</span>',
            'cancelled': '<span class="badge bg-danger">已取消</span>'
        };
        
        return statusMap[status] || `<span class="badge bg-secondary">${status || '未知'}</span>`;
    }
}

// 创建任务详情模态框实例
document.addEventListener('DOMContentLoaded', function() {
    window.taskDetailModal = new TaskDetailModal();
}); 