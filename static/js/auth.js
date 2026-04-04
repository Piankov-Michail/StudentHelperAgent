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
    const hfTokenInput = document.getElementById('hf-token');
    const ollamaTokenInput = document.getElementById('ollama-token');
    const toggleHfBtn = document.getElementById('toggle-hf-token');
    const toggleOllamaBtn = document.getElementById('toggle-ollama-token');
    const saveTokensBtn = document.getElementById('save-tokens-btn');
    const clearTokensBtn = document.getElementById('clear-tokens-btn');
    const tokenStatus = document.getElementById('token-status');

    // Load saved tokens from server
    const loadTokens = async () => {
      try {
        const tokens = await apiRequest('/tokens/');
        const hfToken = tokens.find(t => t.service === 'huggingface');
        const ollamaToken = tokens.find(t => t.service === 'ollama');
        
        if (hfToken && hfToken.has_value) {
          hfTokenInput.placeholder = '••••••••••••••••';
        }
        if (ollamaToken && ollamaToken.has_value) {
          ollamaTokenInput.placeholder = '••••••••••••••••';
        }
      } catch (e) {
        console.error('Failed to load tokens:', e);
      }
    };

    // Load tokens when settings modal opens
    document.getElementById('settings-btn').addEventListener('click', loadTokens);

    // Toggle visibility for HF token
    toggleHfBtn.onclick = () => {
      const icon = toggleHfBtn.querySelector('i');
      if (hfTokenInput.type === 'password') {
        hfTokenInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
      } else {
        hfTokenInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
      }
    };

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

    // Save tokens to server
    saveTokensBtn.onclick = async () => {
      const hfToken = hfTokenInput.value.trim();
      const ollamaToken = ollamaTokenInput.value.trim();
      
      try {
        if (hfToken) {
          await apiRequest('/tokens/', 'POST', { service_name: 'huggingface', token: hfToken });
        }
        if (ollamaToken) {
          await apiRequest('/tokens/', 'POST', { service_name: 'ollama', token: ollamaToken });
        }
        
        tokenStatus.textContent = '✅ Токены сохранены';
        tokenStatus.className = 'text-sm text-center text-green-400';
        
        // Clear input fields after save
        hfTokenInput.value = '';
        ollamaTokenInput.value = '';
        
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
        await apiRequest('/tokens/huggingface', 'DELETE');
        await apiRequest('/tokens/ollama', 'DELETE');
        
        hfTokenInput.value = '';
        ollamaTokenInput.value = '';
        hfTokenInput.placeholder = 'hf_...';
        ollamaTokenInput.placeholder = 'ollama_...';
        
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