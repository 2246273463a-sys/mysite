# Vercel部署指南

## 🚀 快速部署

### 1. 准备工作
```bash
# 确保已安装Node.js
node --version

# 安装Vercel CLI
npm install -g vercel
```

### 2. 部署步骤
```bash
# 1. 运行部署脚本
chmod +x deploy.sh
./deploy.sh

# 2. 或者手动部署
vercel --prod
```

### 3. 配置环境变量
在Vercel后台设置：
- `DATABASE_URL`: 数据库连接（可选，默认使用SQLite）
- `SECRET_KEY`: 安全密钥

## 📁 项目结构
```
mysite/
├── api/
│   └── index.py          # Vercel入口文件
├── templates/             # HTML模板
├── static/               # 静态文件
├── app.py                # Flask主应用
├── requirements.txt      # Python依赖
├── vercel.json          # Vercel配置
├── package.json         # Node.js配置
└── deploy.sh            # 部署脚本
```

## 🔧 本地测试
```bash
# 安装依赖
pip install -r requirements.txt
npm install

# 本地运行
vercel dev
```

## 🌐 访问地址
部署完成后，你的应用将在以下地址可访问：
- `https://your-project.vercel.app`
- 所有设备都可以访问！

## ⚠️ 注意事项
1. Vercel是serverless，每次请求冷启动约1-2秒
2. 免费版有函数执行时间限制（10秒）
3. 数据库建议使用外部服务（如Supabase、PlanetScale）

## 🎯 优势
- ✅ 完全免费
- ✅ 永不休眠
- ✅ 全球CDN
- ✅ 自动HTTPS
- ✅ 自定义域名支持