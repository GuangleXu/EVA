# EVA 项目 Docker 环境启动脚本
# 使用方法: .\temp\start_docker.ps1

Write-Host "开始启动 EVA 项目 Docker 环境" -ForegroundColor Cyan

# 检查 .env 文件是否存在
if (-not (Test-Path -Path "EVA_backend\.env")) {
    Write-Host "错误：EVA_backend\.env 文件不存在！" -ForegroundColor Red
    Write-Host "正在尝试创建 .env 文件..." -ForegroundColor Yellow
    
    # 运行创建 .env 文件的脚本
    if (Test-Path -Path "temp\create_env.ps1") {
        . .\temp\create_env.ps1
    } else {
        Write-Host "无法找到 create_env.ps1 脚本，请手动创建 .env 文件！" -ForegroundColor Red
        exit 1
    }
}

# 检查必要目录
Write-Host "检查必要目录..." -ForegroundColor Yellow
$directories = @(
    "EVA_backend\logfiles",
    "EVA_backend\media"
)

foreach ($dir in $directories) {
    if (-not (Test-Path -Path $dir)) {
        Write-Host "创建目录: $dir" -ForegroundColor Yellow
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}

# 构建镜像并启动容器
Write-Host "开始构建 Docker 镜像..." -ForegroundColor Yellow
docker-compose build

# 检查构建结果
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker 镜像构建失败！请检查错误信息。" -ForegroundColor Red
    exit 1
}

Write-Host "Docker 镜像构建成功！" -ForegroundColor Green
Write-Host "正在启动 Docker 容器..." -ForegroundColor Yellow

# 启动容器
docker-compose up -d

# 检查启动结果
if ($LASTEXITCODE -ne 0) {
    Write-Host "启动 Docker 容器失败！请检查错误信息。" -ForegroundColor Red
    exit 1
}

Write-Host "Docker 容器已成功启动！" -ForegroundColor Green
Write-Host "服务状态：" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n后端服务地址：http://localhost:8000" -ForegroundColor Green
Write-Host "查看日志命令：docker-compose logs -f" -ForegroundColor Yellow
Write-Host "停止命令：docker-compose down" -ForegroundColor Yellow 