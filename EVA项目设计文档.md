📘 EVA AI 助理项目执行文档
更新时间：2025-04-23
项目路径：E:\MyAIAssistant\EVA
本文档结合最新开发架构、模块职责和部署方式，适用于开发者、维护者、部署人员全流程参考。

📌 一、项目概述
1.1 项目目标
EVA 是一款本地运行的 AI 助理，面向"个人专属助手"场景，具备以下核心能力：

理解自然语言输入；

调用 LLM（如 Ollama / DeepSeek）生成回复；

执行用户指令与功能模块联动（如语音播报、GUI 集成）；

完全支持 Docker 容器化部署，后端采用 Django + LangChain + Redis + Pinecone 构建。

🧱 二、项目结构与关键路径
2.1 项目目录结构（核心部分）
EVA/
├── docker-compose.yml # 多容器服务编排
├── file_tree.txt # 目录结构快照（建议定期更新）
├── EVA_backend/
│ ├── .env # 环境变量配置（本地与生产分离）
│ ├── Dockerfile.backend # 后端 + celery 镜像统一构建文件
│ ├── pyproject.toml # Poetry 管理依赖
│ ├── poetry.lock # 锁定依赖版本
│ ├── supervisor.conf # Supervisor 多进程服务配置
│ ├── eva_backend_django/
│ │ └── settings.py # Django 核心配置
│ └── memory_service_app/
│ └── utils/ # 所有记忆模块组件
│ └── models/ # 记忆数据结构
│ └── consumers.py # WebSocket 消费逻辑
├── tests/
│ ├── test_central_executive.py # 中控器联动测试
│ ├── test_memory_system.py # 记忆系统集成测试
│ └── test_rule_memory.py # 规则检索与冲突处理测试
⚙️ 三、开发与运行环境
3.1 推荐配置

项目 推荐配置
操作系统 Windows 10/11 或 WSL2/Ubuntu
Python 3.11.x（建议使用 Poetry）
Docker Desktop 版本，支持 Compose
显卡（可选） RTX 3060 Ti（用于 Ollama）

3.2 核心技术栈

模块 工具/技术 说明
后端框架 Django + Channels Web 框架 + WebSocket 支持
消息队列 Celery + Redis 任务调度 + 缓存中间件
记忆系统 Redis + Pinecone 短期记忆 + 向量检索
LLM 接入 LangChain + DeepSeek/Ollama LLM 框架封装 + 本地运行
依赖管理 Poetry 依赖统一管理
部署方式 Docker + Supervisor 一体化容器部署 + 多进程控制

3.3 健康检查与 Supervisor 配置（2025-05-05 更新）

- 后端服务健康检查统一采用 shell+curl 方案，兼容性强，避免 Python 语法问题。
- 健康检查路径 `/api/health/` 必须与 Django 路由一致，urls.py 需有对应实现。
- 健康检查脚本已优化重试机制和等待时间，避免服务未就绪时误报 unhealthy。
- supervisor.conf 示例：

```
[program:healthcheck]
command=sh -c "sleep 30; echo '🩺 健康检查启动中...'; for i in $(seq 1 10); do curl -sf http://localhost:8000/api/health/ && echo '✅ 健康检查通过' && exit 0; echo '⚠️ 健康检查重试中...'; sleep 10; done; echo '❌ 健康检查多次失败，服务未就绪'; exit 1"
directory=/app
user=appuser
autostart=true
autorestart=false
startsecs=1
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
priority=300
environment=PYTHONPATH="/app"
```

🚀 四、快速启动流程
4.1 Docker 启动前，清理垃圾内容并压缩磁盘

【操作目的说明】
- 释放磁盘空间，避免 Docker/WSL 占用过多硬盘
- 保证后续容器启动和运行更流畅

【详细步骤】

1. 清理 Docker 无用内容（建议定期执行）
   - 在 PowerShell 输入：
     docker system prune -a --volumes  # 清理无用容器、镜像、网络、卷
   - 说明：此命令会释放大量空间，但不会影响正在运行的容器

2. 关闭 WSL 和 Docker Desktop（确保没有相关进程占用虚拟磁盘）
   - 在 PowerShell（普通或管理员模式均可）输入：
     wsl --shutdown  # 彻底关闭所有 WSL 实例
   - 右下角托盘退出 Docker Desktop（如已开启）

