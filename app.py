import os
import json
import re
import html
import logging
from datetime import datetime
from threading import Lock
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import sqlalchemy as sa
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

# 配置日志 - 移除文件日志，只保留控制台输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

# Vercel优化CORS配置 - 允许所有域名
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})

# 安全配置 - 使用环境变量或动态生成
app.secret_key = os.environ.get('SECRET_KEY', hashlib.sha256(os.urandom(32)).hexdigest())
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "wiki_enhanced.db")}')
# 云电脑优化的数据库配置
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 2,  # 进一步减小连接池
    'pool_recycle': 180,  # 3分钟回收连接
    'pool_pre_ping': True,
    'max_overflow': 3,  # 减少溢出连接
    'pool_timeout': 30  # 连接超时时间
}
app.config['JSON_AS_ASCII'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # HTTP环境设为False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制

db = SQLAlchemy(app)

# ========== 数据模型 ==========
class Node(db.Model):
    __tablename__ = 'node'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    type = db.Column(db.String(20), default='note', index=True)
    usage = db.Column(db.Text, default='')
    code_snippet = db.Column(db.Text, default='')
    custom_modules = db.Column(db.Text, default='[]')
    is_expanded = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(500), default='')
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, index=True)
    
    # 修正关系定义，避免递归问题
    children = db.relationship('Node', 
                              backref=db.backref('parent', remote_side=[id]),
                              cascade="all, delete-orphan",
                              lazy='noload')  # 改为 noload，避免自动加载

    def to_dict_simple(self):
        """快速转换，不包含子节点"""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'title': self.title,
            'type': self.type,
            'usage': self.usage[:200] if self.usage else '',
            'code_snippet': self.code_snippet[:200] if self.code_snippet else '',
            'custom_modules': json.loads(self.custom_modules) if self.custom_modules else [],
            'is_expanded': self.is_expanded,
            'tags': self.tags.split(',') if self.tags else [],
            'is_favorite': self.is_favorite,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict_with_children(self, max_depth=3, current_depth=0):
        """带子节点的转换，有深度限制防止无限递归"""
        if current_depth >= max_depth:
            return self.to_dict_simple()
            
        result = self.to_dict_simple()
        # 手动查询子节点，避免递归问题
        children = Node.query.filter_by(parent_id=self.id).order_by(Node.title).all()
        result['children'] = [
            child.to_dict_with_children(max_depth, current_depth + 1) 
            for child in children
        ]
        return result

class History(db.Model):
    __tablename__ = 'history'
    
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)

# 创建索引
def create_indexes():
    """手动创建索引，提高查询性能"""
    inspector = sa.inspect(db.engine)
    existing_indexes = inspector.get_indexes('node')
    index_names = [idx['name'] for idx in existing_indexes]
    
    # 为频繁查询的字段创建索引
    indexes_to_create = [
        ('idx_node_parent_id', Node.parent_id),
        ('idx_node_title', Node.title),
        ('idx_node_type', Node.type),
        ('idx_node_favorite', Node.is_favorite),
        ('idx_node_updated', Node.updated_at),
        ('idx_node_tags', Node.tags)
    ]
    
    for idx_name, column in indexes_to_create:
        if idx_name not in index_names:
            try:
                idx = sa.Index(idx_name, column)
                idx.create(bind=db.engine)
                app.logger.info(f"创建索引: {idx_name}")
            except Exception as e:
                app.logger.warning(f"创建索引失败 {idx_name}: {e}")

# ========== 辅助函数 ==========
def is_descendant(parent_id, child_id):
    """检查是否子节点，使用迭代避免递归栈溢出"""
    if parent_id == child_id:
        return True
    
    # 使用循环代替递归
    current_id = child_id
    visited = set()
    
    while current_id:
        if current_id in visited:
            break  # 防止循环引用
        
        visited.add(current_id)
        node = Node.query.get(current_id)
        if not node or not node.parent_id:
            break
        
        if node.parent_id == parent_id:
            return True
        
        current_id = node.parent_id
    
    return False

def escape_html(text):
    """安全的HTML转义"""
    if text is None:
        return ''
    return html.escape(str(text))

def sanitize_input(text):
    """输入内容清理，防止XSS"""
    if text is None:
        return ''
    
    # 移除危险HTML标签和属性
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
    dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur']
    
    cleaned = html.escape(str(text))
    
    # 移除危险标签
    for tag in dangerous_tags:
        pattern = f'<{tag}[^>]*>.*?</{tag}>'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    return cleaned

