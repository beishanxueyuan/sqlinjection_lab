from flask import Flask, request, jsonify
import urllib.parse
import json
import db
import time
import sys

app = Flask(__name__)

def initialize_dbs():
    """初始化所有数据库。"""
    try:
        print("开始数据库初始化...")
        db.init_databases()
        print("数据库初始化完成")
        return True
    except Exception as e:
        print(f"数据库初始化出错: {e}")
        return False


# --- Run initialization synchronously before starting the server ---
print("正在初始化数据库...")
initialize_dbs()


# --- Helper to extract input ---
def get_input(param_name):
    # 1. GET
    if request.method == 'GET':
        # 处理普通GET参数如?id=1
        value = request.args.get(param_name)
        if value is not None:
            return value
        # 处理GET请求中的URL编码JSON参数如?data=%7B%22id%22%3A%221%22%7D
        data_param = request.args.get('data')
        if data_param:
            try:
                # 首先尝试解码URL编码的参数
                decoded_data = urllib.parse.unquote(data_param)
                data = json.loads(decoded_data)
                if param_name in data:
                    return data[param_name]
            except Exception as e:
                print(f"Error parsing GET URL encoded JSON: {e}") # Log error
                pass
    
    # 2. POST Form
    if request.form.get(param_name):
        return request.form.get(param_name)
    
    # 3. JSON
    if request.is_json:
        data = request.get_json()
        # 处理嵌套 {"data": {"id": "1"}} - data是对象
        if 'data' in data and isinstance(data['data'], dict) and param_name in data['data']:
            return data['data'][param_name]
        # 处理嵌套 {"data": "{\"id\":\"1\"}"} - data是JSON字符串
        if 'data' in data and isinstance(data['data'], str):
            try:
                nested_data = json.loads(data['data'])
                if param_name in nested_data:
                    return nested_data[param_name]
            except Exception as e:
                print(f"Error parsing nested JSON string: {e}") # Log error
                pass
        # 处理普通JSON {"id": "1"}
        if param_name in data:
            return data[param_name]
            
    # 4. POST URL Encoded JSON (data=%7B%22id%22%3A%221%22%7D)
    if request.form.get('data'):
        try:
            # Decode if it looks like JSON string
            json_str = request.form.get('data')
            data = json.loads(json_str)
            if param_name in data:
                return data[param_name]
        except Exception as e:
            print(f"Error parsing URL encoded JSON: {e}") # Log error
            pass
            
    return None

# --- Generic helper for DB queries ---
def execute_query(get_conn_func, query_template, params_dict, db_type_name):
    """
    Executes a query against a database.
    
    Args:
        get_conn_func: Function to get database connection (e.g., db.get_mysql_connection).
        query_template: String template for the SQL query (e.g., "SELECT * FROM users WHERE id = {uid}").
                          Assumes placeholders are replaced using format().
        params_dict: Dictionary containing parameters extracted via get_input.
        db_type_name: Name of the database type for error messages (e.g., "MySQL").

    Returns:
        Tuple (success: bool, response_data: dict, status_code: int)
    """
    # 尝试获取连接
    try:
        conn = get_conn_func()
        if conn is None:
            error_msg = f"无法连接到 {db_type_name} 数据库"
            print(error_msg)
            query = query_template.format(**params_dict)
            return False, {"query": query, "error": error_msg}, 500

        cursor = None
        try:
            # 格式化查询（假设故意存在漏洞用于实验）
            # 注意：实际应用应该使用参数化查询！
            query = query_template.format(**params_dict)
            
            if db_type_name.lower() in ['mysql', 'postgres', 'postgresql', 'oracle']:
                 cursor = conn.cursor()
                 cursor.execute(query)
                 result = cursor.fetchall()
            elif db_type_name.lower() == 'clickhouse':
                # 假设ClickHouse客户端execute直接返回结果
                result = conn.execute(query)
            else:
                 raise ValueError(f"不支持的数据库类型: {db_type_name}")

            return True, {"query": query, "result": result}, 200

        except Exception as e:
            error_msg = f"数据库查询失败: {str(e)}"
            print(f"{db_type_name} 错误: {error_msg}")
            query = query_template.format(**params_dict)
            return False, {"query": query, "error": error_msg}, 500
        finally:
            # 关闭资源
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    if hasattr(conn, 'close'):
                       conn.close()
                except Exception as e:
                    print(f"关闭 {db_type_name} 连接时出错: {e}")
    except Exception as e:
        # 捕获所有异常，确保应用不会崩溃
        print(f"查询过程中发生异常: {e}")
        query = query_template.format(**params_dict)
        return False, {"query": query, "error": str(e)}, 500


