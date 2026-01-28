from flask import Flask
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入你的Flask应用
from app import app, init_data

# 初始化数据库（仅首次部署时需要）
try:
    with app.app_context():
        init_data()
except Exception as e:
    print(f"初始化警告: {e}")

# Vercel需要导出handler
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.debug = False

# Vercel需要这个导出
handler = app
