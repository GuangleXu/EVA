// 全局变量和状态
let socket;
let inputField;
let outputField;
let sendButton;
let apiSelector;
const fixedVoiceIndex = 0;

const CONNECTION_STATE = {
    maxReconnectAttempts: 5,
    reconnectBaseDelay: 1000,
    healthCheckUrl: "http://localhost:8000/api/health/",
    reconnectAttempts: 0,
    isManualClose: false,
    lastHeartbeat: 0,
    heartbeatTimer: null,
    heartbeatTimeout: 45000,
    // WebSocket配置
    wsConfig: {
        llm: {
            path: "ws://localhost:8000/ws/llm/",
            name: "llm-websocket"
        },
        memory: {
            path: "ws://localhost:8000/ws/memory/",
            name: "memory-websocket"
        }
    }
};

// 更新连接状态
function updateConnectionStatus(message) {
    console.log(`🔄 连接状态更新: ${message}`);
    // 触发自定义事件，更新加载状态显示
    const event = new CustomEvent('EVA_CONNECTION_STATUS', { 
        detail: { message } 
    });
    document.dispatchEvent(event);
}

// 触发连接成功事件
function triggerConnectedEvent() {
    console.log('🎉 触发连接成功事件');
    const event = new CustomEvent('EVA_CONNECTED');
    document.dispatchEvent(event);
}

// 获取后端基础URL
function getBackendBaseUrl() {
    // 使用固定的开发环境URL
    // 如果需要区分环境，可以检查window.location或其他浏览器环境变量
    // 或者可以将配置存储在window对象中：window.EVA_CONFIG = { backendUrl: 'http://localhost:8000' }
    return 'http://localhost:8000';
}

// 全局函数定义
async function waitForBackendAndReconnect() {
    if (CONNECTION_STATE.reconnectAttempts >= CONNECTION_STATE.maxReconnectAttempts) {
        renderMessage("无法连接到服务器，请检查后端服务是否启动", "error");
        sendButton.disabled = true;
        updateConnectionStatus("连接失败，请检查后端服务是否启动");
        return;
    }
    CONNECTION_STATE.reconnectAttempts++;
    const delay = CONNECTION_STATE.reconnectBaseDelay * Math.pow(2, CONNECTION_STATE.reconnectAttempts - 1);
    updateConnectionStatus(`正在尝试重新连接...(${CONNECTION_STATE.reconnectAttempts}/${CONNECTION_STATE.maxReconnectAttempts})`);
    setTimeout(async () => {
        const healthStatus = await checkBackendHealth();
        if (healthStatus.isHealthy) {
            connectWebSocket();
        } else {
            waitForBackendAndReconnect();
        }
    }, delay);
}

function clearSystemMessages() {
    const outputField = document.getElementById("output");
    if (!outputField) return;
    const messages = outputField.querySelectorAll('.message.error, .message.warning, .message.system');
    messages.forEach(msg => msg.remove());
}

function renderMessage(content, type = "system") {
    console.log("📝 渲染消息:", content);
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);

    const messageContent = document.createElement("span");
    messageContent.classList.add("message-content");
    messageContent.textContent = content;

    const messageTime = document.createElement("span");
    messageTime.classList.add("message-time");
    messageTime.textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });

    // 错误消息，带帮助
    if (type === "error" && content.includes("后端服务")) {
        const helpText = document.createElement("div");
        helpText.classList.add("help-text");
        helpText.innerHTML = "<strong>可能的解决方法:</strong><br>" +
            "1. 检查Docker Desktop是否正在运行<br>" +
            "2. 尝试重启Docker容器: <code>docker-compose down && docker-compose up -d</code><br>" +
            "3. 确认端口8000未被其他程序占用";
        messageContainer.appendChild(messageContent);
        messageContainer.appendChild(messageTime);
        messageContainer.appendChild(helpText);
    } 
    // 警告消息
    else if (type === "warning") {
        const warningText = document.createElement("div");
        warningText.classList.add("warning-text");
        warningText.innerHTML = "<strong>提示信息:</strong><br>" +
            "EVA将使用关键词分析作为备选方案继续运行。<br>" +
            "这不会影响基本对话功能，但可能影响情感分析相关功能。";
        messageContainer.appendChild(messageContent);
        messageContainer.appendChild(messageTime);
        messageContainer.appendChild(warningText);
    }
    // 用户消息/助手消息/系统消息
    else {
        messageContainer.appendChild(messageContent);
        messageContainer.appendChild(messageTime);
    }

    outputField.appendChild(messageContainer);
    outputField.scrollTop = outputField.scrollHeight;
}