# --- MySQL Endpoints ---

@app.route('/mysql/char', methods=['GET', 'POST'])
def mysql_char():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_mysql_connection,
        "SELECT * FROM users WHERE id = '{uid}'", # Intentionally vulnerable
        {'uid': uid},
        "MySQL"
    )
    return jsonify(data), status_code

@app.route('/mysql/int', methods=['GET', 'POST'])
def mysql_int():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_mysql_connection,
        "SELECT * FROM users WHERE id = {uid}", # Intentionally vulnerable
        {'uid': uid},
        "MySQL"
    )
    return jsonify(data), status_code

@app.route('/mysql/like', methods=['GET', 'POST'])
def mysql_like():
    username = get_input('username')
    if not username: return jsonify({"error": "Missing username parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_mysql_connection,
        "SELECT * FROM users WHERE username LIKE '%{username}%'", # Intentionally vulnerable
        {'username': username},
        "MySQL"
    )
    return jsonify(data), status_code

@app.route('/mysql/orderby', methods=['GET', 'POST'])
def mysql_orderby():
    col = get_input('col')
    if not col: return jsonify({"error": "Missing col parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_mysql_connection,
        "SELECT * FROM users ORDER BY {col}", # Intentionally vulnerable
        {'col': col},
        "MySQL"
    )
    return jsonify(data), status_code

# --- PostgreSQL Endpoints ---

@app.route('/postgres/char', methods=['GET', 'POST'])
def postgres_char():
    uid = get_input('id') # Using 'id' for consistency with instructions, though comment suggested username
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_postgres_connection,
        "SELECT * FROM users WHERE id = '{uid}'", # Intentionally vulnerable - using username for char example
        {'uid': uid}, # Note: uid used in template as username value
        "PostgreSQL"
    )
    return jsonify(data), status_code

@app.route('/postgres/int', methods=['GET', 'POST'])
def postgres_int():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_postgres_connection,
        "SELECT * FROM users WHERE id = {uid}", # Intentionally vulnerable
        {'uid': uid},
        "PostgreSQL"
    )
    return jsonify(data), status_code

@app.route('/postgres/like', methods=['GET', 'POST'])
def postgres_like():
    username = get_input('username')
    if not username: return jsonify({"error": "Missing username parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_postgres_connection,
        "SELECT * FROM users WHERE username LIKE '%{username}%'", # Intentionally vulnerable
        {'username': username},
        "PostgreSQL"
    )
    return jsonify(data), status_code

@app.route('/postgres/orderby', methods=['GET', 'POST'])
def postgres_orderby():
    col = get_input('col')
    if not col: return jsonify({"error": "Missing col parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_postgres_connection,
        "SELECT * FROM users ORDER BY {col}", # Intentionally vulnerable
        {'col': col},
        "PostgreSQL"
    )
    return jsonify(data), status_code

# --- ClickHouse Endpoints ---

@app.route('/clickhouse/int', methods=['GET', 'POST'])
def clickhouse_int():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_clickhouse_connection,
        "SELECT * FROM sqli_lab.users WHERE id = {uid}", # Intentionally vulnerable
        {'uid': uid},
        "ClickHouse"
    )
    return jsonify(data), status_code

@app.route('/clickhouse/char', methods=['GET', 'POST'])
def clickhouse_char():
     # Using 'id' param as per table structure implied
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_clickhouse_connection,
        "SELECT * FROM sqli_lab.users WHERE id = '{uid}'", # Intentionally vulnerable
        {'uid': uid},
        "ClickHouse"
    )
    return jsonify(data), status_code

