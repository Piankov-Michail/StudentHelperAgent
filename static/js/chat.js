window.chat = {
  escapeHtml: (text) => { const d = document.createElement('div'); d.textContent = text; return d.innerHTML; },
  formatTime: (dateStr) => new Date(dateStr).toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'}),
  showToast: (message) => {
    const toast = document.getElementById('toast');
    document.getElementById('toast-message').textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
  },
  getChatState: (chatId) => {
    if (!window.state.chatStates[chatId]) window.state.chatStates[chatId] = { input: '', files: [], loading: false };
    return window.state.chatStates[chatId];
  },
  saveChatState: (chatId) => {
    if (!chatId) return;
    const s = window.chat.getChatState(chatId);
    s.input = document.getElementById('text-input').value;
    s.files = [...window.state.selectedFiles];
  },
  updateChatHeader: (state) => {
    const dot = document.getElementById('chat-status-dot');
    const sub = document.getElementById('chat-subtitle');
    if (state.loading) {
      dot.classList.remove('bg-green-500'); dot.classList.add('bg-yellow-500', 'animate-pulse');
      sub.textContent = 'Обработка...';
    } else {
      dot.classList.add('bg-green-500'); dot.classList.remove('bg-yellow-500', 'animate-pulse');
      sub.textContent = `${document.querySelectorAll('.message-wrapper').length} сообщений`;
    }
  },
  renderMessages: (messages) => {
    const container = document.getElementById('chat');
    container.innerHTML = '';
    if (messages.length === 0) {
      container.innerHTML = `<div class="flex items-start gap-4 max-w-4xl mx-auto animate-fadeIn"><div class="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30"><i class="fas fa-robot text-white"></i></div><div class="flex-1"><div class="message-bubble assistant"><p class="text-gray-200 leading-relaxed">Привет! 👋<br><br>Прикрепите видео или аудио лекции, и я создам подробный конспект.</p></div></div></div>`;
      return;
    }
    messages.forEach(msg => window.chat.addMessage(msg.content, msg.role, msg.file_path, msg.created_at, false, msg.id));
  },
  
  addMessage: (text, role, filePath = null, timestamp = null, scroll = true, messageId = null) => {
      const wrapper = document.createElement('div');
      wrapper.className = `message-wrapper flex items-start gap-4 max-w-4xl mx-auto ${role.toLowerCase() === 'user' ? 'user ml-auto' : ''}`;
      if (messageId) wrapper.dataset.messageId = messageId;

      const isUser = role.toLowerCase() === 'user';
      const avatar = isUser 
          ? `<div class="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30"><span class="text-white font-bold text-sm">${window.state.currentUser?.username?.[0]?.toUpperCase() || 'U'}</span></div>` 
          : `<div class="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30"><i class="fas fa-robot text-white"></i></div>`;
      
      const fileHtml = filePath ? `<div class="file-attachment mb-3">${window.file.getFileIcon(filePath)}<span class="text-sm text-gray-200">${filePath.split('/').pop()}</span></div>` : '';
      const contentHtml = isUser ? window.chat.escapeHtml(text).replace(/\n/g, '<br>') : marked.parse(text);
      const time = timestamp ? window.chat.formatTime(timestamp) : new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});

      // Кнопки действий (чистый HTML без лишних Tailwind-утилит, чтобы не конфликтовать с CSS)
      const actionButtons = `<div class="message-actions">
          <button class="btn-icon copy" onclick="window.chat.copyMessage(this)" title="Копировать"><i class="fas fa-copy"></i></button>
          ${isUser ? `
          <button class="btn-icon resend" onclick="window.chat.resendMessage(this)" title="Повторить"><i class="fas fa-redo"></i></button>
          <button class="btn-icon delete" onclick="window.chat.deleteMessage(this)" title="Удалить"><i class="fas fa-trash"></i></button>
          ` : ''}
      </div>`;

      wrapper.innerHTML = `
          ${avatar}
          <div class="flex-1 min-w-0">
              <div class="message-bubble ${role.toLowerCase()}">${fileHtml}<div class="prose prose-invert max-w-none">${contentHtml}</div></div>
              <div class="flex items-center gap-2 mt-2.5 text-xs text-gray-500 ${isUser ? 'justify-end mr-2' : 'ml-2'}">
                  <span>${isUser ? 'Вы' : 'StudentHelper'}</span><span>•</span><span>${time}</span>
              </div>
              ${actionButtons}
          </div>`;

      document.getElementById('chat').appendChild(wrapper);
      
      // Подсветка кода
      wrapper.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
      if (scroll) document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
  },
  addLoadingMessage: (agentType = 'transcript') => {
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper flex items-start gap-4 max-w-4xl mx-auto'; wrapper.id = 'loading-message';
    const names = { transcript: '🎬 Транскрибация', assistant: '💬 Помощник', rag: '🧠 RAG' };
    const steps = { transcript: ['📁 Загрузка файла...', '🔊 Транскрибация...', '📝 Анализ...', '✨ Конспект готов!'], assistant: ['💭 Обработка...', '✨ Ответ...'], rag: ['🔍 Поиск...', '🧩 Синтез...', '✨ Ответ...'] };
    const list = steps[agentType] || steps['assistant'];
    wrapper.innerHTML = `<div class="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30"><i class="fas fa-spinner text-white animate-spin"></i></div><div class="flex-1 min-w-0"><div class="message-bubble assistant"><div class="flex items-center gap-2 mb-3"><span class="text-blue-400 font-semibold">${names[agentType]}</span><span class="text-xs text-gray-500">в работе</span></div><div class="space-y-2" id="processing-steps">${list.map((s, i) => `<div class="flex items-center gap-2 text-sm ${i===0?'text-blue-400':'text-gray-500'}" data-step="${i}"><div class="w-4 h-4 rounded-full ${i===0?'bg-blue-500 animate-pulse':'bg-gray-700'}"></div><span>${s}</span></div>`).join('')}</div></div></div>`;
    document.getElementById('chat').appendChild(wrapper);
    document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
    
    return wrapper;
  },
  updateProcessingStep: (stepIndex, message = null, status = 'processing') => {
    const steps = document.querySelectorAll('#processing-steps [data-step]');
    steps.forEach((step, i) => {
      const dot = step.querySelector('div'); const text = step.querySelector('span');
      if (i < stepIndex) { dot.className='w-4 h-4 rounded-full bg-green-500'; text.className='text-green-400 line-through'; }
      else if (i === stepIndex) { dot.className='w-4 h-4 rounded-full bg-blue-500 animate-pulse'; text.className='text-blue-400'; if(message) text.textContent=message; }
      else { dot.className='w-4 h-4 rounded-full bg-gray-700'; text.className='text-gray-500'; }
    });
    if (status === 'completed' || status === 'error') setTimeout(() => { const el = document.getElementById('loading-message'); if(el) el.remove(); }, 500);
  },
  copyMessage: (btn) => { navigator.clipboard.writeText(btn.closest('.message-wrapper').querySelector('.prose').innerText); window.chat.showToast('Скопировано'); },
  resendMessage: async (btn) => {
    const messageWrapper = btn.closest('.message-wrapper');
    const messageId = messageWrapper.dataset.messageId;
    const chatId = window.state.currentChatId;
    
    console.log('🔄 Resend message:', { messageId, chatId });
    
    if (!messageId || !chatId) {
      window.chat.showToast('❌ Невозможно повторить');
      return;
    }
    
    // Stop any ongoing generation
    if (window.state.isGenerating) {
      window.app.stopGeneration();
    }
    
    try {
      // Call API to retry - server will delete messages after this one and regenerate
      const fd = new FormData();
      fd.append('agent_type', window.state.currentAgentType);
      
      const res = await fetch(`/chats/${chatId}/retry/${messageId}`, {
        method: 'POST',
        body: fd,
        headers: { 'Authorization': `Bearer ${window.state.token}` }
      });
      
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Ошибка повтора');
      }
      
      const data = await res.json();
      console.log('✅ Retry response:', data);
      
      // Update user message ID with new ID from server
      if (data.user_message_id) {
        messageWrapper.dataset.messageId = data.user_message_id;
      }
      
      // Remove all messages from DOM after this wrapper
      let nextSibling = messageWrapper.nextElementSibling;
      while (nextSibling) {
        const toRemove = nextSibling;
        nextSibling = nextSibling.nextElementSibling;
        if (toRemove.classList.contains('message-wrapper')) {
          toRemove.remove();
        }
      }
      
      // Add the new assistant response with its ID
      window.chat.addMessage(data.answer, 'assistant', null, null, true, data.assistant_message_id);
      window.chat.loadChats();
      window.chat.showToast('✅ Запрос повторён');
      
    } catch (err) {
      console.error('❌ Retry error:', err);
      window.chat.showToast('❌ Ошибка: ' + err.message);
    }
  },
  deleteMessage: async (btn) => {
    if (!confirm('Удалить это сообщение и все последующие?')) return;
    const messageWrapper = btn.closest('.message-wrapper');
    const messageId = messageWrapper.dataset.messageId;
    const chatId = window.state.currentChatId;
    
    console.log('🗑️ Delete message:', { messageId, chatId });
    
    if (!messageId || !chatId) {
      window.chat.showToast('❌ Невозможно удалить');
      return;
    }
    
    try {
      // Call API to delete this message and all after it
      await apiRequest(`/chats/${chatId}/messages/${messageId}`, 'DELETE');
      
      // Remove from DOM
      let nextSibling = messageWrapper.nextElementSibling;
      while (nextSibling) {
        const toRemove = nextSibling;
        nextSibling = nextSibling.nextElementSibling;
        if (toRemove.classList.contains('message-wrapper')) {
          toRemove.remove();
        }
      }
      messageWrapper.remove();
      
      window.chat.showToast('✅ Сообщения удалены');
    } catch (err) {
      console.error('❌ Delete error:', err);
      window.chat.showToast('❌ Ошибка: ' + err.message);
    }
  },
  connectWebSocket: (chatId) => {
    if (window.ws) window.ws.close();
    const wsUrl = `ws://${window.location.host}/ws/progress/${chatId}?token=${window.state.token}`;
    window.ws = new WebSocket(wsUrl);
    window.ws.onopen = () => { 
      console.log('✅ WS connected');
      window.wsPingInterval = setInterval(() => {
        if (window.ws && window.ws.readyState === WebSocket.OPEN) {
          window.ws.send('ping');
        }
      }, 30000);
    };
    window.ws.onmessage = (e) => { 
      const d = JSON.parse(e.data); 
      console.log('📨 WS message:', d);
      if(d.type==='progress') {
        window.chat.updateProcessingStep(d.step-1, d.message, d.status);
      } else if(d.type==='connected') {
        console.log('✅ WS confirmed:', d.message);
      }
    };
    window.ws.onclose = () => { 
      console.log('❌ WS closed');
      if (window.wsPingInterval) {
        clearInterval(window.wsPingInterval);
        window.wsPingInterval = null;
      }
    };
    window.ws.onerror = (err) => {
      console.error('❌ WS error:', err);
    };
  },
  loadChats: async () => {
    try {
      window.state.chats = await apiRequest('/chats/');
      window.chat.renderChatsList();
      document.getElementById('chat-count').textContent = window.state.chats.length;
      if (window.state.chats.length > 0 && !window.state.currentChatId) window.chat.selectChat(window.state.chats[0].id);
      else if (window.state.chats.length === 0) window.chat.createNewChat();
    } catch (e) { console.error(e); }
  },
  renderChatsList: () => {
    const list = document.getElementById('chats-list');
    if (window.state.chats.length === 0) { list.innerHTML = '<div class="text-center py-12"><p class="text-gray-500 text-sm">Нет чатов</p></div>'; return; }
    list.innerHTML = window.state.chats.map(c => {
      const st = window.chat.getChatState(c.id);
      return `<div class="chat-item group flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition border border-transparent ${c.id===window.state.currentChatId?'active':'hover:bg-white/5'} ${st.loading?'loading':''}" onclick="window.chat.selectChat(${c.id})"><div class="flex items-center gap-3 flex-1 min-w-0"><div class="w-9 h-9 bg-white/5 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-blue-500/20"><i class="fas fa-comment text-gray-400 group-hover:text-blue-400"></i></div><span class="text-sm truncate text-gray-300">${c.title}</span></div><button class="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 p-1.5" onclick="event.stopPropagation();window.chat.deleteChat(${c.id})"><i class="fas fa-trash text-xs"></i></button></div>`;
    }).join('');
  },
  selectChat: async (chatId) => {
    window.state.currentChatId = chatId;
    window.chat.renderChatsList();
    const st = window.chat.getChatState(chatId);
    document.getElementById('text-input').value = st.input || '';
    window.state.selectedFiles = st.files || [];
    window.file.renderFilePreviews();
    window.app.updateSendButton();
    window.chat.updateChatHeader(st);
    try {
      const data = await apiRequest(`/chats/${chatId}`);
      document.getElementById('chat-title').textContent = data.chat.title;
      window.chat.renderMessages(data.messages);
    } catch (e) { console.error(e); }
  },
  createNewChat: async () => {
    try {
      const fd = new FormData(); fd.append('title', 'Новый чат');
      const res = await fetch('/chats/', { method: 'POST', body: fd, headers: { 'Authorization': `Bearer ${window.state.token}` } });
      if (!res.ok) throw new Error('Ошибка создания');
      const nc = await res.json();
      window.state.chats.unshift(nc);
      window.state.chatStates[nc.id] = { input: '', files: [], loading: false };
      window.chat.selectChat(nc.id);
    } catch (e) { console.error(e); }
  },
  deleteChat: async (chatId) => {
    if (!confirm('Удалить чат?')) return;
    try {
      await apiRequest(`/chats/${chatId}`, 'DELETE');
      window.state.chats = window.state.chats.filter(c => c.id !== chatId);
      delete window.state.chatStates[chatId];
      if (window.state.currentChatId === chatId) {
        window.state.currentChatId = null;
        if (window.state.chats.length > 0) window.chat.selectChat(window.state.chats[0].id); else window.chat.createNewChat();
      } else { window.chat.renderChatsList(); document.getElementById('chat-count').textContent = window.state.chats.length; }
    } catch (e) { console.error(e); }
  },
  init: () => {
    document.getElementById('new-chat-btn').onclick = window.chat.createNewChat;
    document.getElementById('delete-chat-btn').onclick = () => { if (window.state.currentChatId) window.chat.deleteChat(window.state.currentChatId); };
    document.getElementById('export-btn').onclick = async () => {
      if (!window.state.currentChatId) return;
      try {
        const data = await apiRequest(`/chats/${window.state.currentChatId}`);
        navigator.clipboard.writeText(data.messages.map(m => `[${m.role.toUpperCase()}]: ${m.content}`).join('\n'));
        window.chat.showToast('Скопировано в буфер');
      } catch (e) { window.chat.showToast('Ошибка экспорта'); }
    };
  }
};
