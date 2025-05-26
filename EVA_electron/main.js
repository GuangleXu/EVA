const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const axios = require('axios'); // 如果与后端通信需要，确保 axios 被正确引入
const net = require('net');

let mainWindow; // 确保 mainWindow 是全局变量
let isBackendChecked = false;

process.on('uncaughtException', (err) => {
  console.error('主进程未捕获异常:', err);
});

// 检查后端是否可用
async function checkBackendHealth() {
    try {
        console.log('🔍 检查后端服务...');
        const response = await axios.get('http://localhost:8000/api/health/', { timeout: 5000 });
        
        // 检查基础健康状态
        const isHealthy = response.status === 200 && response.data.status === 'ok';
        
        // 检查情感分析模块状态
        let emotionAnalyzerStatus = false;
        try {
            const moduleResponse = await axios.get('http://localhost:8000/api/modules/status', { timeout: 3000 });
            emotionAnalyzerStatus = moduleResponse.data?.emotional_analyzer === 'loaded';
            console.log(`🧠 情感分析模块状态: ${emotionAnalyzerStatus ? '正常' : '未加载'}`);
        } catch (moduleError) {
            console.warn('⚠️ 情感分析模块状态检查失败:', moduleError.message);
        }
        
        return {
            isHealthy,
            emotionAnalyzerStatus
        };
    } catch (error) {
        console.error('❌ 后端服务检查失败:', error.message);
        return {
            isHealthy: false,
            emotionAnalyzerStatus: false
        };
    }
}

// 检查端口是否可用
function isPortAvailable(port) {
    return new Promise((resolve) => {
        const tester = net.createServer()
            .once('error', () => {
                // 端口被占用
                resolve(false);
            })
            .once('listening', () => {
                // 端口可用
                tester.close();
                resolve(true);
            })
            .listen(port);
    });
}

// 检查后端服务和端口
async function checkBackendServicesAndContinue() {
    // 避免重复检查
    if (isBackendChecked) return;

    const portAvailable = await isPortAvailable(8000);
    
    if (portAvailable) {
        // 端口未被占用，提示用户启动后端
        console.log('⚠️ 端口8000未被占用，可能需要启动后端服务');
        isBackendChecked = true;
        
        dialog.showMessageBox(mainWindow, {
            type: 'warning',
            title: 'EVA 后端未启动',
            message: '后端服务未检测到',
            detail: '请确保已启动EVA后端服务。\n\n启动方式:\n1. 打开Docker Desktop\n2. 在命令行中执行: docker-compose up -d',
            buttons: ['继续', '退出'],
            defaultId: 0
        }).then(result => {
            if (result.response === 1) {
                // app.quit(); // 暂时注释，防止误关闭
                console.log('【调试】用户选择退出，但已阻止自动关闭应用');
            }
        });
    } else {
        // 端口被占用，检查是否是EVA后端
        const healthCheck = await checkBackendHealth();
        
        if (healthCheck.isHealthy) {
            console.log('✅ 后端服务运行正常');
            
            // 检查情感分析模块状态
            if (!healthCheck.emotionAnalyzerStatus) {
                console.log('⚠️ 情感分析模块未加载，功能可能受限');
                
                dialog.showMessageBox(mainWindow, {
                    type: 'info',
                    title: 'EVA 情感分析模块',
                    message: '情感分析模块未完全加载',
                    detail: '情感分析模块未加载或初始化中，部分功能可能暂时受限。\n\n这可能是因为：\n1. 系统资源不足\n2. 模型仍在初始化\n3. 配置问题\n\n系统将继续使用备选方案运行。',
                    buttons: ['确定'],
                    defaultId: 0
                });
            }
        } else {
            console.log('⚠️ 端口8000被占用，但无法连接到EVA后端');
            
            if (!isBackendChecked) {  // 避免重复显示对话框
                isBackendChecked = true;
                
                dialog.showMessageBox(mainWindow, {
                    type: 'warning',
                    title: 'EVA 后端异常',
                    message: '无法连接到EVA后端服务',
                    detail: '端口8000已被占用，但无法确认是否为EVA后端服务。\n\n可能的解决方法:\n1. 检查Docker容器状态\n2. 重启Docker服务\n3. 释放8000端口',
                    buttons: ['继续', '退出'],
                    defaultId: 0
                }).then(result => {
                    if (result.response === 1) {
                        // app.quit(); // 暂时注释，防止误关闭
                        console.log('【调试】用户选择退出，但已阻止自动关闭应用');
                    }
                });
            }
        }
    }
}

app.on('ready', () => {
    console.log('🚀 Electron 应用启动...');
    
    // 创建主窗口
    process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = true; // 禁用 Electron 的安全警告
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'), // 加载预加载脚本
            contextIsolation: true, // 启用上下文隔离，增加安全性
            enableRemoteModule: false, // 禁用 remote 模块
            nodeIntegration: false, // 禁用 Node.js 集成
            webSecurity: true,
            permissions: [
                'audioCapture',
                'audio'
            ]
        },
    });

    console.log('📝 加载 HTML 文件...');
    mainWindow.loadFile('index.html');

    // 打开开发者工具（调试模式下使用）
    mainWindow.webContents.openDevTools();

    // 监听页面加载完成事件
    mainWindow.webContents.on('did-finish-load', () => {
        console.log('✅ 页面加载完成');
        // 向渲染进程发送初始化消息
        mainWindow.webContents.send('app-ready');
        
        // 检查后端服务状态
        setTimeout(() => {
            checkBackendServicesAndContinue();
        }, 1000);
    });

    // 监听渲染进程错误
    mainWindow.webContents.on('render-process-gone', (event, details) => {
        console.error('❌ 渲染进程崩溃:', details);
    });

    // 监听未捕获的异常
    mainWindow.webContents.on('uncaught-exception', (event, error) => {
        console.error('❌ 未捕获的异常:', error);
    });

    console.log('✅ 主进程初始化完成');
});

// 监听所有窗口关闭事件
app.on('window-all-closed', () => {
    console.log('👋 所有窗口已关闭');
    if (process.platform !== 'darwin') {
        // app.quit(); // 暂时注释，防止误关闭
        console.log('【调试】所有窗口已关闭，但已阻止自动关闭应用');
    }
});

