window.app = {
  updateSendButton: () => {
    const btn = document.getElementById('send-btn');
    const hasContent = document.getElementById('text-input').value.trim() || window.state.selectedFiles.length > 0;
    const isGenerating = window.state.isGenerating;
    
    if (isGenerating) {
      btn.disabled = false;
      btn.classList.remove('bg-[#1a73e8]', 'hover:bg-[#1765cc]');
      btn.classList.add('bg-red-600', 'hover:bg-red-500');
      btn.innerHTML = '<i class="fas fa-stop text-lg"></i>';
    } else {
      btn.disabled = !hasContent;
      btn.classList.remove('bg-red-600', 'hover:bg-red-500');
      btn.classList.add('bg-[#1a73e8]', 'hover:bg-[#1765cc]');
      btn.innerHTML = '<i class="fas fa-arrow-up text-lg"></i>';
    }
  },
  
  stopGeneration: () => {
    if (window.state.abortController) {
      window.state.abortController.abort();
      window.state.abortController = null;
    }
    if (window.ws) { 
      window.ws.close(); 
      window.ws = null; 
    }
    if (window.wsPingInterval) {
      clearInterval(window.wsPingInterval);
      window.wsPingInterval = null;
    }
    
    const loadingMsg = document.getElementById('loading-message');
    if (loadingMsg) loadingMsg.remove();
    
    window.chat.addMessage('⚠️ Генерация остановлена пользователем', 'assistant');
    
    const st = window.chat.getChatState(window.state.currentChatId);
    st.loading = false;
    window.state.isGenerating = false;
    window.chat.renderChatsList();
    window.chat.updateChatHeader(st);
    window.app.updateSendButton();
  },
  
  initResizable: () => {
    const sidebar = document.getElementById('sidebar');
    const handle = document.getElementById('sidebar-resize-handle');
    let isResizing = false, startX, startWidth;
    
    if (handle) {
      handle.addEventListener('mousedown', (e) => { 
        isResizing=true; 
        startX=e.pageX; 
        startWidth=sidebar.offsetWidth; 
        handle.classList.add('active'); 
        document.body.classList.add('resizing'); 
        e.preventDefault(); 
      });
    }
    
    document.addEventListener('mousemove', (e) => { 
      if(!isResizing) return; 
      const d=e.pageX-startX; 
      const newWidth = Math.min(Math.max(startWidth+d,200),500);
      sidebar.style.width=newWidth+'px';
    });
    
    document.addEventListener('mouseup', () => { 
      if(!isResizing) return; 
      isResizing=false; 
      handle?.classList.remove('active'); 
      document.body.classList.remove('resizing'); 
      localStorage.setItem('sidebarWidth', sidebar.style.width); 
    });
    
    const saved = localStorage.getItem('sidebarWidth');
    if(saved && window.innerWidth>=1024) {
      sidebar.style.width=saved;
    }
    
    const inputArea = document.querySelector('.input-area');
    if(inputArea) { inputArea.style.resize='vertical'; inputArea.style.overflowY='auto'; }
  },
  
  init: () => {
    window.auth.init();
    window.file.init();
    window.chat.init();
    window.app.initResizable();

    document.getElementById('welcome-time').textContent = new Date().toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'});

    // Textarea auto-resize & save state
    const ti = document.getElementById('text-input');
    ti.addEventListener('input', function() { this.style.height='auto'; this.style.height=Math.min(this.scrollHeight,160)+'px'; window.chat.saveChatState(window.state.currentChatId); window.app.updateSendButton(); });
    ti.addEventListener('keydown', (e) => { 
      if(e.key==='Enter' && !e.shiftKey) { 
        e.preventDefault(); 
        const btn = document.getElementById('send-btn');
        if(!btn.disabled) btn.click(); 
      } 
    });

    // Send/Stop button click handler
    const sendBtn = document.getElementById('send-btn');
    sendBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      if (window.state.isGenerating) {
        window.app.stopGeneration();
        return;
      }
      
      // Send message
      const text = ti.value.trim();
      if(!text && window.state.selectedFiles.length===0) return;
      
      // Trigger form submit
      document.getElementById('chat-form').dispatchEvent(new Event('submit'));
    });

    // Chat form submit
    document.getElementById('chat-form').onsubmit = async (e) => {
      e.preventDefault();
      const text = ti.value.trim();
      if(!text && window.state.selectedFiles.length===0) return;
      if(!window.state.currentChatId) { await window.chat.createNewChat(); if(!window.state.currentChatId) { window.chat.addMessage('❌ Ошибка создания чата','assistant'); return; } }
      const st = window.chat.getChatState(window.state.currentChatId);
      if(st.loading) return;
      
      // Create abort controller for this request
      window.state.abortController = new AbortController();
      window.state.isGenerating = true;
      st.loading = true; 
      window.chat.renderChatsList(); 
      window.chat.updateChatHeader(st); 
      window.app.updateSendButton();
      
      // Add user message temporarily without ID
      let userMessageElement;
      if(window.state.selectedFiles.length>0) {
        window.state.selectedFiles.forEach(f => window.chat.addMessage(text||`Файл: ${f.name}`, 'user', f.name));
        userMessageElement = document.querySelector('#chat .message-wrapper.user:last-child');
      } else {
        window.chat.addMessage(text, 'user');
        userMessageElement = document.querySelector('#chat .message-wrapper.user:last-child');
      }
      
      const fd = new FormData(); fd.append('text', text||'Анализируй файл'); fd.append('agent_type', window.state.currentAgentType); fd.append('stream', 'true');
      if(window.state.selectedFiles.length>0) fd.append('file', window.state.selectedFiles[0]);
      ti.value=''; ti.style.height='auto'; window.state.selectedFiles=[]; window.file.renderFilePreviews(); window.chat.saveChatState(window.state.currentChatId); window.app.updateSendButton();
      
      // Всегда подключаем WebSocket для получения токенов
      window.chat.connectWebSocket(window.state.currentChatId);
      
      // Для transcript с файлами показываем loading с прогресс-баром
      // После транскрибации loading удалится и создастся пустое сообщение для streaming
      const hasFile = fd.get('file') !== null;
      const isTranscript = window.state.currentAgentType === 'transcript';
      
      if (isTranscript && hasFile) {
        window.chat.addLoadingMessage(window.state.currentAgentType);
      } else {
        // Для assistant или transcript без файлов сразу создаем пустое сообщение для streaming
        window.chat.addMessage('', 'assistant', null, null, false);
      }
      
      try {
        const res = await fetch(`/chats/${window.state.currentChatId}/message`, { 
          method:'POST', 
          body:fd, 
          headers:{ 'Authorization': `Bearer ${window.state.token}` },
          signal: window.state.abortController.signal
        });
        if(!res.ok) { const err=await res.json().catch(()=>({})); throw new Error(err.detail||'Ошибка'); }
        const data = await res.json();
        
        // Update user message with ID from server
        if(userMessageElement && data.user_message_id) {
          userMessageElement.dataset.messageId = data.user_message_id;
        }
        
        // Удаляем loading message если он еще есть
        document.getElementById('loading-message')?.remove();
        
        // Обновляем последнее сообщение ассистента с ID
        const lastAssistant = document.querySelector('#chat .message-wrapper:not(.user):last-child');
        if (lastAssistant && data.assistant_message_id) {
          lastAssistant.dataset.messageId = data.assistant_message_id;
          // Если контент пустой (streaming не сработал), добавляем полный ответ
          const contentDiv = lastAssistant.querySelector('.message-content');
          if (contentDiv && (!lastAssistant.dataset.rawText || !lastAssistant.dataset.rawText.trim())) {
            lastAssistant.dataset.rawText = data.answer;
            contentDiv.innerHTML = marked.parse(data.answer);
            contentDiv.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
          }
        } else if (!lastAssistant || lastAssistant.classList.contains('user')) {
          // Если streaming вообще не создал сообщение, добавляем его
          window.chat.addMessage(data.answer, 'assistant', null, null, true, data.assistant_message_id);
        }
        
        // Закрываем WebSocket только если он был открыт
        if (window.ws) {
          window.ws.close();
          window.ws = null;
        }
        if (window.wsPingInterval) {
          clearInterval(window.wsPingInterval);
          window.wsPingInterval = null;
        }
        
        window.chat.loadChats();
      } catch(err) {
        if (err.name === 'AbortError') {
          // Request was aborted by stop button - handled in stopGeneration()
          return;
        }
        if(window.ws){ window.ws.close(); window.ws=null; }
        if (window.wsPingInterval) { clearInterval(window.wsPingInterval); window.wsPingInterval = null; }
        document.getElementById('loading-message')?.remove(); 
        window.chat.addMessage('❌ Ошибка: '+err.message, 'assistant');
      } finally { 
        st.loading=false; 
        window.state.isGenerating = false;
        window.state.abortController = null;
        window.chat.renderChatsList(); 
        window.chat.updateChatHeader(st); 
        window.app.updateSendButton(); 
      }
    };

    // Agent selector
    const ag = document.getElementById('agent-selector');
    if(ag) {
      ag.onchange = () => { window.state.currentAgentType = ag.value; document.getElementById('agent-description').textContent = {transcript:'🎬 Транскрибация + умный конспект', assistant:'💬 Обычный чат без файлов', rag:'🔮 Граф знаний (в разработке)'}[ag.value]||''; if(window.state.currentChatId) localStorage.setItem(`chat_${window.state.currentChatId}_agent`, ag.value); };
      ag.onchange();
    }

    // Settings modal
    const sm = document.getElementById('settings-modal');
    if(sm) {
      document.getElementById('settings-btn').onclick = () => { sm.classList.remove('hidden'); };
      document.getElementById('close-settings').onclick = () => sm.classList.add('hidden');
      sm.onclick = (e) => { if(e.target===sm) sm.classList.add('hidden'); };
    }

    // Init auth
    window.auth.checkAuth();
  }
};

document.addEventListener('DOMContentLoaded', window.app.init);