def validate_node_title(title):
    """验证节点标题"""
    if not title or not isinstance(title, str):
        return False, "标题不能为空"
    
    title = title.strip()
    if len(title) < 1:
        return False, "标题至少需要1个字符"
    if len(title) > 200:
        return False, "标题不能超过200个字符"
    
    # 检查非法字符
    if any(char in title for char in ['<', '>', '&', '"', "'", '\\', '/', '|', '?', '*']):
        return False, "标题包含非法字符"
    
    return True, title

def safe_json_loads(json_str, default=None):
    """安全的JSON解析"""
    if default is None:
        default = []
    
    try:
        if not json_str or json_str.strip() == '':
            return default
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON解析失败: {e}, 原始数据: {json_str[:100]}")
        return default

# 错误处理装饰器
def handle_errors(f):
    """统一的错误处理装饰器"""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API错误 {request.path}: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500, 
                'msg': '服务器内部错误，请稍后重试',
                'error_id': hashlib.md5(str(e).encode()).hexdigest()[:8]
            }), 500
    return wrapper

def highlight_text(text, keyword):
    """文本高亮，性能优化版本"""
    if not text or not keyword:
        return escape_html(text) if text else ''
    
    try:
        # 快速检查是否包含关键词
        if keyword.lower() not in text.lower():
            return escape_html(text)
        
        # 只处理前500个字符，提高性能
        text_to_process = text[:500] + ('...' if len(text) > 500 else '')
        escaped_text = escape_html(text_to_process)
        escaped_keyword = escape_html(keyword)
        
        pattern = re.compile(re.escape(escaped_keyword), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<span class="search-highlight">{m.group(0)}</span>',
            escaped_text
        )
        
        # 如果截断了，加上省略号
        if len(text) > 500:
            result += '...'
            
        return result
    except Exception as e:
        app.logger.error(f"高亮文本失败: {e}")
        return escape_html(text[:500]) + ('...' if len(text) > 500 else '')

# ========== 缓存优化 ==========
node_cache = {}
cache_lock = Lock()
CACHE_TIMEOUT = 5  # 缓存5秒

def get_cached_node(node_id):
    """获取缓存的节点"""
    with cache_lock:
        if node_id in node_cache:
            data, timestamp = node_cache[node_id]
            if (datetime.now() - timestamp).total_seconds() < CACHE_TIMEOUT:
                return data
        return None

def set_cached_node(node_id, data):
    """设置节点缓存"""
    with cache_lock:
        node_cache[node_id] = (data, datetime.now())
        # 限制缓存大小
        if len(node_cache) > 100:
            # 删除最旧的缓存
            oldest = min(node_cache.keys(), key=lambda k: node_cache[k][1])
            del node_cache[oldest]

def clear_node_cache(node_id=None):
    """清除缓存"""
    with cache_lock:
        if node_id:
            if node_id in node_cache:
                del node_cache[node_id]
        else:
            node_cache.clear()

# ========== 安全头部 ==========
@app.after_request
def apply_security_headers(response):
    """安全头部设置"""
    # 移除可能冲突的头部
    headers_to_remove = ['Pragma', 'X-Frame-Options', 'X-XSS-Protection']
    for header in headers_to_remove:
        if header in response.headers:
            del response.headers[header]
    
    # 设置CSP
    csp_policy = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none';"
    response.headers['Content-Security-Policy'] = csp_policy
    
    # 缓存控制
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
    else:
        response.headers['Cache-Control'] = 'no-cache'
    
    # 字符集
    if 'Content-Type' in response.headers and 'text/html' in response.headers['Content-Type']:
        if 'charset=' not in response.headers['Content-Type']:
            response.headers['Content-Type'] += '; charset=utf-8'
    
    return response

