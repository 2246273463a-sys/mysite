# PythonAnywhere 部署指南

## 部署步骤

### 1. 准备工作
```bash
# 安装依赖
pip install -r requirements.txt

# 测试应用
python simple_test.py
```

### 2. PythonAnywhere配置

#### 2.1 创建Web应用
1. 登录PythonAnywhere
2. 进入"Web"页面
3. 点击"Add a new web app"
4. 选择"Manual Configuration"
5. 选择Python版本（推荐3.9+）

#### 2.2 配置虚拟环境
```bash
# 在PythonAnywhere Bash中运行
cd ~/mysite
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2.3 配置WSGI文件
在Web页面，编辑WSGI配置文件：
```python
import os
import sys

# 添加项目路径
project_home = u'/home/yourusername/mysite'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# 导入应用
from app import app as application

# 设置环境变量
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'sqlite:////home/yourusername/mysite/wiki_enhanced.db'
```

#### 2.4 配置静态文件
在Web页面设置静态文件路径：
```
URL: /static
Directory: /home/yourusername/mysite/static
```

### 3. 文件上传
```bash
# 上传所有文件到 ~/mysite/
# 确保包含：
# - app.py
# - templates/index.html
# - static/ 目录
# - requirements.txt
```

### 4. 数据库初始化
```bash
# 在PythonAnywhere Bash中运行
cd ~/mysite
source venv/bin/activate
python -c "from app import init_data; init_data()"
```

### 5. 重启Web应用
在Web页面点击"Reload"按钮

## 风险评估

### 已解决的安全问题：
✅ XSS防护 - 输入验证和HTML转义
✅ SQL注入防护 - SQLAlchemy ORM
✅ 请求大小限制 - 16MB限制
✅ 文件上传安全 - 类型和大小验证

### 性能优化：
✅ 数据库连接池优化
✅ 缓存机制
✅ 虚拟滚动支持
✅ 懒加载图片

### 错误处理：
✅ 统一错误处理装饰器
✅ 详细日志记录
✅ 用户友好的错误信息
✅ 错误追踪ID

## 部署后测试

### 1. 基本功能测试
- 访问主页
- 创建文件夹和笔记
- 搜索功能
- 代码高亮

### 2. 安全测试
- 尝试XSS攻击
- SQL注入测试
- 文件上传限制

### 3. 性能测试
- 页面加载速度
- 大量数据处理
- 内存使用情况

## 监控和维护

### 日志查看
```bash
# 查看应用日志
tail -f /var/log/yourusername/error.log

# 查看应用日志
tail -f ~/mysite/app.log
```

### 定期维护
- 清理过期缓存
- 备份数据库
- 更新依赖包
- 监控磁盘空间

## 故障排查

### 常见问题：
1. **500错误** - 检查日志，通常是导入错误
2. **静态文件404** - 检查静态文件路径配置
3. **数据库错误** - 检查数据库文件权限
4. **内存不足** - 调整Gunicorn workers数量

### 联系支持：
如遇问题，可查看日志文件或联系PythonAnywhere技术支持。

## 部署检查清单

- [ ] 所有文件已上传
- [ ] 依赖已安装
- [ ] WSGI配置正确
- [ ] 静态文件路径正确
- [ ] 数据库已初始化
- [ ] 环境变量已设置
- [ ] Web应用已重启
- [ ] 基本功能测试通过
- [ ] 安全测试通过
- [ ] 性能测试通过

完成以上步骤后，应用即可在PythonAnywhere上正常运行！