// 健康检查函数：只在真正网络断开、接口500/超时等异常时才弹窗
async function checkBackendHealth() {
    try {
        console.log("🔍 正在检查后端健康状态...");
        updateConnectionStatus("正在检查后端服务状态...");
        const baseUrl = getBackendBaseUrl();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        try {
            const response = await fetch(`${baseUrl}/api/health/`, {
                method: "GET",
                headers: { "Accept": "application/json" },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                // 只有500等严重错误才弹窗
                if (response.status >= 500) {
                    renderMessage(`后端服务异常: HTTP ${response.status}`, "error");
                }
                updateConnectionStatus(`后端服务返回错误: HTTP ${response.status}`);
                return { isHealthy: false, modulesStatus: {} };
            }
            const data = await response.json().catch(() => null);
            console.log("✅ 后端健康状态:", data);
            clearSystemMessages();
            let emotionAnalyzerStatus = false;
            try {
                updateConnectionStatus("正在检查情感分析模块...");
                const moduleResponse = await fetch(`${baseUrl}/api/modules/status`, {
                    method: "GET",
                    headers: { "Accept": "application/json" }
                });
                if (moduleResponse.ok) {
                    const moduleData = await moduleResponse.json();
                    emotionAnalyzerStatus = moduleData?.emotional_analyzer === 'loaded';
                    console.log(`🧠 情感分析模块状态: ${emotionAnalyzerStatus ? '正常' : '未加载'}`);
                    if (!emotionAnalyzerStatus) {
                        renderMessage("情感分析模块未完全加载，部分功能可能受限", "system");
                    }
                }
            } catch (moduleError) {
                console.warn("⚠️ 情感分析模块状态检查失败:", moduleError.message);
            }
            return { 
                isHealthy: data && data.status === "ok",
                emotionAnalyzerStatus,
            };
        } catch (fetchError) {
            clearTimeout(timeoutId);
            throw fetchError;
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            renderMessage("后端服务连接超时，请检查服务是否启动", "error");
            updateConnectionStatus("连接超时，请检查后端服务是否启动");
        } else {
            // 只有网络断开等严重异常才弹窗
            if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
                renderMessage(`无法连接到后端服务: ${error.message}`, "error");
            }
            updateConnectionStatus(`连接失败: ${error.message}`);
        }
        return { isHealthy: false, emotionAnalyzerStatus: false };
    }
}

// 修改音频播放函数，增强兼容性和容错
function playAudioFromURL(audioUrl) {
    if (!audioUrl) {
        alert("⚠️ 没有提供音频 URL，无法播放音频");
        return;
    }

    const baseUrl = getBackendBaseUrl();
    let fullUrl = `${baseUrl}${audioUrl}`;
    console.log("🎵 播放音频，完整 URL:", fullUrl);

    // 尝试播放 .wav
    const audio = new Audio(fullUrl);
    audio.volume = 1.0;
    audio.muted = false;
    audio.play()
        .then(() => console.log("✅ 音频播放成功:", fullUrl))
        .catch(error => {
            console.error("❌ 播放 .wav 音频失败，尝试 .mp3:", error);
            // 自动尝试 .mp3 格式
            if (fullUrl.endsWith('.wav')) {
                const mp3Url = fullUrl.replace('.wav', '.mp3');
                const audioMp3 = new Audio(mp3Url);
                audioMp3.volume = 1.0;
                audioMp3.muted = false;
                audioMp3.play()
                    .then(() => console.log("✅ .mp3 音频播放成功:", mp3Url))
                    .catch(err2 => {
                        console.error("❌ .mp3 也播放失败:", err2);
                        let msg = `音频播放失败！\n\n错误信息: ${error.message || error}`;
                        msg += "\n\n请检查：\n1. 系统音量是否开启\n2. EVA 是否被静音\n3. 音频文件是否有效\n4. 若为首次播放，需手动点击页面激活音频权限";
                        msg += `\n\n[手动测试] 可点击下载音频文件：\n${fullUrl}`;
                        alert(msg);
                    });
            } else {
                let msg = `音频播放失败！\n\n错误信息: ${error.message || error}`;
                msg += "\n\n请检查：\n1. 系统音量是否开启\n2. EVA 是否被静音\n3. 音频文件是否有效\n4. 若为首次播放，需手动点击页面激活音频权限";
                msg += `\n\n[手动测试] 可点击下载音频文件：\n${fullUrl}`;
                alert(msg);
            }
        });
}

function startHeartbeat() {
    console.log("💓 启动心跳检测...");
    stopHeartbeat();

    CONNECTION_STATE.heartbeatTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            console.log("💓 发送心跳...");
            socket.send(JSON.stringify({ type: "heartbeat", ping: true }));
            CONNECTION_STATE.lastHeartbeat = Date.now();
        }
    }, 30000);
}

function stopHeartbeat() {
    if (CONNECTION_STATE.heartbeatTimer) {
        console.log("🛑 停止心跳检测");
        clearInterval(CONNECTION_STATE.heartbeatTimer);
        CONNECTION_STATE.heartbeatTimer = null;
    }
}