@app.route('/clickhouse/like', methods=['GET', 'POST'])
def clickhouse_like():
    username = get_input('username')
    if not username: return jsonify({"error": "Missing username parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_clickhouse_connection,
        "SELECT * FROM sqli_lab.users WHERE username LIKE '%{username}%'", # Intentionally vulnerable
        {'username': username},
        "ClickHouse"
    )
    return jsonify(data), status_code

@app.route('/clickhouse/orderby', methods=['GET', 'POST'])
def clickhouse_orderby():
    col = get_input('col')
    if not col: return jsonify({"error": "Missing col parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_clickhouse_connection,
        "SELECT * FROM sqli_lab.users ORDER BY {col}", # Intentionally vulnerable
        {'col': col},
        "ClickHouse"
    )
    return jsonify(data), status_code

# --- Oracle Endpoints ---

@app.route('/oracle/char', methods=['GET', 'POST'])
def oracle_char():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_oracle_connection,
        "SELECT * FROM users WHERE id = '{uid}'", # Intentionally vulnerable
        {'uid': uid},
        "Oracle"
    )
    return jsonify(data), status_code

@app.route('/oracle/int', methods=['GET', 'POST'])
def oracle_int():
    uid = get_input('id')
    if not uid: return jsonify({"error": "Missing id parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_oracle_connection,
        "SELECT * FROM users WHERE id = {uid}", # Intentionally vulnerable
        {'uid': uid},
        "Oracle"
    )
    return jsonify(data), status_code

@app.route('/oracle/like', methods=['GET', 'POST'])
def oracle_like():
    username = get_input('username')
    if not username: return jsonify({"error": "Missing username parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_oracle_connection,
        "SELECT * FROM users WHERE username LIKE '%{username}%'", # Intentionally vulnerable
        {'username': username},
        "Oracle"
    )
    return jsonify(data), status_code

@app.route('/oracle/orderby', methods=['GET', 'POST'])
def oracle_orderby():
    col = get_input('col')
    if not col: return jsonify({"error": "Missing col parameter"}), 400
    
    success, data, status_code = execute_query(
        db.get_oracle_connection,
        "SELECT * FROM users ORDER BY {col}", # Intentionally vulnerable
        {'col': col},
        "Oracle"
    )
    return jsonify(data), status_code

# --- Homepage Route ---
@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL 注入实验室</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
        h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; font-family: 'Monaco', 'Consolas', monospace; color: #e83e8c; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; border: 1px solid #ddd; }
        .btn { display: inline-block; background: #3498db; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 0.9em; margin: 5px 0; cursor: pointer; border: none; }
        .btn:hover { background: #2980b9; }
        .btn-run { background: #27ae60; }
        .btn-run:hover { background: #219653; }
        .btn-alt { background: #9b59b6; } /* Purple for URL-encoded */
        .btn-alt:hover { background: #8e44ad; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .endpoint { margin-bottom: 15px; padding: 10px; border-left: 4px solid #3498db; background-color: #f9f9f9; }
        .method { font-weight: bold; color: #27ae60; }
        .param { color: #d35400; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .result-box { margin-top: 10px; padding: 10px; border-radius: 5px; background-color: #e9f7fe; border: 1px solid #bee5eb; white-space: pre-wrap; font-family: 'Monaco', 'Consolas', monospace; font-size: 0.9em; }
        .error-box { background-color: #fce4e4; border: 1px solid #fadbd8; color: #c0392b; }
        .payload-input { width: calc(100% - 22px); padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; font-family: inherit; }
        .payload-section { margin-top: 10px; }
        .tabs { display: flex; margin-bottom: 10px; }
        .tab { padding: 8px 16px; background-color: #e0e0e0; cursor: pointer; border: 1px solid #ccc; border-bottom: none; margin-right: 5px; border-radius: 5px 5px 0 0; }
        .tab.active { background-color: #3498db; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <h1>SQL 注入实验室</h1>
    
    <div class="card" style="background-color: #e8f6f3; border-color: #a3e4d7;">
        <h2>🚀 状态</h2>
        <p>数据库已在启动时完成初始化。</p>
    </div>

    <h2>📚 文档说明</h2>
    <p>本实验提供了针对 4 种不同数据库的易受攻击的接口。所有接口均返回 JSON 格式的数据。</p>
    
    <h3>支持的输入方式</h3>
    <ul>
        <li><strong>GET 请求</strong>: <code>?id=1</code></li>
        <li><strong>GET URL 编码的 JSON</strong>: <code>?data=%7B%22id%22%3A%221%22%7D</code></li>
        <li><strong>POST 表单</strong>: <code>id=1</code></li>
        <li><strong>JSON 数据</strong>: <code>{"id": "1"}</code></li>
        <li><strong>嵌套 JSON 对象</strong>: <code>{"data": {"id": "1"}}</code></li>
        <li><strong>嵌套 JSON 对象(数字型)</strong>: <code>{"data": {"id": 1}}</code></li>
        <li><strong>嵌套 JSON 字符串</strong>: <code>{"data": "{\"id\":\"1\"}"}</code></li>
        <li><strong>URL 编码的 JSON</strong>: <code>data=%7B%22id%22%3A%221%22%7D</code></li>
    </ul>

    <h2>🎯 接口列表</h2>

    <!-- MySQL -->
    <h3>MySQL</h3>
    <table>
        <tr><th>类型</th><th>接口</th><th>参数</th><th>操作</th></tr>
        <tr>
            <td>字符串</td>
            <td><code>/mysql/char</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/mysql/char', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/mysql/char', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/mysql/char', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/mysql/char', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/mysql/char', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/mysql/char', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/mysql/char', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>整数</td>
            <td><code>/mysql/int</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/mysql/int', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/mysql/int', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/mysql/int', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/mysql/int', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/mysql/int', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/mysql/int', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/mysql/int', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Like</td>
            <td><code>/mysql/like</code></td>
            <td>username</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/mysql/like', 'username', 'admin', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/mysql/like', 'username', 'admin', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/mysql/like', 'username', 'admin')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/mysql/like', 'username', 'admin')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/mysql/like', 'username', 'admin')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/mysql/like', 'username', 'admin')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/mysql/like', 'username', 'admin')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Order By</td>
            <td><code>/mysql/orderby</code></td>
            <td>col</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/mysql/orderby', 'col', 'id', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/mysql/orderby', 'col', 'id', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/mysql/orderby', 'col', 'id')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/mysql/orderby', 'col', 'id')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/mysql/orderby', 'col', 'id')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/mysql/orderby', 'col', 'id')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/mysql/orderby', 'col', 'id')">GET URL编码</button>
            </td>
        </tr>
    </table>

    <!-- PostgreSQL -->
    <h3>PostgreSQL</h3>
    <table>
        <tr><th>类型</th><th>接口</th><th>参数</th><th>操作</th></tr>
        <tr>
            <td>字符串</td>
            <td><code>/postgres/char</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/postgres/char', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/postgres/char', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/postgres/char', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/postgres/char', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/postgres/char', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/postgres/char', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/postgres/char', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>整数</td>
            <td><code>/postgres/int</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/postgres/int', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/postgres/int', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/postgres/int', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/postgres/int', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/postgres/int', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/postgres/int', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/postgres/int', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Like</td>
            <td><code>/postgres/like</code></td>
            <td>username</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/postgres/like', 'username', 'admin', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/postgres/like', 'username', 'admin', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/postgres/like', 'username', 'admin')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/postgres/like', 'username', 'admin')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/postgres/like', 'username', 'admin')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/postgres/like', 'username', 'admin')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/postgres/like', 'username', 'admin')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Order By</td>
            <td><code>/postgres/orderby</code></td>
            <td>col</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/postgres/orderby', 'col', 'id', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/postgres/orderby', 'col', 'id', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/postgres/orderby', 'col', 'id')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/postgres/orderby', 'col', 'id')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/postgres/orderby', 'col', 'id')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/postgres/orderby', 'col', 'id')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/postgres/orderby', 'col', 'id')">GET URL编码</button>
            </td>
        </tr>
    </table>

    <!-- ClickHouse -->
    <h3>ClickHouse</h3>
    <table>
        <tr><th>类型</th><th>接口</th><th>参数</th><th>操作</th></tr>
        <tr>
            <td>字符串</td>
            <td><code>/clickhouse/char</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/clickhouse/char', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/clickhouse/char', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/clickhouse/char', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/clickhouse/char', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/clickhouse/char', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/clickhouse/char', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/clickhouse/char', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>整数</td>
            <td><code>/clickhouse/int</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/clickhouse/int', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/clickhouse/int', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/clickhouse/int', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/clickhouse/int', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/clickhouse/int', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/clickhouse/int', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/clickhouse/int', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Like</td>
            <td><code>/clickhouse/like</code></td>
            <td>username</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/clickhouse/like', 'username', 'admin', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/clickhouse/like', 'username', 'admin', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/clickhouse/like', 'username', 'admin')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/clickhouse/like', 'username', 'admin')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/clickhouse/like', 'username', 'admin')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/clickhouse/like', 'username', 'admin')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/clickhouse/like', 'username', 'admin')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Order By</td>
            <td><code>/clickhouse/orderby</code></td>
            <td>col</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/clickhouse/orderby', 'col', 'id', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/clickhouse/orderby', 'col', 'id', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/clickhouse/orderby', 'col', 'id')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/clickhouse/orderby', 'col', 'id')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/clickhouse/orderby', 'col', 'id')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/clickhouse/orderby', 'col', 'id')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/clickhouse/orderby', 'col', 'id')">GET URL编码</button>
            </td>
        </tr>
    </table>

    <!-- Oracle -->
    <h3>Oracle</h3>
    <table>
        <tr><th>类型</th><th>接口</th><th>参数</th><th>操作</th></tr>
        <tr>
            <td>字符串</td>
            <td><code>/oracle/char</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/oracle/char', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/oracle/char', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/oracle/char', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/oracle/char', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/oracle/char', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/oracle/char', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/oracle/char', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>整数</td>
            <td><code>/oracle/int</code></td>
            <td>id</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/oracle/int', 'id', '1', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/oracle/int', 'id', '1', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/oracle/int', 'id', '1')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/oracle/int', 'id', '1')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/oracle/int', 'id', '1')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/oracle/int', 'id', '1')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/oracle/int', 'id', '1')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Like</td>
            <td><code>/oracle/like</code></td>
            <td>username</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/oracle/like', 'username', 'admin', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/oracle/like', 'username', 'admin', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/oracle/like', 'username', 'admin')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/oracle/like', 'username', 'admin')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/oracle/like', 'username', 'admin')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/oracle/like', 'username', 'admin')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/oracle/like', 'username', 'admin')">GET URL编码</button>
            </td>
        </tr>
        <tr>
            <td>Order By</td>
            <td><code>/oracle/orderby</code></td>
            <td>col</td>
            <td>
                <button class="btn btn-run" onclick="runTest('/oracle/orderby', 'col', 'id', 'json')">JSON</button>
                <button class="btn" onclick="runTest('/oracle/orderby', 'col', 'id', 'form')">表单</button>
                <button class="btn btn-alt" onclick="runUrlEncodedTest('/oracle/orderby', 'col', 'id')">URL编码</button>
                <button class="btn" style="background: #f39c12;" onclick="runNestedJsonStringTest('/oracle/orderby', 'col', 'id')">嵌套JSON字符串</button>
                <button class="btn" style="background: #27ae60;" onclick="runNestedJsonObjectTest('/oracle/orderby', 'col', 'id')">嵌套JSON对象</button>
                <button class="btn" style="background: #e74c3c;" onclick="runGetTest('/oracle/orderby', 'col', 'id')">GET请求</button>
                <button class="btn" style="background: #16a085;" onclick="runGetUrlEncodedTest('/oracle/orderby', 'col', 'id')">GET URL编码</button>
            </td>
        </tr>
    </table>

    <h2>🛠️ 自定义请求</h2>
    <div class="card">
        <div class="tabs">
            <div class="tab active" onclick="openTab(event, 'tab-json')">JSON</div>
            <div class="tab" onclick="openTab(event, 'tab-form')">表单</div>
            <div class="tab" onclick="openTab(event, 'tab-nested')">嵌套 JSON</div>
            <div class="tab" onclick="openTab(event, 'tab-nested-string')">嵌套 JSON 字符串</div>
            <div class="tab" onclick="openTab(event, 'tab-urlencoded')">URL 编码</div>
            <div class="tab" onclick="openTab(event, 'tab-get')">GET 请求</div>
            <div class="tab" onclick="openTab(event, 'tab-get-urlencoded')">GET URL 编码</div>
        </div>

        <div id="tab-json" class="tab-content active">
            <label for="custom-endpoint-json">接口:</label>
            <input type="text" id="custom-endpoint-json" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-param-json">参数名:</label>
            <input type="text" id="custom-param-json" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-json">参数值:</label>
            <input type="text" id="custom-value-json" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn btn-run" style="margin-top: 15px;" onclick="runCustomTest('json')">发送 JSON 请求</button>
            <div id="custom-result-json" class="result-box" style="display:none;"></div>
        </div>

        <div id="tab-form" class="tab-content">
            <label for="custom-endpoint-form">接口:</label>
            <input type="text" id="custom-endpoint-form" class="payload-input" value="/mysql/orderby" placeholder="例如: /mysql/orderby">

            <label for="custom-param-form">参数名:</label>
            <input type="text" id="custom-param-form" class="payload-input" value="col" placeholder="例如: col">

            <label for="custom-value-form">参数值:</label>
            <input type="text" id="custom-value-form" class="payload-input" value="id" placeholder="例如: id">

            <button class="btn btn-run" style="margin-top: 15px;" onclick="runCustomTest('form')">发送表单请求</button>
            <div id="custom-result-form" class="result-box" style="display:none;"></div>
        </div>

        <div id="tab-nested" class="tab-content">
            <label for="custom-endpoint-nested">接口:</label>
            <input type="text" id="custom-endpoint-nested" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-wrapper-nested">外层键名:</label>
            <input type="text" id="custom-wrapper-nested" class="payload-input" value="data" placeholder="例如: data">

            <label for="custom-param-nested">内层参数名:</label>
            <input type="text" id="custom-param-nested" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-nested">内层参数值:</label>
            <input type="text" id="custom-value-nested" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn btn-run" style="margin-top: 15px;" onclick="runCustomTest('nested')">发送嵌套 JSON 请求</button>
            <div id="custom-result-nested" class="result-box" style="display:none;"></div>
        </div>
        
        <div id="tab-urlencoded" class="tab-content">
            <label for="custom-endpoint-urlencoded">接口:</label>
            <input type="text" id="custom-endpoint-urlencoded" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-param-urlencoded">参数名:</label>
            <input type="text" id="custom-param-urlencoded" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-urlencoded">参数值:</label>
            <input type="text" id="custom-value-urlencoded" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn btn-alt" style="margin-top: 15px;" onclick="runCustomTest('urlencoded')">发送 URL 编码 JSON 请求</button>
            <div id="custom-result-urlencoded" class="result-box" style="display:none;"></div>
        </div>

        <div id="tab-nested-string" class="tab-content">
            <label for="custom-endpoint-nested-string">接口:</label>
            <input type="text" id="custom-endpoint-nested-string" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-wrapper-nested-string">外层键名:</label>
            <input type="text" id="custom-wrapper-nested-string" class="payload-input" value="data" placeholder="例如: data">

            <label for="custom-param-nested-string">内层参数名:</label>
            <input type="text" id="custom-param-nested-string" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-nested-string">内层参数值:</label>
            <input type="text" id="custom-value-nested-string" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn" style="background: #f39c12; margin-top: 15px;" onclick="runCustomTest('nested-string')">发送嵌套 JSON 字符串请求</button>
            <div id="custom-result-nested-string" class="result-box" style="display:none;"></div>
        </div>

        <div id="tab-get" class="tab-content">
            <label for="custom-endpoint-get">接口:</label>
            <input type="text" id="custom-endpoint-get" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-param-get">参数名:</label>
            <input type="text" id="custom-param-get" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-get">参数值:</label>
            <input type="text" id="custom-value-get" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn" style="background: #e74c3c; margin-top: 15px;" onclick="runCustomTest('get')">发送 GET 请求</button>
            <div id="custom-result-get" class="result-box" style="display:none;"></div>
        </div>

        <div id="tab-get-urlencoded" class="tab-content">
            <label for="custom-endpoint-get-urlencoded">接口:</label>
            <input type="text" id="custom-endpoint-get-urlencoded" class="payload-input" value="/mysql/int" placeholder="例如: /mysql/int">

            <label for="custom-param-get-urlencoded">参数名:</label>
            <input type="text" id="custom-param-get-urlencoded" class="payload-input" value="id" placeholder="例如: id">

            <label for="custom-value-get-urlencoded">参数值:</label>
            <input type="text" id="custom-value-get-urlencoded" class="payload-input" value="1 OR 1=1" placeholder="例如: 1 OR 1=1">

            <button class="btn" style="background: #16a085; margin-top: 15px;" onclick="runCustomTest('get-urlencoded')">发送 GET URL 编码 JSON 请求</button>
            <div id="custom-result-get-urlencoded" class="result-box" style="display:none;"></div>
        </div>
    </div>

    <script>
        // Tab switching logic
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            tablinks = document.getElementsByClassName("tab");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.className += " active";
        }

        // Generic function to run standard tests from the table (JSON/Form)
        async function runTest(endpoint, paramName, paramValue, dataType) {
            let url = endpoint;
            let options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            if (dataType === 'json') {
                let actualValue = paramValue;
                // 对于int类型端点，始终将纯数字字符串转换为数字类型
                if (endpoint.includes('/int') && /^\d+$/.test(paramValue)) {
                    actualValue = parseInt(paramValue, 10);
                }
                options.body = JSON.stringify({ [paramName]: actualValue });
            } else if (dataType === 'form') {
                options.method = 'POST';
                options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                options.body = `${encodeURIComponent(paramName)}=${encodeURIComponent(paramValue)}`;
            }

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target; 
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }
        
        // Function to run nested JSON string test from the table (e.g., {"data":"{\"id\":\"1\"}"})
        async function runNestedJsonStringTest(endpoint, paramName, paramValue) {
            const url = endpoint;
            let actualValue = paramValue;
            // 对于int类型端点，始终将纯数字字符串转换为数字类型
            if (endpoint.includes('/int') && /^\d+$/.test(paramValue)) {
                actualValue = parseInt(paramValue, 10);
            }
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Create the nested JSON string structure
                body: JSON.stringify({ data: JSON.stringify({ [paramName]: actualValue }) })
            };

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('Nested JSON string Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }

        // Function to run nested JSON object test (e.g., {"data": {"id": "1"}} or {"data": {"id": 1}})
        async function runNestedJsonObjectTest(endpoint, paramName, paramValue) {
            const url = endpoint;
            // 创建嵌套JSON对象，根据端点类型决定参数值类型
            let actualValue = paramValue;
            // 对于int类型端点，始终将纯数字字符串转换为数字类型
            if (endpoint.includes('/int') && /^\d+$/.test(paramValue)) {
                actualValue = parseInt(paramValue, 10);
            }
            
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // 创建嵌套JSON对象结构
                body: JSON.stringify({ data: { [paramName]: actualValue } })
            };

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('Nested JSON object Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }

        // Function to run GET request test from the table (e.g., ?id=1)
        async function runGetTest(endpoint, paramName, paramValue) {
            // Create the URL with query parameters
            const url = `${endpoint}?${paramName}=${encodeURIComponent(paramValue)}`;
            const options = {
                method: 'GET'
            };

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('GET Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }

        // Function to run GET URL-encoded JSON test from the table (e.g., ?data=%7B%22id%22%3A%221%22%7D)
        async function runGetUrlEncodedTest(endpoint, paramName, paramValue) {
            // Create the JSON object first, then stringify and encode it
            let actualValue = paramValue;
            // 对于int类型端点，始终将纯数字字符串转换为数字类型
            if (endpoint.includes('/int') && /^\d+$/.test(paramValue)) {
                actualValue = parseInt(paramValue, 10);
            }
            const jsonStr = JSON.stringify({ [paramName]: actualValue });
            const encodedJson = encodeURIComponent(jsonStr);
            const url = `${endpoint}?data=${encodedJson}`;
            const options = {
                method: 'GET'
            };

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('GET URL-encoded Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }

        // Function to run URL-encoded JSON test from the table
        async function runUrlEncodedTest(endpoint, paramName, paramValue) {
            const url = endpoint;
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                // Create the JSON object first, then stringify and encode it
                body: `data=${encodeURIComponent(JSON.stringify({ [paramName]: paramValue }))}`
            };

            try {
                const response = await fetch(url, options);
                const resultText = await response.text();
                const button = event.target; 
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = resultText;
                resultBox.style.display = 'block';
                if (!response.ok) {
                     resultBox.classList.add('error-box');
                } else {
                     resultBox.classList.remove('error-box');
                }
            } catch (error) {
                console.error('URL-encoded Fetch error:', error);
                const button = event.target;
                const row = button.closest('tr');
                let resultBox = row.querySelector('.result-box');
                if (!resultBox) {
                    resultBox = document.createElement('div');
                    resultBox.className = 'result-box error-box';
                    row.appendChild(resultBox);
                }
                resultBox.textContent = `请求失败: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }


        // Function to run custom tests
        async function runCustomTest(type) {
            let endpoint, paramName, paramValue, wrapperName, options, resultElementId;

            if (type === 'json') {
                endpoint = document.getElementById('custom-endpoint-json').value;
                paramName = document.getElementById('custom-param-json').value;
                paramValue = document.getElementById('custom-value-json').value;
                options = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ [paramName]: paramValue })
                };
                resultElementId = 'custom-result-json';
            } else if (type === 'form') {
                endpoint = document.getElementById('custom-endpoint-form').value;
                paramName = document.getElementById('custom-param-form').value;
                paramValue = document.getElementById('custom-value-form').value;
                options = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `${encodeURIComponent(paramName)}=${encodeURIComponent(paramValue)}`
                };
                resultElementId = 'custom-result-form';
            } else if (type === 'nested') {
                endpoint = document.getElementById('custom-endpoint-nested').value;
                wrapperName = document.getElementById('custom-wrapper-nested').value;
                paramName = document.getElementById('custom-param-nested').value;
                paramValue = document.getElementById('custom-value-nested').value;
                const dataObj = {};
                dataObj[wrapperName] = { [paramName]: paramValue };
                options = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataObj)
                };
                resultElementId = 'custom-result-nested';
            } else if (type === 'nested-string') {
                endpoint = document.getElementById('custom-endpoint-nested-string').value;
                wrapperName = document.getElementById('custom-wrapper-nested-string').value;
                paramName = document.getElementById('custom-param-nested-string').value;
                paramValue = document.getElementById('custom-value-nested-string').value;
                // 创建嵌套JSON字符串结构 {"data": "{\"id\":\"1\"}"}
                const dataObj = {};
                dataObj[wrapperName] = JSON.stringify({ [paramName]: paramValue });
                options = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataObj)
                };
                resultElementId = 'custom-result-nested-string';
            } else if (type === 'get') {
                endpoint = document.getElementById('custom-endpoint-get').value;
                paramName = document.getElementById('custom-param-get').value;
                paramValue = document.getElementById('custom-value-get').value;
                // 创建带查询参数的URL
                endpoint = `${endpoint}?${paramName}=${encodeURIComponent(paramValue)}`;
                options = {
                    method: 'GET'
                };
                resultElementId = 'custom-result-get';
            } else if (type === 'get-urlencoded') {
                endpoint = document.getElementById('custom-endpoint-get-urlencoded').value;
                paramName = document.getElementById('custom-param-get-urlencoded').value;
                paramValue = document.getElementById('custom-value-get-urlencoded').value;
                // 创建JSON对象，然后序列化并编码
                const jsonStr = JSON.stringify({ [paramName]: paramValue });
                const encodedJson = encodeURIComponent(jsonStr);
                endpoint = `${endpoint}?data=${encodedJson}`;
                options = {
                    method: 'GET'
                };
                resultElementId = 'custom-result-get-urlencoded';
            } else if (type === 'urlencoded') {
                 endpoint = document.getElementById('custom-endpoint-urlencoded').value;
                 paramName = document.getElementById('custom-param-urlencoded').value;
                 paramValue = document.getElementById('custom-value-urlencoded').value;
                 options = {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                     body: `data=${encodeURIComponent(JSON.stringify({ [paramName]: paramValue }))}`
                 };
                 resultElementId = 'custom-result-urlencoded';
            }

            const resultElement = document.getElementById(resultElementId);
            resultElement.style.display = 'block';
            resultElement.textContent = '正在发送请求...';

            try {
                const response = await fetch(endpoint, options);
                const resultText = await response.text();
                resultElement.textContent = resultText;
                if (!response.ok) {
                     resultElement.classList.add('error-box');
                } else {
                     resultElement.classList.remove('error-box');
                }
            } catch (error) {
                console.error('Custom Fetch error:', error);
                resultElement.textContent = `请求失败: ${error.message}`;
                resultElement.classList.add('error-box');
            }
        }
    </script>
</body>
</html>
    """

# --- Manual Init Route (Optional, kept for completeness) ---
@app.route('/init')
def init():
    try:
        print("接收到数据库初始化请求")
        db.init_databases()
        return "Databases Initialized Successfully"
    except Exception as e:
        print(f"初始化请求处理出错: {e}")
        return f"Error initializing databases: {str(e)}", 500


if __name__ == '__main__':
    # The initialization happens above, outside the if __name__ block
    app.run(host='0.0.0.0', port=8888, debug=True) # Debug mode is okay for lab env