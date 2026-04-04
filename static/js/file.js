window.file = {
  getFileIcon: (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'webm'];
    const audioExts = ['mp3', 'wav', 'm4a', 'flac', 'ogg'];
    if (videoExts.includes(ext)) return `<i class="fas fa-video text-red-400"></i>`;
    else if (audioExts.includes(ext)) return `<i class="fas fa-music text-green-400"></i>`;
    return `<i class="fas fa-file text-gray-400"></i>`;
  },
  renderFilePreviews: () => {
    const container = document.getElementById('file-previews');
    if (window.state.selectedFiles.length === 0) { container.innerHTML = ''; return; }
    container.innerHTML = window.state.selectedFiles.map((file, index) => `
      <div class="flex items-center gap-2.5 glass px-4 py-2.5 rounded-xl border border-indigo-500/20 animate-fadeIn">
        ${window.file.getFileIcon(file.name)}
        <span class="text-sm text-gray-300 max-w-[180px] truncate">${file.name}</span>
        <span class="text-xs text-gray-500">${(file.size / 1024 / 1024).toFixed(1)} MB</span>
        <button onclick="window.file.removeFile(${index})" class="text-gray-400 hover:text-red-400 btn-icon p-1 rounded-lg hover:bg-red-500/10 transition"><i class="fas fa-times"></i></button>
      </div>`).join('');
  },
  removeFile: (index) => {
    window.state.selectedFiles.splice(index, 1);
    window.file.renderFilePreviews();
    window.chat.saveChatState(window.state.currentChatId);
    window.app.updateSendButton();
  },
  init: () => {
    document.getElementById('file-input').onchange = () => {
      const files = Array.from(document.getElementById('file-input').files);
      files.forEach(f => { if (!window.state.selectedFiles.find(x => x.name === f.name)) window.state.selectedFiles.push(f); });
      window.file.renderFilePreviews();
      window.chat.saveChatState(window.state.currentChatId);
      window.app.updateSendButton();
      document.getElementById('file-input').value = '';
    };
  }
};