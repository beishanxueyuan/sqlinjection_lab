import os
import time
import mysql.connector

# 尝试导入其他数据库驱动，如果失败则设置为None
try:
    import psycopg2
except ImportError:
    psycopg2 = None
    print("警告: PostgreSQL驱动未安装，PostgreSQL功能将不可用")

try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    ClickHouseClient = None
    print("警告: ClickHouse驱动未安装，ClickHouse功能将不可用")

try:
    import oracledb
except ImportError:
    oracledb = None
    print("警告: Oracle驱动未安装，Oracle功能将不可用")

# Environment variables - All point to localhost since all DBs will run in same container
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'localhost')
ORACLE_HOST = os.environ.get('ORACLE_HOST', 'localhost')

def get_mysql_connection():
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            user='root',
            password='rootpassword',
            database='sqli_lab'
        )
    except Exception as e:
        print(f"MySQL Connection Error: {e}")
        return None

def get_postgres_connection():
    if psycopg2 is None:
        print("PostgreSQL驱动未安装，无法连接")
        return None
    try:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            user='root',
            password='rootpassword',
            dbname='sqli_lab'
        )
    except Exception as e:
        print(f"Postgres Connection Error: {e}")
        return None

def get_clickhouse_connection():
    if ClickHouseClient is None:
        print("ClickHouse驱动未安装，无法连接")
        return None
    try:
        return ClickHouseClient(host=CLICKHOUSE_HOST)
    except Exception as e:
        print(f"ClickHouse Connection Error: {e}")
        return None

def get_oracle_connection():
    # Oracle is not available in the single container setup due to licensing restrictions
    print("Oracle is not available in this single-container setup due to licensing restrictions")
    return None

def init_databases():
    print("Initializing databases... (某些数据库可能不可用，但MySQL应该可以正常工作)")
    
    # Retry logic for each database
    max_retries = 5  # 减少重试次数以加快启动
    retry_interval = 2

    # MySQL Init
    for i in range(max_retries):
        conn = get_mysql_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(255), password VARCHAR(255))")
                cursor.execute("TRUNCATE TABLE users")
                cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123'), ('user1', 'pass1')")
                conn.commit()
                conn.close()
                print("MySQL Initialized")
                break
            except Exception as e:
                print(f"MySQL Init Error: {e}")
        else:
            print(f"Waiting for MySQL... ({i+1}/{max_retries})")
        time.sleep(retry_interval)

    # Postgres Init - 只有在驱动可用时才尝试
    if psycopg2 is not None:
        for i in range(max_retries):
            conn = get_postgres_connection()
            if conn:
                try:
                    conn.autocommit = True
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(255), password VARCHAR(255))")
                    cursor.execute("TRUNCATE TABLE users RESTART IDENTITY")
                    cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123'), ('user1', 'pass1')")
                    conn.close()
                    print("Postgres Initialized")
                    break
                except Exception as e:
                    print(f"Postgres Init Error: {e}")
            else:
                print(f"Waiting for Postgres... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
    else:
        print("跳过PostgreSQL初始化 - 驱动未安装")

    # ClickHouse Init - 只有在驱动可用时才尝试
    if ClickHouseClient is not None:
        for i in range(max_retries):
            client = get_clickhouse_connection()
            if client:
                try:
                    client.execute("CREATE DATABASE IF NOT EXISTS sqli_lab")
                    client.execute("CREATE TABLE IF NOT EXISTS sqli_lab.users (id UInt32, username String, password String) ENGINE = MergeTree() ORDER BY id")
                    client.execute("TRUNCATE TABLE sqli_lab.users")
                    client.execute("INSERT INTO sqli_lab.users (id, username, password) VALUES (1, 'admin', 'admin123'), (2, 'user1', 'pass1')")
                    print("ClickHouse Initialized")
                    break
                except Exception as e:
                    print(f"ClickHouse Init Error: {e}")
            else:
                print(f"Waiting for ClickHouse... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
    else:
        print("跳过ClickHouse初始化 - 驱动未安装")

    # Oracle Init - 只有在驱动可用时才尝试
    if oracledb is not None:
        for i in range(max_retries):
            conn = get_oracle_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    try:
                        cursor.execute("CREATE TABLE users (id NUMBER GENERATED BY DEFAULT AS IDENTITY, username VARCHAR2(255), password VARCHAR2(255))")
                    except oracledb.DatabaseError as e:
                        if e.args[0].code != 955: # ORA-00955: name is already used by an existing object
                            raise
                    
                    cursor.execute("DELETE FROM users")
                    cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
                    cursor.execute("INSERT INTO users (username, password) VALUES ('user1', 'pass1')")
                    conn.commit()
                    conn.close()
                    print("Oracle Initialized")
                    break
                except Exception as e:
                    print(f"Oracle Init Error: {e}")
            else:
                print(f"Waiting for Oracle... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
    else:
        print("跳过Oracle初始化 - 驱动未安装")
