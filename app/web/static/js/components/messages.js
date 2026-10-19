// 消息模块JS - 负责联系人列表切换和聊天功能
document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const contactItems = document.querySelectorAll('.contact-item');
    const chatArea = document.querySelector('.chat-area');
    const emptyChatState = document.querySelector('.empty-state');
    const chatMessages = document.querySelector('.chat-messages');
    const chatHeader = document.querySelector('.chat-header');
    const sendButton = document.querySelector('.send-button');
    const messageInput = document.querySelector('.message-input');
    
    // 当前选中的联系人ID
    let currentContactId = null;
    // 最后加载的消息时间戳，用于新消息检查
    let lastMessageTimestamp = 0;
    // 刷新间隔（毫秒）
    const refreshInterval = 5000;
    // 用于控制定时刷新的变量
    let refreshTimer = null;
    
    // 检测当前用户类型（广告主还是合作者）以使用正确的API路径
    const isAdvertiser = window.location.pathname.includes('/advertiser/');
    const apiPrefix = isAdvertiser ? '/advertiser' : '/collaborator';
    
    // 联系人点击事件
    contactItems.forEach(item => {
        item.addEventListener('click', () => {
            // 移除之前的active状态
            contactItems.forEach(c => c.classList.remove('active'));
            // 添加当前active状态
            item.classList.add('active');
            
            if (emptyChatState) {
                emptyChatState.style.display = 'none';
            }
            
            // 显示聊天区域
            chatArea.style.display = 'flex';
            
            // 获取联系人信息
            const contactId = item.getAttribute('data-id');
            // 从contact-123格式中提取ID数字部分
            const receiverId = contactId.split('-')[1];
            currentContactId = receiverId;
            
            const contactName = item.querySelector('.contact-name').textContent;
            const contactAvatar = item.querySelector('.contact-avatar').src;
            
            // 更新聊天头部
            chatHeader.innerHTML = `
                <img src="${contactAvatar}" alt="${contactName}" class="contact-avatar">
                <div class="contact-info">
                    <div class="contact-name">${contactName}</div>
                    <div class="contact-status">在线</div>
                </div>
            `;
            
            // 清除未读消息标记（如果有）
            const unreadBadge = item.querySelector('.unread-badge');
            if (unreadBadge) {
                unreadBadge.remove();
            }
            
            // 重置最后消息时间戳
            lastMessageTimestamp = 0;
            
            // 从服务器加载聊天记录
            loadChatMessages(receiverId);
            
            // 清除之前的定时器
            if (refreshTimer) {
                clearInterval(refreshTimer);
            }
            
            // 设置定时刷新
            refreshTimer = setInterval(() => {
                if (currentContactId) {
                    checkNewMessages(currentContactId);
                }
            }, refreshInterval);
        });
    });
    
    // 从服务器加载聊天记录
    function loadChatMessages(receiverId) {
        // 清空现有消息
        chatMessages.innerHTML = '';
        
        // 显示加载中状态
        chatMessages.innerHTML = '<div class="text-center p-3"><i class="bi bi-arrow-repeat spinner"></i> 加载消息中...</div>';
        
        // 发起API请求获取消息历史
        fetch(`${apiPrefix}/api/get_messages/${receiverId}`)
            .then(response => response.json())
            .then(data => {
                // 清空加载状态
                chatMessages.innerHTML = '';
                
                if (data.status === 'success') {
                    const messages = data.data;
                    
                    if (messages.length === 0) {
                        // 没有聊天记录，显示提示
                        chatMessages.innerHTML = '<div class="text-center p-3 text-muted">还没有聊天记录，发送消息开始对话吧</div>';
                        return;
                    }
                    
                    // 添加消息到聊天区域
                    messages.forEach(msg => {
                        // 使用is_sent来确定消息的样式类 - 发送的消息显示在右边，接收的消息显示在左边
                        const messageClass = msg.is_sent ? 'sent' : 'received';
                        const messageEl = document.createElement('div');
                        messageEl.className = `message ${messageClass}`;
                        messageEl.innerHTML = `
                            <div class="message-text">${msg.content}</div>
                            <div class="message-time">${msg.time}</div>
                        `;
                        chatMessages.appendChild(messageEl);
                        
                        // 更新最后消息ID
                        if (msg.id > lastMessageTimestamp) {
                            lastMessageTimestamp = msg.id;
                        }
                    });
                    
                    // 滚动到最新消息
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } else {
                    // 显示错误消息
                    chatMessages.innerHTML = `<div class="text-center p-3 text-danger">${data.message || '加载消息失败'}</div>`;
                }
            })
            .catch(error => {
                console.error('获取消息出错:', error);
                chatMessages.innerHTML = '<div class="text-center p-3 text-danger">加载消息失败，请稍后重试</div>';
            });
    }
    
    // 检查新消息
    function checkNewMessages(receiverId) {
        // 发起API请求获取消息历史
        fetch(`${apiPrefix}/api/get_messages/${receiverId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const messages = data.data;
                    let hasNewMessages = false;
                    
                    // 检查是否有新消息
                    messages.forEach(msg => {
                        if (msg.id > lastMessageTimestamp) {
                            hasNewMessages = true;
                            
                            // 创建新消息元素
                            const messageClass = msg.is_sent ? 'sent' : 'received';
                            const messageEl = document.createElement('div');
                            messageEl.className = `message ${messageClass}`;
                            messageEl.innerHTML = `
                                <div class="message-text">${msg.content}</div>
                                <div class="message-time">${msg.time}</div>
                            `;
                            chatMessages.appendChild(messageEl);
                            
                            // 更新最后消息ID
                            lastMessageTimestamp = msg.id;
                        }
                    });
                    
                    // 如果有新消息，滚动到底部
                    if (hasNewMessages) {
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                }
            })
            .catch(error => {
                console.error('检查新消息出错:', error);
            });
    }
    
    // 发送消息功能
    if (sendButton && messageInput) {
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    function sendMessage() {
        const text = messageInput.value.trim();
        if (!text) return;
        
        // 获取当前选中的联系人ID
        if (!currentContactId) {
            alert('请先选择一个联系人');
            return;
        }
        
        // 禁用发送按钮，防止重复发送
        sendButton.disabled = true;
        
        // 发送消息到服务器
        fetch(`${apiPrefix}/api/send_message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                receiver_id: currentContactId,
                content: text
            }),
        })
        .then(response => response.json())
        .then(data => {
            // 重新启用发送按钮
            sendButton.disabled = false;
            
            if (data.status === 'success') {
                // 创建新消息元素 - 发送的消息总是显示在右边
                const messageEl = document.createElement('div');
                messageEl.className = 'message sent';
                
                // 使用服务器返回的时间
                const timeStr = data.data.time;
                
                messageEl.innerHTML = `
                    <div class="message-text">${text}</div>
                    <div class="message-time">${timeStr}</div>
                `;
                
                // 添加到聊天区域
                chatMessages.appendChild(messageEl);
                
                // 更新联系人最后消息
                const activeContact = document.querySelector('.contact-item.active');
                if (activeContact) {
                    const lastMessageEl = activeContact.querySelector('.contact-last-message');
                    if (lastMessageEl) {
                        lastMessageEl.textContent = text;
                    }
                }
                
                // 更新最后消息ID
                if (data.data.id > lastMessageTimestamp) {
                    lastMessageTimestamp = data.data.id;
                }
                
                // 清空输入框
                messageInput.value = '';
                
                // 滚动到底部
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                // 显示错误信息
                alert(data.message || '发送消息失败');
            }
        })
        .catch(error => {
            console.error('发送消息出错:', error);
            sendButton.disabled = false;
            alert('发送消息时发生错误，请稍后重试');
        });
    }
    
    // 如果有联系人，默认选中第一个
    if (contactItems.length > 0) {
        contactItems[0].click();
    }
    
    // 当用户离开页面时清除定时器
    window.addEventListener('beforeunload', () => {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
    });
});
