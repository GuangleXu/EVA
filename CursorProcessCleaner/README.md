# Cursor Python 进程清理工具

该工具用于解决 Cursor 编辑器在使用过程中产生大量 Python 后台进程的问题，通过定时清理闲置的 Python 进程来提高系统性能。

## 功能说明

1. **自动识别** - 智能识别与 Cursor 相关的 Python 进程
2. **保留活跃进程** - 只清理闲置超过 10 分钟的进程，保留活跃的进程
3. **定时执行** - 每 30 分钟自动运行一次，无需手动干预
4. **安全可靠** - 只清理确定为 Cursor 相关的闲置 Python 进程

## 使用方法

### 方法一：手动运行清理

直接运行 `clean_python.ps1` 脚本进行一次性清理：

```powershell
.\clean_python.ps1
```

### 方法二：设置定时任务（推荐）

以管理员权限运行 PowerShell，然后执行 `setup_task.ps1` 脚本：

```powershell
# 以管理员权限运行 PowerShell
Start-Process powershell -Verb RunAs -ArgumentList "-File `".\setup_task.ps1`""
```

或者手动右键 `setup_task.ps1` 文件，选择"以管理员身份运行"。

## 查看任务状态

设置完成后，可以通过以下方式查看任务：

1. 打开"任务计划程序"
2. 在左侧导航中点击"任务计划程序库"
3. 找到名为 "CursorPythonCleaner" 的任务

## 自定义设置

如需调整清理频率或其他参数：

1. 编辑 `setup_task.ps1` 文件中的 `$triggerFrequency` 变量（默认为 30 分钟）
2. 编辑 `clean_python.ps1` 文件中的进程判断条件

## 注意事项

- 脚本会保留最近 5 分钟内启动的进程
- 脚本会保留有 CPU 活动的进程
- 只会清理启动超过 10 分钟且无活动的进程 