3. 压缩 WSL 虚拟磁盘（必须以管理员身份运行 PowerShell）
   - 在"开始菜单"搜索 PowerShell，右键"以管理员身份运行"
   - 输入以下命令（路径请根据实际情况调整）：
     Optimize-VHD -Path "E:\\DockerDesktopWSL\\disk\\docker_data.vhdx" -Mode Full
   - 说明：此命令会将虚拟磁盘文件瘦身，释放 Windows 物理空间
   - 注意：如提示"文件被占用"，请确认 Docker Desktop 和所有 WSL 进程已关闭

【常见问题与解决办法】
- 报错"文件被占用"：请再次确认 Docker Desktop 和 WSL 已完全退出
- 权限不足：请务必用"以管理员身份运行"PowerShell
- 路径不对：请用资源管理器定位 vhdx 文件实际路径

【一键脚本推荐】
可将上述命令整理为 PowerShell 脚本，保存为 cleanup_and_optimize.ps1，右键"以管理员身份运行"即可。

4.2 使用 Docker 启动
cd E:\MyAIAssistant\EVA
docker-compose up --build
docker-compose up -d
4.3 进入后端容器
docker exec -it eva-backend /bin/bash
4.4 启动本地虚拟环境（如不使用 Docker）

python -m venv .venv
.venv\Scripts\activate
poetry install
🧠 五、记忆系统模块与架构（SecondMe 极简架构·最新版）

5.1 模块职责概览

| 模块名称             | 目录路径                                               | 主要职责与说明                         |
|----------------------|--------------------------------------------------------|----------------------------------------|
| central_executive    | utils/central_executive.py                             | 记忆系统唯一调度入口，负责分流调用各类记忆适配器，拼接最终上下文（final_context） |
| 长期记忆适配器       | utils/secondme_integration/memory_adapter.py           | 负责长期记忆的存储、检索、更新、删除，所有操作本地化，支持结构化语义分析 |
| 工作记忆适配器       | utils/secondme_integration/working_memory_adapter.py   | 负责短期/对话记忆的存取、归纳、清理，支持对话历史结构化管理           |
| 规则记忆适配器       | utils/secondme_integration/rule_adapter.py             | 负责规则类记忆的存储、检索、合并、冲突处理，支持多标签与结构化归纳     |
| 配置与参数           | utils/secondme_integration/config.py、secondme_config.json | 统一管理所有记忆系统参数、数据路径、模型配置等                       |

【极简设计优势说明】
- 所有记忆相关操作均通过 central_executive 统一调度，外部只需调用一个入口，极大简化开发和维护。
- 三大适配器（长期、工作、规则）各司其职，底层实现细节对业务层完全透明。
- 支持本地 JSON 存储、结构化语义分析、自动归纳与冲突融合，便于后续扩展。
- 配置集中，支持灵活切换数据路径、模型参数，适应不同部署环境。

【主要接口与调用流程】
- 长期记忆：
  - store_memory(text, metadata)  # 存储长期记忆
  - retrieve_memory(query, top_k) # 检索长期记忆
  - update_memory(memory_id, new_text, metadata) # 更新长期记忆
  - delete_memory(memory_id)      # 删除长期记忆
- 工作记忆：
  - add_message(human_message, ai_message) # 添加一轮对话
  - get_messages(query, top_k)             # 检索对话历史
  - clear_messages()                       # 清空对话历史
  - summarize()                            # 生成对话摘要
- 规则记忆：
  - store_rule(rule_text, metadata)         # 存储规则
  - retrieve_rules(query, top_k)            # 检索规则
  - update_rule(rule_id, rule_text, metadata) # 更新规则
  - delete_rule(rule_id)                    # 删除规则
- 统一调度：
  - central_executive.process_input(raw_input) # 自动判别类型并分流到对应适配器

【注意事项】
- 所有记忆操作建议通过 central_executive 统一调用，避免直接操作底层适配器。
- 如需扩展底层存储或检索方式，仅需修改对应适配器，无需改动业务层代码。
- 配置文件 secondme_config.json 支持自定义数据路径、模型参数，便于本地/生产环境切换。

