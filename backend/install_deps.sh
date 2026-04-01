#!/bin/bash
# 安装依赖脚本

echo "📦 安装 1688 爬虫依赖..."

# 检查 uv 是否可用
if command -v uv &> /dev/null; then
    echo "✅ 使用 uv 安装依赖"
    cd "$(dirname "$0")"
    uv pip install --system -r requirements.txt
else
    echo "⚠️  uv 不可用，尝试使用 pip3"
    pip3 install -r requirements.txt
fi

echo "✅ 依赖安装完成"
