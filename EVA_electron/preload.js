const { contextBridge, ipcRenderer } = require('electron');

// 使用 contextBridge 暴露安全 API
contextBridge.exposeInMainWorld('electronAPI', {
    sendMessage: (channel, data) => {
        const validChannels = ['query-ollama']; // 允许的通信通道
        if (validChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },
    onMessage: (channel, callback) => {
        const validChannels = ['ollama-response']; // 允许的接收通道
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => callback(...args));
        }
    }
});

// 暴露必要的 Web API
contextBridge.exposeInMainWorld('webAPI', {
    AudioContext: window.AudioContext || window.webkitAudioContext,
    createAudioContext: () => new (window.AudioContext || window.webkitAudioContext)()
});