function sendMessage() {
    console.log("🚀 开始发送消息...");
    const message = inputField.value.trim();
    console.log("📝 消息内容:", message);

    if (!message) {
        console.warn("⚠️ 试图发送空消息，已阻止");
        return;
    }

    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error("❌ WebSocket 未连接，状态:", socket ? socket.readyState : "socket 未初始化");
        renderMessage("服务器未连接，稍后再试", "error");
        return;
    }

    const messageId = crypto.randomUUID();
    CONNECTION_STATE.lastMessageId = messageId;
    console.log("🔑 生成消息ID:", messageId);

    renderMessage(message, "user");
    inputField.value = "";

    try {
        console.log("📤 准备发送消息:", {
            type: "message",
            message_id: messageId,
            message: message,
            api_choice: apiSelector.value,
            need_speech: apiSelector.value === "deepseek",
            voice_index: fixedVoiceIndex
        });

        socket.send(JSON.stringify({
            type: "message",
            message_id: messageId,
            message: message,
            api_choice: apiSelector.value,
            need_speech: apiSelector.value === "deepseek",
            voice_index: fixedVoiceIndex
        }));
        console.log("✅ 消息发送成功");
    } catch (error) {
        console.error("❌ 发送消息失败:", error);
        renderMessage("消息发送失败", "error");
    }
}

// 修改 WebSocket 连接函数
async function connectWebSocket() {
    try {
        const healthStatus = await checkBackendHealth();
        if (!healthStatus.isHealthy) {
            clearSystemMessages();
            renderMessage("后端服务未就绪，请确保Docker容器已正确启动", "error");
            updateConnectionStatus("后端服务未就绪，请检查Docker容器状态");
            waitForBackendAndReconnect();
            return;
        }
        // 连接成功时，清除所有系统/错误/警告消息
        clearSystemMessages();

        // 创建 WebSocket 连接
        const wsUrl = CONNECTION_STATE.wsConfig.llm.path;
        console.log(`🔌 尝试连接到 WebSocket: ${wsUrl}`);
        renderMessage("正在连接到 EVA 后端服务...", "system");
        updateConnectionStatus("正在建立WebSocket连接...");

        if (socket && socket.readyState === WebSocket.OPEN) {
            console.log("🔄 关闭现有连接");
            CONNECTION_STATE.isManualClose = true;
            socket.close();
        }

        // 设置较短的连接超时
        const connectTimeout = setTimeout(() => {
            if (socket && socket.readyState !== WebSocket.OPEN) {
                console.warn("⚠️ WebSocket 连接超时");
                socket.close();
                renderMessage("WebSocket连接超时，请检查网络状态和服务器配置", "error");
                updateConnectionStatus("WebSocket连接超时");
                waitForBackendAndReconnect();
            }
        }, 5000);

        socket = new WebSocket(wsUrl);
        console.log("🔄 WebSocket 已创建，等待连接...");

        socket.onopen = (event) => {
            clearTimeout(connectTimeout);
            console.log("✅ WebSocket 连接成功");
            clearSystemMessages(); // 连接成功时清除所有系统/错误/警告消息
            renderMessage("已连接到 EVA 后端服务", "system");
            updateConnectionStatus("连接成功");
            
            // 触发连接成功事件，隐藏加载动画
            triggerConnectedEvent();
            
            // 如果情感分析模块状态异常，显示额外提示
            if (!healthStatus.emotionAnalyzerStatus) {
                renderMessage("情感分析模块未完全加载，系统将使用备选方案进行情感分析", "warning");
            }
            
            CONNECTION_STATE.reconnectAttempts = 0;
            sendButton.disabled = false;
            startHeartbeat();
        };

        socket.onmessage = handleWebSocketMessage;

        socket.onclose = (event) => {
            clearTimeout(connectTimeout);
            console.log(`🔌 WebSocket 连接关闭: ${event.code} ${event.reason}`);
            stopHeartbeat();
            sendButton.disabled = true;
            
            if (!CONNECTION_STATE.isManualClose) {
                clearSystemMessages();
                renderMessage("与服务器的连接已断开，正在尝试重新连接...", "system");
                updateConnectionStatus("连接已断开，正在尝试重新连接...");
                setTimeout(waitForBackendAndReconnect, 1000);
            } else {
                CONNECTION_STATE.isManualClose = false;
            }
        };

        socket.onerror = (error) => {
            clearTimeout(connectTimeout);
            console.error("❌ WebSocket 错误:", error);
            clearSystemMessages();
            renderMessage("连接错误，请检查网络或后端服务状态", "error");
            updateConnectionStatus("WebSocket连接错误");
            sendButton.disabled = true;
        };
    } catch (error) {
        console.error("❌ 创建 WebSocket 连接时出错:", error);
        clearSystemMessages();
        renderMessage(`连接错误: ${error.message}`, "error");
        updateConnectionStatus(`连接错误: ${error.message}`);
        sendButton.disabled = true;
        waitForBackendAndReconnect();
    }
}

