// shared state & api
window.state = {
  token: localStorage.getItem('token'),
  currentUser: null,
  currentChatId: null,
  chats: [],
  selectedFiles: [],
  chatStates: {},
  currentAgentType: 'transcript',
  isRegisterMode: false,
  isGenerating: false,
  abortController: null
};

async function apiRequest(endpoint, method = 'GET', body = null, useAuth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (useAuth && window.state.token) headers['Authorization'] = `Bearer ${window.state.token}`;
  const options = { method, headers };
  if (body && method !== 'GET') options.body = JSON.stringify(body);
  
  const res = await fetch(endpoint, options);
  if (res.status === 401) { window.auth.logout(); throw new Error('Unauthorized'); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Ошибка запроса');
  }
  return res.json();
}