# ========== 路由 ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ========== API 接口 ==========
@app.route('/api/tree')
def get_tree():
    """获取树形结构 - 优化版本"""
    try:
        # 尝试从缓存获取
        cached = get_cached_node('tree')
        if cached:
            return jsonify({'code': 200, 'data': cached})
        
        # 批量查询所有节点，避免N+1
        all_nodes = Node.query.all()
        
        # 构建节点映射
        nodes_by_id = {}
        for node in all_nodes:
            nodes_by_id[node.id] = node
        
        # 构建树结构
        tree = []
        for node in all_nodes:
            if node.parent_id is None:
                tree.append(build_tree_node(node, nodes_by_id))
        
        # 缓存结果
        set_cached_node('tree', tree)
        
        return jsonify({'code': 200, 'data': tree})
    except Exception as e:
        app.logger.error(f"获取树形结构失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

def build_tree_node(node, nodes_by_id, depth=0):
    """递归构建树节点，有深度限制"""
    if depth > 10:  # 防止无限递归
        return node.to_dict_simple()
    
    result = node.to_dict_simple()
    
    # 查找子节点
    children = []
    for child_id, child_node in nodes_by_id.items():
        if child_node.parent_id == node.id:
            children.append(build_tree_node(child_node, nodes_by_id, depth + 1))
    
    result['children'] = children
    return result

@app.route('/api/folder/<int:fid>')
def get_folder(fid):
    """获取文件夹内容 - 优化版本"""
    try:
        cache_key = f'folder_{fid}'
        cached = get_cached_node(cache_key)
        if cached:
            return jsonify({'code': 200, 'data': cached})
        
        if fid == 0:
            nodes = Node.query.filter_by(parent_id=None).all()
        else:
            nodes = Node.query.filter_by(parent_id=fid).all()
        
        # 只返回必要信息，不递归查询
        result = [n.to_dict_simple() for n in nodes]
        
        set_cached_node(cache_key, result)
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        app.logger.error(f"获取文件夹失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/node/<int:nid>')
def get_node(nid):
    """获取单个节点 - 优化版本"""
    try:
        cached = get_cached_node(f'node_{nid}')
        if cached:
            return jsonify({'code': 200, 'data': cached})
        
        node = Node.query.get(nid)
        if not node:
            return jsonify({'code': 404, 'msg': '节点不存在'}), 404
        
        result = node.to_dict_with_children(max_depth=1)  # 只获取一层子节点
        set_cached_node(f'node_{nid}', result)
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        app.logger.error(f"获取节点失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/search')
def search():
    """搜索 - 优化版本"""
    try:
        keyword = request.args.get('q', '').strip()
        if not keyword or len(keyword) < 2:
            return jsonify({'code': 200, 'data': []})

        # 使用数据库索引优化搜索
        results = []
        
        # 分字段搜索，利用索引
        # 1. 标题搜索 (最高权重)
        title_matches = Node.query.filter(
            Node.title.ilike(f'%{keyword}%')
        ).limit(50).all()
        
        for node in title_matches:
            results.append(build_search_result(node, keyword, 'title', 100))
        
        # 2. 标签搜索 (中等权重)
        tag_matches = Node.query.filter(
            Node.tags.ilike(f'%{keyword}%')
        ).limit(30).all()
        
        for node in tag_matches:
            if node.id not in [r['id'] for r in results]:  # 避免重复
                results.append(build_search_result(node, keyword, 'tags', 80))
        
        # 3. 描述搜索 (低权重)
        if len(results) < 20:  # 如果结果不够，再搜索描述
            usage_matches = Node.query.filter(
                Node.usage.ilike(f'%{keyword}%')
            ).limit(20).all()
            
            for node in usage_matches:
                if node.id not in [r['id'] for r in results]:
                    results.append(build_search_result(node, keyword, 'usage', 60))
        
        # 去重并排序
        unique_results = {}
        for result in results:
            if result['id'] not in unique_results:
                unique_results[result['id']] = result
            elif result['relevance'] > unique_results[result['id']]['relevance']:
                unique_results[result['id']] = result
        
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x['relevance'], reverse=True)
        
        return jsonify({'code': 200, 'data': final_results[:50]})
        
    except Exception as e:
        app.logger.error(f"搜索失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '搜索失败'}), 500

def build_search_result(node, keyword, field, base_relevance):
    """构建搜索结果"""
    # 获取面包屑（有限深度）
    breadcrumbs = []
    current = node
    depth = 0
    while current and depth < 5:  # 限制深度
        breadcrumbs.insert(0, {
            'id': current.id,
            'title': current.title,
            'type': current.type
        })
        if current.parent:
            current = current.parent
        else:
            break
        depth += 1
    
    # 构建预览
    preview = ''
    if field == 'title':
        preview = highlight_text(node.title, keyword)
    elif field == 'usage' and node.usage:
        preview = highlight_text(node.usage[:150], keyword)
    elif field == 'tags' and node.tags:
        preview = highlight_text(node.tags, keyword)
    elif node.usage:
        preview = highlight_text(node.usage[:150], keyword)
    
    return {
        'id': node.id,
        'title': node.title,
        'type': node.type,
        'relevance': base_relevance,
        'preview': preview,
        'parent_id': node.parent_id,
        'updated_at': node.updated_at.isoformat() if node.updated_at else None,
        'breadcrumbs': breadcrumbs,
        'match_details': [{'field': field, 'content': preview}]
    }

@app.route('/api/breadcrumbs/<int:nid>')
def get_breadcrumbs_api(nid):
    """获取面包屑 - 优化版本"""
    try:
        crumbs = []
        node = Node.query.get(nid)
        if not node:
            return jsonify({'code': 404, 'msg': '节点不存在'}), 404
        
        # 使用循环代替递归
        current = node
        max_depth = 10  # 防止循环引用
        while current and len(crumbs) < max_depth:
            crumbs.insert(0, {
                'id': current.id, 
                'title': current.title, 
                'type': current.type
            })
            if current.parent:
                current = current.parent
            else:
                break
        
        return jsonify({'code': 200, 'data': crumbs})
    except Exception as e:
        app.logger.error(f"获取面包屑失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/save', methods=['POST'])
@handle_errors
def save():
    """保存节点 - 安全优化版本"""
    # 检查请求大小
    content_length = request.content_length
    if content_length and content_length > 10 * 1024 * 1024:  # 10MB限制
        return jsonify({'code': 413, 'msg': '请求数据过大'}), 413
    
    data = request.json
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据为空'}), 400

    # 验证和清理标题
    title_valid, title_result = validate_node_title(data.get('title', ''))
    if not title_valid:
        return jsonify({'code': 400, 'msg': title_result}), 400
    clean_title = title_result

    # 验证节点类型
    node_type = data.get('type', 'note')
    if node_type not in ['folder', 'note']:
        return jsonify({'code': 400, 'msg': '无效的节点类型'}), 400

    # 安全处理自定义模块
    custom_modules = data.get('custom_modules', [])
    if not isinstance(custom_modules, list):
        custom_modules = []
    
    # 限制模块数量和大小
    if len(custom_modules) > 50:
        return jsonify({'code': 400, 'msg': '自定义模块数量不能超过50个'}), 400
    
    try:
        custom_json = json.dumps(custom_modules[:50], ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError) as e:
        logger.warning(f"自定义模块JSON序列化失败: {e}")
        custom_json = '[]'

    # 验证父节点ID
    pid = data.get('parent_id')
    if pid in [0, "", None, "None"]:
        pid = None
    else:
        try:
            pid = int(pid)
            if pid and pid > 0:
                parent_node = Node.query.get(pid)
                if not parent_node or parent_node.type != 'folder':
                    logger.warning(f"无效的父节点ID: {pid}")
                    pid = None
        except (ValueError, TypeError):
            pid = None

    node_id = data.get('id')
    
    with db.session.begin_nested():  # 使用嵌套事务
        if node_id:
            node = Node.query.get(node_id)
            if not node:
                return jsonify({'code': 404, 'msg': '节点不存在'}), 404

            # 检查是否真的需要保存历史记录
            should_save_history = (
                node.type == 'note' and 
                (node.title != clean_title or
                 node.code_snippet != sanitize_input(data.get('code_snippet', '')) or
                 node.usage != sanitize_input(data.get('usage', '')))
            )
            
            if should_save_history:
                history = History(
                    note_id=node.id,
                    title=node.title,
                    content=json.dumps(node.to_dict_simple(), ensure_ascii=False)
                )
                db.session.add(history)

            # 更新节点数据
            node.title = clean_title
            node.usage = sanitize_input(data.get('usage', ''))
            node.code_snippet = sanitize_input(data.get('code_snippet', ''))
            node.parent_id = pid
            node.is_expanded = bool(data.get('is_expanded', node.is_expanded))
            
            # 处理标签
            tags = data.get('tags', [])
            if isinstance(tags, list):
                cleaned_tags = [str(tag).strip() for tag in tags if str(tag).strip() and len(str(tag)) <= 50]
                node.tags = ','.join(cleaned_tags[:20])  # 最多20个标签
            elif isinstance(tags, str):
                node.tags = tags[:500]  # 限制长度
            
            node.is_favorite = bool(data.get('is_favorite', node.is_favorite))
            node.custom_modules = custom_json
            node.updated_at = datetime.now()
            
            db.session.flush()  # 立即刷新，但不提交
            
        else:
            # 创建新节点
            node = Node(
                title=clean_title,
                type=node_type,
                parent_id=pid,
                usage=sanitize_input(data.get('usage', '')),
                code_snippet=sanitize_input(data.get('code_snippet', '')),
                custom_modules=custom_json,
                tags=','.join([str(tag).strip() for tag in data.get('tags', []) if str(tag).strip()][:20]),
                is_favorite=bool(data.get('is_favorite', False))
            )
            db.session.add(node)
            db.session.flush()  # 获取ID
    
    # 清除相关缓存
    clear_node_cache()
    
    return jsonify({
        'code': 200, 
        'data': {
            'id': node.id,
            'title': node.title,
            'type': node.type
        }
    })

@app.route('/api/delete', methods=['POST'])
def delete_nodes():
    """删除节点 - 优化版本"""
    try:
        data = request.json
        if not data:
            return jsonify({'code': 400, 'msg': '请求数据为空'}), 400

        ids = data.get('ids', [])
        if not ids:
            return jsonify({'code': 400, 'msg': '没有选择项目'})

        # 验证所有节点存在
        nodes_to_delete = []
        for node_id in ids:
            try:
                node_id = int(node_id)
                if node_id == 0:  # 防止删除根目录
                    return jsonify({'code': 400, 'msg': '根目录不能被删除'}), 400
                    
                node = Node.query.get(node_id)
                if not node:
                    return jsonify({'code': 404, 'msg': f'节点不存在: {node_id}'}), 404
                nodes_to_delete.append(node)
            except ValueError:
                return jsonify({'code': 400, 'msg': f'无效的节点ID: {node_id}'}), 400

        # 批量删除
        try:
            for node in nodes_to_delete:
                db.session.delete(node)
            
            db.session.commit()
            
            # 清除缓存
            clear_node_cache()
            
            return jsonify({'code': 200, 'msg': '删除成功'})
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        app.logger.error(f"删除节点失败: {str(e)}")
        return jsonify({'code': 500, 'msg': f'删除失败: {str(e)}'}), 500

@app.route('/api/move', methods=['POST'])
def move_node():
    """移动节点 - 优化版本"""
    try:
        data = request.json
        if not data:
            return jsonify({'code': 400, 'msg': '请求数据为空'}), 400

        item_id = data.get('itemId')
        target_id = data.get('targetId')
        
        if not item_id:
            return jsonify({'code': 400, 'msg': '缺少要移动的项目ID'}), 400
        
        try:
            item_id = int(item_id)
            if item_id == 0:  # 防止移动根目录
                return jsonify({'code': 400, 'msg': '根目录不能被移动'}), 400
                
            if target_id is not None:
                target_id = int(target_id)
                if target_id == 0:
                    target_id = None
        except ValueError:
            return jsonify({'code': 400, 'msg': 'ID格式错误'}), 400
        
        # 开始事务
        with db.session.begin_nested():
            node_to_move = Node.query.get(item_id)
            if not node_to_move:
                return jsonify({'code': 404, 'msg': '要移动的节点不存在'}), 404
            
            if target_id is not None:
                target_node = Node.query.get(target_id)
                if not target_node:
                    return jsonify({'code': 400, 'msg': '目标节点不存在'}), 400
                
                if target_node.type != 'folder':
                    return jsonify({'code': 400, 'msg': '目标不是有效的文件夹'}), 400
                
                if is_descendant(target_id, item_id):
                    return jsonify({'code': 400, 'msg': '不能将文件夹移动到自己的子文件夹中'}), 400
            
            # 检查是否真的需要移动
            if node_to_move.parent_id == target_id:
                return jsonify({'code': 200, 'msg': '节点已在目标位置'})
            
            node_to_move.parent_id = target_id
            node_to_move.updated_at = datetime.now()
        
        # 清除缓存
        clear_node_cache()
        
        return jsonify({
            'code': 200, 
            'msg': '移动成功',
            'data': node_to_move.to_dict_simple()
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"移动节点错误: {str(e)}")
        return jsonify({'code': 500, 'msg': f'移动失败: {str(e)}'}), 500

@app.route('/api/favorites')
def get_favorites():
    """获取收藏列表 - 优化版本"""
    try:
        favorites = Node.query.filter_by(is_favorite=True).limit(50).all()
        return jsonify({'code': 200, 'data': [{
            'id': n.id,
            'title': n.title,
            'type': n.type,
            'parent_id': n.parent_id
        } for n in favorites]})
    except Exception as e:
        app.logger.error(f"获取收藏列表失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/recent')
def get_recent():
    """获取最近编辑 - 优化版本"""
    try:
        recent = Node.query.filter_by(type='note')\
                          .order_by(Node.updated_at.desc())\
                          .limit(10).all()
        return jsonify({'code': 200, 'data': [{
            'id': n.id,
            'title': n.title,
            'type': n.type,
            'updated_at': n.updated_at.isoformat() if n.updated_at else None,
            'usage': n.usage[:100] + '...' if n.usage and len(n.usage) > 100 else (n.usage or '')
        } for n in recent]})
    except Exception as e:
        app.logger.error(f"获取最近编辑失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """切换收藏状态 - 优化版本"""
    try:
        data = request.json
        node_id = data.get('id')
        
        if not node_id:
            return jsonify({'code': 400, 'msg': '缺少节点ID'}), 400
        
        node = Node.query.get(node_id)
        if not node:
            return jsonify({'code': 404, 'msg': '节点不存在'}), 404
        
        node.is_favorite = not node.is_favorite
        node.updated_at = datetime.now()
        db.session.commit()
        
        # 清除缓存
        clear_node_cache()
        
        return jsonify({
            'code': 200,
            'msg': '收藏状态已更新',
            'data': {
                'id': node.id,
                'is_favorite': node.is_favorite
            }
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"切换收藏状态失败: {str(e)}")
        return jsonify({'code': 500, 'msg': f'操作失败: {str(e)}'}), 500

@app.route('/api/history/<int:note_id>')
def get_history(note_id):
    """获取历史记录 - 优化版本"""
    try:
        history = History.query.filter_by(note_id=note_id)\
                              .order_by(History.created_at.desc())\
                              .limit(20).all()
        return jsonify({'code': 200, 'data': [{
            'id': h.id,
            'title': h.title,
            'content': json.loads(h.content) if h.content else {},
            'created_at': h.created_at.isoformat() if h.created_at else None
        } for h in history]})
    except Exception as e:
        app.logger.error(f"获取历史记录失败: {str(e)}")
        return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

@app.route('/api/restore/<int:history_id>')
def restore_history(history_id):
    """恢复历史记录 - 优化版本"""
    try:
        history = History.query.get(history_id)
        if not history:
            return jsonify({'code': 404, 'msg': '历史记录不存在'}), 404
        
        note = Node.query.get(history.note_id)
        if not note:
            return jsonify({'code': 404, 'msg': '笔记不存在'}), 404
        
        # 开始事务
        with db.session.begin_nested():
            # 保存当前状态到历史记录
            new_history = History(
                note_id=note.id,
                title=note.title,
                content=json.dumps(note.to_dict_simple(), ensure_ascii=False)
            )
            db.session.add(new_history)
            
            # 恢复旧数据
            if history.content:
                try:
                    old_data = json.loads(history.content)
                    note.title = old_data.get('title', note.title)
                    note.usage = old_data.get('usage', note.usage)
                    note.code_snippet = old_data.get('code_snippet', note.code_snippet)
                    
                    tags = old_data.get('tags', [])
                    if isinstance(tags, list):
                        note.tags = ','.join([str(tag).strip() for tag in tags if str(tag).strip()])
                    elif isinstance(tags, str):
                        note.tags = tags
                    
                    custom_modules = old_data.get('custom_modules', [])
                    note.custom_modules = json.dumps(custom_modules, ensure_ascii=False)
                    
                    note.updated_at = datetime.now()
                except json.JSONDecodeError:
                    return jsonify({'code': 500, 'msg': '历史记录数据格式错误'}), 500
        
        # 清除缓存
        clear_node_cache()
        
        return jsonify({'code': 200, 'msg': '恢复成功', 'data': note.to_dict_simple()})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"恢复历史记录失败: {str(e)}")
        return jsonify({'code': 500, 'msg': f'恢复失败: {str(e)}'}), 500

# ========== 初始化数据 ==========
def init_data():
    with app.app_context():
        db.create_all()
        create_indexes()  # 创建索引
        
        # 确保至少有一个根目录存在
        if not Node.query.first():
            root_folder = Node(
                title="根目录", 
                type="folder", 
                is_expanded=True,
                tags="系统,根目录"
            )
            db.session.add(root_folder)
            db.session.commit()
            
            app.logger.info("数据库初始化完成，创建根目录")

# ========== 启动应用 ==========
if __name__ == '__main__':
    init_data()
    # 云电脑优化配置
    app.run(
        host='127.0.0.1',  # 只监听本地，减少网络开销
        port=5000,
        debug=False,
        threaded=True,
        processes=1,  # 限制进程数
        use_reloader=False  # 禁用重载减少资源消耗
    )