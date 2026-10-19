/**
 * 通用模态框组件，支持动态加载内容、表单提交等功能
 */
class ModalManager {
    constructor() {
        this.activeModal = null;
        this.modalOverlay = null;
        this.eventHandlers = {};
        this.init();
    }

    init() {
        // 检查是否已存在模态框容器
        let existingOverlay = document.querySelector('.modal-overlay');
        if (existingOverlay) {
            this.modalOverlay = existingOverlay;
        } else {
            // 创建模态框遮罩层
            this.modalOverlay = document.createElement('div');
            this.modalOverlay.className = 'modal-overlay';
            document.body.appendChild(this.modalOverlay);
        }

        // 点击遮罩层关闭模态框，但不关闭模态框内容区域
        this.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.modalOverlay) {
                this.close();
            }
        });

        // 添加键盘事件监听，ESC 键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
    }

    /**
     * 创建一个新的模态框
     * @param {Object} options - 模态框配置项
     * @param {string} options.title - 模态框标题
     * @param {string} options.content - 模态框内容 HTML
     * @param {string} options.size - 模态框大小 (sm, md, lg, xl)
     * @param {string} options.theme - 模态框主题 (默认, danger, success, warning, info)
     * @param {Function} options.onOpen - 模态框打开时回调
     * @param {Function} options.onClose - 模态框关闭时回调
     * @param {Function} options.onSubmit - 表单提交时回调
     * @returns {HTMLElement} - 模态框 DOM 元素
     */
    create(options = {}) {
        const { 
            title = '提示', 
            content = '', 
            size = 'md', 
            theme = '',
            onOpen = null,
            onClose = null,
            onSubmit = null
        } = options;

        // 创建模态框容器
        const modalContainer = document.createElement('div');
        modalContainer.className = `modal-container ${size ? `modal-${size}` : ''} ${theme ? `modal-${theme}` : ''}`;

        // 创建模态框头部
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header';
        
        const modalTitle = document.createElement('h3');
        modalTitle.className = 'modal-title';
        modalTitle.textContent = title;
        
        const closeButton = document.createElement('button');
        closeButton.className = 'modal-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', () => this.close());
        
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        modalContainer.appendChild(modalHeader);

        // 创建模态框主体
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body';
        
        if (typeof content === 'string') {
            modalBody.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            modalBody.appendChild(content);
        }
        
        modalContainer.appendChild(modalBody);

        // 保存当前模态框
        this.activeModal = modalContainer;
        
        // 保存回调函数
        this.eventHandlers = {
            onOpen,
            onClose,
            onSubmit
        };

        // 处理模态框中的表单提交
        const forms = modalContainer.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (typeof this.eventHandlers.onSubmit === 'function') {
                    this.eventHandlers.onSubmit(e, form);
                }
            });
        });

        return modalContainer;
    }

    /**
     * 打开模态框
     * @param {HTMLElement|Object} modal - 模态框元素或配置项
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    open(modal) {
        // 如果传入的是配置项，则创建新的模态框
        if (typeof modal === 'object' && !(modal instanceof HTMLElement)) {
            modal = this.create(modal);
        }

        // 如果已经有打开的模态框，则先关闭
        if (this.isOpen()) {
            this.close();
        }

        // 保存当前打开的模态框
        this.activeModal = modal;
        
        // 将模态框添加到遮罩层
        this.modalOverlay.appendChild(modal);
        
        // 显示模态框
        setTimeout(() => {
            this.modalOverlay.classList.add('active');
        }, 10);

        // 触发打开回调
        if (typeof this.eventHandlers.onOpen === 'function') {
            this.eventHandlers.onOpen();
        }

        return this;
    }

    /**
     * 关闭当前模态框
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    close() {
        if (!this.isOpen()) return this;

        // 隐藏模态框
        this.modalOverlay.classList.remove('active');
        
        // 触发关闭回调
        if (typeof this.eventHandlers.onClose === 'function') {
            this.eventHandlers.onClose();
        }

        // 移除模态框
        setTimeout(() => {
            if (this.activeModal && this.activeModal.parentNode === this.modalOverlay) {
                this.modalOverlay.removeChild(this.activeModal);
            }
            this.activeModal = null;
        }, 300);

        return this;
    }

    /**
     * 更新模态框内容
     * @param {string|HTMLElement} content - 新的内容
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    updateContent(content) {
        if (!this.isOpen()) return this;

        const modalBody = this.activeModal.querySelector('.modal-body');
        if (!modalBody) return this;

        if (typeof content === 'string') {
            modalBody.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            modalBody.innerHTML = '';
            modalBody.appendChild(content);
        }

        return this;
    }

    /**
     * 更新模态框标题
     * @param {string} title - 新的标题
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    updateTitle(title) {
        if (!this.isOpen()) return this;

        const modalTitle = this.activeModal.querySelector('.modal-title');
        if (modalTitle) {
            modalTitle.textContent = title;
        }

        return this;
    }

    /**
     * 添加底部按钮区域
     * @param {Array} buttons - 按钮配置数组
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    addFooter(buttons = []) {
        if (!this.isOpen()) return this;

        // 移除现有的底部区域
        let modalFooter = this.activeModal.querySelector('.modal-footer');
        if (modalFooter) {
            modalFooter.remove();
        }

        // 没有按钮则不添加底部区域
        if (!buttons || buttons.length === 0) return this;

        // 创建新的底部区域
        modalFooter = document.createElement('div');
        modalFooter.className = 'modal-footer';

        // 添加按钮
        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.type = btn.type || 'button';
            button.className = `modal-btn ${btn.className || 'modal-btn-secondary'}`;
            button.textContent = btn.text || '按钮';
            
            if (btn.id) {
                button.id = btn.id;
            }
            
            if (typeof btn.onClick === 'function') {
                button.addEventListener('click', (e) => btn.onClick(e, this));
            }
            
            modalFooter.appendChild(button);
        });

        this.activeModal.appendChild(modalFooter);
        return this;
    }

    /**
     * 显示加载状态
     * @param {string} message - 加载提示信息
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    showLoading(message = '加载中...') {
        if (!this.isOpen()) return this;

        const loadingContent = `
            <div class="modal-loading">
                <div class="modal-spinner"></div>
                <p style="margin-left: 15px;">${message}</p>
            </div>
        `;
        
        this.updateContent(loadingContent);
        return this;
    }

    /**
     * 显示成功消息
     * @param {string} message - 成功提示信息
     * @param {Function} callback - 关闭后的回调函数
     * @param {number} autoClose - 自动关闭时间（毫秒），0 表示不自动关闭
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    showSuccess(message, callback = null, autoClose = 2000) {
        this.showMessage(message, 'success', callback, autoClose);
        return this;
    }

    /**
     * 显示错误消息
     * @param {string} message - 错误提示信息
     * @param {Function} callback - 关闭后的回调函数
     * @param {number} autoClose - 自动关闭时间（毫秒），0 表示不自动关闭
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    showError(message, callback = null, autoClose = 0) {
        this.showMessage(message, 'error', callback, autoClose);
        return this;
    }

    /**
     * 显示消息
     * @param {string} message - 提示信息
     * @param {string} type - 消息类型 (success, error, warning, info)
     * @param {Function} callback - 关闭后的回调函数
     * @param {number} autoClose - 自动关闭时间（毫秒），0 表示不自动关闭
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    showMessage(message, type = 'info', callback = null, autoClose = 0) {
        const messageContent = `
            <div class="modal-message modal-message-${type}">
                ${message}
            </div>
        `;
        
        if (!this.isOpen()) {
            this.open({
                title: type.charAt(0).toUpperCase() + type.slice(1),
                content: messageContent,
                size: 'sm',
                theme: type,
                onClose: callback
            });
        } else {
            this.updateContent(messageContent);
            this.eventHandlers.onClose = callback;
        }
        
        if (autoClose > 0) {
            setTimeout(() => this.close(), autoClose);
        }
        
        return this;
    }

    /**
     * 确认对话框
     * @param {Object} options - 配置项
     * @param {string} options.title - 标题
     * @param {string} options.content - 内容
     * @param {string} options.confirmText - 确认按钮文本
     * @param {string} options.cancelText - 取消按钮文本
     * @param {Function} options.onConfirm - 确认回调
     * @param {Function} options.onCancel - 取消回调
     * @returns {ModalManager} - 当前实例，用于链式调用
     */
    confirm(options = {}) {
        const {
            title = '确认',
            content = '确定要执行此操作吗？',
            confirmText = '确定',
            cancelText = '取消',
            onConfirm = null,
            onCancel = null
        } = options;
        
        this.open({
            title,
            content,
            size: 'sm'
        });
        
        this.addFooter([
            {
                text: cancelText,
                className: 'modal-btn-secondary',
                onClick: (e, modal) => {
                    if (typeof onCancel === 'function') {
                        onCancel();
                    }
                    modal.close();
                }
            },
            {
                text: confirmText,
                className: 'modal-btn-primary',
                onClick: (e, modal) => {
                    if (typeof onConfirm === 'function') {
                        onConfirm();
                    }
                    modal.close();
                }
            }
        ]);
        
        return this;
    }

    /**
     * 检查模态框是否打开
     * @returns {boolean} - 是否打开
     */
    isOpen() {
        return this.activeModal !== null && this.modalOverlay.contains(this.activeModal);
    }

    /**
     * 获取当前活动的模态框元素
     * @returns {HTMLElement|null} - 模态框元素
     */
    getActiveModal() {
        return this.activeModal;
    }

    /**
     * 获取模态框内容区域
     * @returns {HTMLElement|null} - 内容区域元素
     */
    getModalBody() {
        if (!this.isOpen()) return null;
        return this.activeModal.querySelector('.modal-body');
    }
}

