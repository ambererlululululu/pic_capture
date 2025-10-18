#!/bin/bash

echo "🖼️  图片链接提取器"
echo "=================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python"
    exit 1
fi

# 检查依赖是否安装
echo "📦 检查依赖包..."
python3 -c "import flask, requests, bs4, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请手动运行: pip3 install -r requirements.txt"
        exit 1
    fi
fi

echo "✅ 依赖检查完成"
echo ""
echo "🚀 启动应用..."
echo "📱 请在浏览器中访问: http://localhost:8080"
echo "⏹️  按 Ctrl+C 停止应用"
echo ""

# 启动应用
python3 app.py
