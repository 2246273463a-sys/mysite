#!/bin/bash

echo "=== Vercel部署脚本 ==="

# 1. 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 请先安装Node.js"
    exit 1
fi

# 2. 安装Vercel CLI
echo "📦 安装Vercel CLI..."
npm install -g vercel

# 3. 安装项目依赖
echo "📦 安装项目依赖..."
npm install

# 4. 检查Python依赖
echo "🐍 检查Python依赖..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt已准备"
else
    echo "❌ requirements.txt不存在"
    exit 1
fi

# 5. 创建必要目录
echo "📁 创建目录结构..."
mkdir -p api templates static

# 6. 检查关键文件
echo "🔍 检查关键文件..."
files=("vercel.json" "api/index.py" "app.py" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 缺失"
        exit 1
    fi
done

# 7. 部署到Vercel
echo "🚀 开始部署..."
vercel --prod

echo "✅ 部署完成！"
echo "📝 记住要在Vercel后台设置环境变量"