// 创建模态框管理器实例
const modalManager = new ModalManager();
window.modalManager = modalManager;

// 创建邀请合作模态框组件
class InvitationModalManager {
    constructor() {
        this.modal = window.modalManager; // 使用window.modalManager而不是modalManager
        this.selectedTaskId = null;
    }

    /**
     * 打开邀请合作模态框
     * @param {number} collaboratorId - 合作者ID
     * @param {string} collaboratorName - 合作者名称
     */
    open(collaboratorId, collaboratorName) {
        this.collaboratorId = collaboratorId;
        this.collaboratorName = collaboratorName;
        
        // 显示加载状态
        this.modal.open({
            title: `邀请 ${collaboratorName} 合作`,
            content: '<div class="modal-loading"><div class="modal-spinner"></div><p style="margin-left: 15px;">加载广告任务...</p></div>',
            size: 'md'
        });
        
        // 加载广告任务列表
        fetch(`/advertiser/api/tasks/published`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取任务列表失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success' && data.tasks && data.tasks.length > 0) {
                    this.renderTaskList(data.tasks);
                } else {
                    this.renderNoTasks();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.modal.showError('获取任务列表失败，请稍后再试。');
            });
    }
    
    /**
     * 渲染任务列表
     * @param {Array} tasks - 任务列表
     */
    renderTaskList(tasks) {
        // 使用当前时间戳生成唯一ID前缀
        const uniquePrefix = `inv_${Date.now()}`;
        const invitationMessageId = `${uniquePrefix}_message`;
        const sendBtnId = `${uniquePrefix}_send_btn`;
        
        let content = `
            <div class="modal-form-group">
                <p>请选择要邀请合作的广告任务：</p>
                <div class="modal-task-list">
        `;
        
        tasks.forEach(task => {
            content += `
                <div class="modal-task-item" data-id="${task.id}">
                    <div class="modal-task-title">${task.title}</div>
                    <div class="modal-task-budget">预算: ¥${task.budget}</div>
                    <div class="modal-task-deadline">截止日期: ${task.deadline || '未设置'}</div>
                    <div class="modal-task-description">${task.description.substr(0, 100)}${task.description.length > 100 ? '...' : ''}</div>
                </div>
            `;
        });
        
        content += `
                </div>
            </div>
            <div class="modal-form-group">
                <label for="${invitationMessageId}" class="modal-form-label">邀请说明：</label>
                <div class="modal-quicktext-container">
                    <div class="modal-quicktext-title">快捷语句：</div>
                    <div class="modal-quicktext-options">
                        <div class="modal-quicktext-option" data-text="您好，我看到您的内容非常优质，希望能与您建立长期合作关系。">长期合作</div>
                        <div class="modal-quicktext-option" data-text="您的粉丝画像与我们的产品目标用户非常匹配，诚邀您参与我们的推广活动。">精准用户</div>
                        <div class="modal-quicktext-option" data-text="我们的产品已有许多好评，相信与您合作会带来双赢的效果。">双赢合作</div>
                        <div class="modal-quicktext-option" data-text="我们提供具有竞争力的报酬，期待与您一起创造优质内容。">优质内容</div>
                        <div class="modal-quicktext-option" data-text="看过您之前的作品，非常欣赏您的创作风格，希望能合作推广我们的产品。">欣赏风格</div>
                    </div>
                </div>
                <textarea id="${invitationMessageId}" class="modal-form-text invitation-message" placeholder="请输入邀请说明，告诉合作者为什么选择他/她..."></textarea>
            </div>
        `;
        
        // 更新模态框内容
        this.modal.updateContent(content);
        
        // 保存邀请消息输入框ID，用于后续获取值
        this.invitationMessageId = invitationMessageId;
        
        // 添加底部按钮
        this.modal.addFooter([
            {
                text: '取消',
                className: 'modal-btn-secondary',
                onClick: (e, modal) => {
                    modal.close();
                }
            },
            {
                text: '发送邀请',
                className: 'modal-btn-primary',
                id: sendBtnId,
                onClick: (e, modal) => {
                    this.sendInvitation();
                }
            }
        ]);
        
        // 绑定任务选择事件
        const taskItems = document.querySelectorAll('.modal-task-item');
        taskItems.forEach(item => {
            item.addEventListener('click', () => {
                // 移除所有选中状态
                taskItems.forEach(task => task.classList.remove('selected'));
                // 添加选中状态
                item.classList.add('selected');
                // 保存选中的任务ID
                this.selectedTaskId = item.getAttribute('data-id');
                
                // 启用发送按钮
                document.getElementById(sendBtnId).disabled = false;
            });
        });
        
        // 绑定快捷语句点击事件
        const quickTextOptions = document.querySelectorAll('.modal-quicktext-option');
        const messageTextarea = document.getElementById(invitationMessageId);
        
        quickTextOptions.forEach(option => {
            option.addEventListener('click', () => {
                const text = option.getAttribute('data-text');
                
                // 如果文本域已有内容，则在末尾添加换行后再添加快捷语句
                if (messageTextarea.value.trim()) {
                    messageTextarea.value = messageTextarea.value.trim() + '\n\n' + text;
                } else {
                    messageTextarea.value = text;
                }
                
                // 聚焦文本域，使用户可以继续编辑
                messageTextarea.focus();
                
                // 为被点击的快捷语句添加动画效果
                option.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    option.style.transform = '';
                }, 200);
            });
        });
        
        // 默认禁用发送按钮
        document.getElementById(sendBtnId).disabled = true;
    }
    
    /**
     * 渲染无任务提示
     */
    renderNoTasks() {
        const content = `
            <div class="modal-message modal-message-warning">
                您当前没有已发布的广告任务。请先创建并发布广告任务，然后再邀请合作者。
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <a href="/advertiser/ad_tasks/new" class="modal-btn modal-btn-primary">创建广告任务</a>
            </div>
        `;
        
        this.modal.updateContent(content);
        
        // 添加底部按钮
        this.modal.addFooter([
            {
                text: '关闭',
                className: 'modal-btn-secondary',
                onClick: (e, modal) => {
                    modal.close();
                }
            }
        ]);
    }
    
    /**
     * 发送邀请
     */
    sendInvitation() {
        // 检查是否选择了任务
        if (!this.selectedTaskId) {
            this.modal.showError('请选择一个广告任务');
            return;
        }
        
        // 获取邀请内容
        const invitationMessage = document.getElementById(this.invitationMessageId).value.trim();
        if (!invitationMessage) {
            this.modal.showError('请输入邀请说明');
            return;
        }
        
        // 显示加载状态
        this.modal.showLoading('正在发送邀请...');

        // 准备请求数据
        const requestData = {
            collaborator_id: parseInt(this.collaboratorId),
            ad_task_id: parseInt(this.selectedTaskId),
            invitation_content: invitationMessage
        };
        
        console.log('准备发送邀请请求:', requestData);
        
        // 设置请求超时
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15秒超时
        
        // 发送请求
        fetch('/advertiser/api/send_invitation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestData),
            signal: controller.signal
        })
        .then(response => {
            console.log('邀请请求响应状态:', response.status);
            clearTimeout(timeoutId); // 清除超时
            
            // 检查响应状态
            if (!response.ok) {
                if (response.status === 500) {
                    console.error('服务器内部错误，状态码:', response.status);
                    throw new Error('服务器内部错误，请联系管理员');
                }
                return response.json().then(errorData => {
                    throw new Error(errorData.message || '发送邀请失败，请稍后再试');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('邀请请求成功:', data);
            if (data.status === 'success') {
                this.modal.showSuccess('邀请已成功发送', () => {
                    // 刷新页面或更新UI
                    window.location.reload();
                }, 1500); // 显示1.5秒后自动刷新
            } else {
                this.modal.showError(data.message || '发送邀请失败，请稍后再试');
            }
        })
        .catch(error => {
            console.error('邀请请求错误:', error);
            clearTimeout(timeoutId); // 确保超时被清除
            
            if (error.name === 'AbortError') {
                this.modal.showError('请求超时，请检查网络连接后重试');
            } else if (error.name === 'SyntaxError') {
                // JSON解析错误，说明返回的不是JSON格式
                console.error('响应不是有效的JSON格式，可能是服务器返回了HTML错误页面');
                this.modal.showError('服务器响应格式错误，请联系管理员');
            } else {
                this.modal.showError(error.message || '发送邀请失败，请稍后再试');
            }
        });
    }
}

// 创建邀请模态框实例
window.invitationModal = new InvitationModalManager(); 