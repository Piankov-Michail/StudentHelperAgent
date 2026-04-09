window.auth = {
  checkAuth: async () => {
    if (!window.state.token) { auth.showAuth(); return; }
    try {
      window.state.currentUser = await apiRequest('/auth/me');
      document.getElementById('user-display').textContent = window.state.currentUser.username;
      document.getElementById('user-avatar').textContent = window.state.currentUser.username[0].toUpperCase();
      auth.hideAuth();
      window.chat.loadChats();
    } catch (e) { auth.logout(); }
  },
  showAuth: () => {
    document.getElementById('auth-modal').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
  },
  hideAuth: () => {
    document.getElementById('auth-modal').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
  },
  logout: () => {
    window.state.token = null; window.state.currentUser = null; window.state.currentChatId = null;
    localStorage.removeItem('token');
    auth.showAuth();
  },
  init: () => {
    const authSwitch = document.getElementById('auth-switch');
    const authSwitchText = document.getElementById('auth-switch-text');
    const authTitle = document.getElementById('auth-title');
    const authForm = document.getElementById('auth-form');
    const authError = document.getElementById('auth-error');

    authSwitch.onclick = () => {
      window.state.isRegisterMode = !window.state.isRegisterMode;
      authTitle.textContent = window.state.isRegisterMode ? 'Регистрация' : 'Вход';
      authSwitch.textContent = window.state.isRegisterMode ? 'Войти' : 'Зарегистрироваться';
      authSwitchText.textContent = window.state.isRegisterMode ? 'Есть аккаунт?' : 'Нет аккаунта?';
      authError.classList.add('hidden');
    };

    authForm.onsubmit = async (e) => {
      e.preventDefault();
      const username = document.getElementById('auth-username').value.trim();
      const password = document.getElementById('auth-password').value;
      if (!username || !password) {
        authError.textContent = 'Заполните все поля'; authError.classList.remove('hidden'); return;
      }
      try {
        const endpoint = window.state.isRegisterMode ? '/auth/register' : '/auth/login';
        const res = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка');
        if (window.state.isRegisterMode) {
          const loginRes = await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
          const loginData = await loginRes.json();
          window.state.token = loginData.access_token;
        } else { window.state.token = data.access_token; }
        localStorage.setItem('token', window.state.token);
        window.state.currentUser = await apiRequest('/auth/me');
        document.getElementById('user-display').textContent = window.state.currentUser.username;
        document.getElementById('user-avatar').textContent = window.state.currentUser.username[0].toUpperCase();
        auth.hideAuth();
        window.chat.loadChats();
      } catch (err) { authError.textContent = err.message; authError.classList.remove('hidden'); }
    };

    document.getElementById('logout-btn').onclick = auth.logout;
    document.getElementById('menu-btn').onclick = () => {
      document.getElementById('sidebar').classList.toggle('open');
      document.getElementById('sidebar-overlay').classList.toggle('hidden');
    };
    document.getElementById('sidebar-overlay').onclick = () => {
      document.getElementById('sidebar').classList.remove('open');
      document.getElementById('sidebar-overlay').classList.add('hidden');
    };

    document.getElementById('delete-account-btn').onclick = () => document.getElementById('delete-account-modal').classList.remove('hidden');
    document.getElementById('cancel-delete-btn').onclick = () => document.getElementById('delete-account-modal').classList.add('hidden');
    document.getElementById('confirm-delete-btn').onclick = async () => {
      try {
        const res = await fetch('/auth/delete', { method: 'DELETE', headers: { 'Authorization': `Bearer ${window.state.token}` } });
        if (res.ok) { auth.logout(); window.app.showToast('Аккаунт удалён'); }
        else throw new Error('Не удалось удалить аккаунт');
      } catch (err) { window.app.showToast(err.message); }
      finally { document.getElementById('delete-account-modal').classList.add('hidden'); }
    };

    // Settings modal - API tokens with toggle visibility
    const ollamaTokenInput = document.getElementById('ollama-token');
    const groqTokenInput = document.getElementById('groq-token');
    const nvidiaTokenInput = document.getElementById('nvidia-token');
    const toggleOllamaBtn = document.getElementById('toggle-ollama-token');
    const toggleGroqBtn = document.getElementById('toggle-groq-token');
    const toggleNvidiaBtn = document.getElementById('toggle-nvidia-token');
    const saveTokensBtn = document.getElementById('save-tokens-btn');
    const clearTokensBtn = document.getElementById('clear-tokens-btn');
    const tokenStatus = document.getElementById('token-status');

    // Check if all elements exist
    if (!ollamaTokenInput || !groqTokenInput || !nvidiaTokenInput || !toggleOllamaBtn || !toggleGroqBtn || !toggleNvidiaBtn || !saveTokensBtn || !clearTokensBtn || !tokenStatus) {
      console.error('Some token input elements not found');
      return;
    }

    // Load saved tokens from server
    const loadTokens = async () => {
      try {
        const tokens = await apiRequest('/tokens/');
        const ollamaToken = tokens.find(t => t.service === 'ollama');
        const groqToken = tokens.find(t => t.service === 'groq');
        const nvidiaToken = tokens.find(t => t.service === 'nvidia');
        
        if (ollamaToken && ollamaToken.has_value) {
          ollamaTokenInput.placeholder = '••••••••••••••••';
        }
        if (groqToken && groqToken.has_value) {
          groqTokenInput.placeholder = '••••••••••••••••';
        }
        if (nvidiaToken && nvidiaToken.has_value) {
          nvidiaTokenInput.placeholder = '••••••••••••••••';
        }
      } catch (e) {
        console.error('Failed to load tokens:', e);
      }
    };

    // Load tokens when settings modal opens
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
      settingsBtn.addEventListener('click', loadTokens);
    }

    // Toggle visibility for Ollama token
    toggleOllamaBtn.onclick = () => {
      const icon = toggleOllamaBtn.querySelector('i');
      if (ollamaTokenInput.type === 'password') {
        ollamaTokenInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
      } else {
        ollamaTokenInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
      }
    };

    // Toggle visibility for Groq token
    toggleGroqBtn.onclick = () => {
      const icon = toggleGroqBtn.querySelector('i');
      if (groqTokenInput.type === 'password') {
        groqTokenInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
      } else {
        groqTokenInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
      }
    };

    // Toggle visibility for NVIDIA token
    toggleNvidiaBtn.onclick = () => {
      const icon = toggleNvidiaBtn.querySelector('i');
      if (nvidiaTokenInput.type === 'password') {
        nvidiaTokenInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
      } else {
        nvidiaTokenInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
      }
    };

    // Save tokens to server
    saveTokensBtn.onclick = async () => {
      const ollamaToken = ollamaTokenInput.value.trim();
      const groqToken = groqTokenInput.value.trim();
      const nvidiaToken = nvidiaTokenInput.value.trim();
      
      try {
        if (ollamaToken) {
          await apiRequest('/tokens/', 'POST', { service_name: 'ollama', token: ollamaToken });
        }
        if (groqToken) {
          await apiRequest('/tokens/', 'POST', { service_name: 'groq', token: groqToken });
        }
        if (nvidiaToken) {
          await apiRequest('/tokens/', 'POST', { service_name: 'nvidia', token: nvidiaToken });
        }
        
        tokenStatus.textContent = '✅ Токены сохранены';
        tokenStatus.className = 'text-sm text-center text-green-400';
        
        // Clear input fields after save
        ollamaTokenInput.value = '';
        groqTokenInput.value = '';
        nvidiaTokenInput.value = '';
        
        setTimeout(() => { tokenStatus.textContent = ''; loadTokens(); }, 3000);
      } catch (err) {
        tokenStatus.textContent = '❌ Ошибка: ' + err.message;
        tokenStatus.className = 'text-sm text-center text-red-400';
        setTimeout(() => { tokenStatus.textContent = ''; }, 3000);
      }
    };

    // Clear tokens from server
    clearTokensBtn.onclick = async () => {
      try {
        await apiRequest('/tokens/ollama', 'DELETE');
        await apiRequest('/tokens/groq', 'DELETE');
        await apiRequest('/tokens/nvidia', 'DELETE');
        
        ollamaTokenInput.value = '';
        groqTokenInput.value = '';
        nvidiaTokenInput.value = '';
        ollamaTokenInput.placeholder = 'ollama_...';
        groqTokenInput.placeholder = 'gsk_...';
        nvidiaTokenInput.placeholder = 'nvapi-...';
        
        tokenStatus.textContent = '🗑️ Токены удалены';
        tokenStatus.className = 'text-sm text-center text-gray-400';
        setTimeout(() => { tokenStatus.textContent = ''; }, 3000);
      } catch (err) {
        tokenStatus.textContent = '❌ Ошибка: ' + err.message;
        tokenStatus.className = 'text-sm text-center text-red-400';
        setTimeout(() => { tokenStatus.textContent = ''; }, 3000);
      }
    };
  }
};