🧪 六、测试用例与验证方法

测试模块 测试文件路径 说明
中控集成测试 tests/test_central_executive.py 完整上下文 + LLM 验证
记忆系统测试 tests/test_memory_system.py 检索、存储、优先级等流程，建议覆盖"记住我最喜欢中国红"这类典型场景
规则检索测试 tests/test_rule_memory.py 冲突处理 + 规则存储验证

【补充说明】
- 日志已增强，能详细追踪每条消息的存储、检索、上下文拼接、Pinecone 检索分数、去重判断等环节。

🗃 七、部署相关文件路径对照

类型 文件路径 用途
Docker 构建 EVA_backend/Dockerfile.backend 后端镜像统一构建
Supervisor 配置 EVA_backend/supervisor.conf 控制 daphne/worker 启动
服务编排 docker-compose.yml 服务编排 + 环境注入
环境变量 EVA_backend/.env Redis、DB、API key 配置
依赖管理 EVA_backend/pyproject.toml Poetry 管理依赖
锁定依赖 EVA_backend/poetry.lock 保证一致性安装结果
后端配置 EVA_backend/eva_backend_django/settings.py Django 核心配置
🧭 八、推荐最佳实践
✅ 使用 .env 文件统一管理配置，避免敏感信息暴露；
✅ 只保留 Dockerfile.backend，将 Celery 与 Django 后端整合统一容器；
✅ 采用 Poetry 维护依赖，所有服务构建与运行过程一致；
✅ 推荐结合 GitHub Actions 实现自动化测试 + 构建流程；
✅ 测试覆盖后续持续补全，特别是规则模块、冲突分支与上下文整合。
✅ 记忆系统建议定期运行 auto_cleanup、merge_similar_rules、auto_optimize_rules 等方法，保持内容高质量和智能进化。

【常见问题与排查建议】
- 健康检查失败时，优先检查端口监听、服务初始化慢、依赖服务（如 Redis、Postgres）状态。
- 记忆检索异常时，先查 combine_context 日志，定位是存储、检索还是拼接环节出错。
- 如需保留原始输入文本用于审计，可在 SensoryBuffer 后双份存储。

📝 九、日志系统规范与最佳实践（2025-05-21 新增）

1. 日志目录统一为：`EVA_backend/logfiles`
2. 日志文件类型：`system.log`、`error.log`、`django.log`、`celery.log` 等
3. 日志写入模式：全部采用追加（`a`）模式，编码统一为 `utf-8`
4. 日志等级：支持 `DEBUG`、`INFO`、`WARNING`、`ERROR`
5. 日志查找命令推荐：
   - PowerShell/Windows：`ls EVA_backend/logfiles`，`type ... | findstr "DEBUG"`
   - Linux/Mac：`ls EVA_backend/logfiles`，`cat ... | grep DEBUG`
6. 常见问题与解决方案：
   - 路径找不到：优先检查目录拼写和当前工作目录
   - 日志无内容：检查日志等级和 logger 配置
7. 自动化脚本、人工排查、团队协作时，务必优先查阅本节内容，避免路径、命令、权限等低级错误。


| 模块名称           | 目录路径                                               | 说明                       |
|--------------------|--------------------------------------------------------|----------------------------|
| 后端主目录         | EVA_backend/                                           | 后端所有代码根目录         |
| 记忆系统           | EVA_backend/memory_service_app/utils/                  | 记忆相关适配器与工具       |
| 长期记忆           | EVA_backend/memory_service_app/utils/long_term_memory/ | Pinecone 长期记忆实现      |
| 工作记忆           | EVA_backend/memory_service_app/utils/working_term_memory/ | Redis 工作记忆实现      |
| 规则记忆           | EVA_backend/memory_service_app/utils/rule_memory/      | 规则存储与冲突处理         |
| Second-Me 适配层   | EVA_backend/memory_service_app/utils/secondme_integration/ | Second-Me 相关适配器   |
| 日志系统           | EVA_backend/logfiles/                                  | 所有日志文件统一存放目录   |
| 测试用例           | EVA_backend/tests/                                     | 自动化测试脚本与用例       |
| 配置文件           | EVA_backend/memory_service_app/utils/secondme_integration/secondme_config.json | Second-Me 配置文件 |