// WebSocket消息处理：无type消息完全忽略，不影响UI和弹窗
async function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        console.log("📨 收到消息:", data);
        if (!data.type || typeof data.type !== 'string') {
            // 完全忽略无type消息，不影响UI和弹窗
            return;
        }
        switch (data.type) {
            case "pong":
                CONNECTION_STATE.lastHeartbeat = Date.now();
                break;
            case "error":
                renderMessage(data.message, "error");
                break;
            case "response":
                renderMessage(data.response, "assistant");
                if (data.speech_url) {
                    playAudioFromURL(data.speech_url);
                }
                break;
            case "system":
                renderMessage(data.message, "system");
                break;
            case "warning":
                renderMessage(data.message, "warning");
                break;
            default:
                // 只在控制台提示未知类型，不弹窗
                console.warn("⚠️ 未知消息类型:", data);
                break;
        }
    } catch (error) {
        renderMessage("收到无效的服务器响应", "error");
    }
}

// 在前端启动时自动连接 /ws/memory/，保持 MemoryConsumer 激活
let memorySocket = null;
function connectMemoryWebSocket() {
    memorySocket = new WebSocket("ws://localhost:8000/ws/memory/");
    memorySocket.onopen = () => {
        console.log("🟢 Memory WebSocket 已连接");
    };
    memorySocket.onclose = () => {
        console.warn("🔴 Memory WebSocket 已断开，尝试重连...");
        setTimeout(connectMemoryWebSocket, 3000); // 断线自动重连
    };
    memorySocket.onerror = (err) => {
        console.error("❌ Memory WebSocket 错误:", err);
    };
    memorySocket.onmessage = (event) => {
        // 可根据需要处理 memory 通道的消息
        console.log("📥 Memory WebSocket 收到消息:", event.data);
    };
}

// 初始化函数
function initializeApp() {
    console.log("🚀 开始初始化应用...");

    // 获取 DOM 元素
    sendButton = document.getElementById("send-btn");
    inputField = document.getElementById("input");
    outputField = document.getElementById("output");
    apiSelector = document.getElementById("api-choice");

    console.log("🔍 DOM 元素检查:", {
        sendButton: sendButton ? "存在" : "不存在",
        inputField: inputField ? "存在" : "不存在",
        outputField: outputField ? "存在" : "不存在",
        apiSelector: apiSelector ? "存在" : "不存在"
    });

    if (!sendButton || !inputField || !outputField || !apiSelector) {
        console.error("❌ 找不到部分必要的 UI 元素");
        return;
    }

    // 初始化时禁用发送按钮，直到连接成功
    sendButton.disabled = true;
    console.log("✅ 发送按钮状态:", sendButton.disabled ? "禁用" : "启用");

    // 显示初始连接提示
    renderMessage("正在尝试连接到EVA后端服务...", "system");

    sendButton.onclick = () => {
        console.log("🖱️ 发送按钮被点击");
        sendMessage();
    };

    inputField.onkeypress = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            console.log("⌨️ 检测到回车键");
            sendMessage();
        }
    };

    inputField.onfocus = () => {
        console.log("🎯 输入框获得焦点");
    };

    inputField.onblur = () => {
        console.log("👋 输入框失去焦点");
    };

    // 添加样式以显示帮助文本和警告文本
    const style = document.createElement('style');
    style.textContent = `
    .help-text {
        margin-top: 8px;
        font-size: 12px;
        color: #888;
        background-color: #f5f5f5;
        padding: 8px;
        border-radius: 4px;
        border-left: 3px solid #ff6b6b;
    }
    .help-text strong {
        color: #ff6b6b;
    }
    .help-text code {
        background-color: #e9e9e9;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: monospace;
    }
    .warning-text {
        margin-top: 8px;
        font-size: 12px;
        color: #856404;
        background-color: #fff3cd;
        padding: 8px;
        border-radius: 4px;
        border-left: 3px solid #ffeeba;
    }
    .warning-text strong {
        color: #856404;
    }
    .message.warning {
        background-color: rgba(255, 243, 205, 0.2);
        border-left: 3px solid #ffc107;
    }
    `;
    document.head.appendChild(style);

    console.log("🚀 开始初始化 WebSocket 连接...");
    connectWebSocket();
}

// 监听主进程消息
window.addEventListener('message', (event) => {
    if (event.data === 'app-ready') {
        console.log('📨 收到主进程初始化消息');
        initializeApp();
    }
});

// 确保在 DOM 加载完成后也初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM 加载完成');
    initializeApp();
    connectMemoryWebSocket();
});    