#!/bin/bash
# webLing 一键部署脚本

set -e

echo "=== webLing 部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: 请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 请先安装 docker-compose"
    exit 1
fi

# 构建 embed.js
echo "构建 embed.js..."
cd apps/embed && npm run build && cd ../..

# 启动服务
echo "启动服务..."
docker-compose up -d --build

echo ""
echo "=== 部署完成 ==="
echo "前端: http://localhost"
echo "后端 API: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
