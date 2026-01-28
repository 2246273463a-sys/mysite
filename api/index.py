import os
import sys
from flask import Flask

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 直接导入应用实例
from app import app

# Vercel需要导出handler
handler = app
