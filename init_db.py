#!/usr/bin/env python3
"""
数据库初始化脚本
确保在所有数据库服务启动后再初始化数据库
"""

import time
import mysql.connector
import psycopg2
from clickhouse_driver import Client
import subprocess
import sys
import os

def wait_for_service(service_cmd, timeout=60):
    """等待服务启动"""
    for _ in range(timeout):
        try:
            result = subprocess.run(service_cmd, shell=True, capture_output=True)
            if result.returncode == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def init_mysql():
    """初始化MySQL数据库"""
    try:
        print("正在初始化MySQL...")
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='rootpassword'
        )
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS sqli_lab;")
        cursor.execute("USE sqli_lab;")
        
        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50),
                password VARCHAR(50)
            );
        """)
        
        # 插入测试数据
        cursor.execute("DELETE FROM users WHERE username IN ('admin', 'user1');")
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s), (%s, %s);", 
                      ('admin', 'admin123', 'user1', 'pass1'))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("MySQL初始化完成")
        return True
    except Exception as e:
        print(f"MySQL初始化失败: {e}")
        return False

def init_postgresql():
    """初始化PostgreSQL数据库"""
    try:
        print("正在初始化PostgreSQL...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='test',
            password='123456',
            database='sqli_lab'
        )
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50),
                password VARCHAR(50)
            );
        """)
        
        # 插入测试数据
        cursor.execute("DELETE FROM users WHERE username IN ('admin', 'user1');")
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s), (%s, %s);", 
                      ('admin', 'admin123', 'user1', 'pass1'))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("PostgreSQL初始化完成")
        return True
    except Exception as e:
        print(f"PostgreSQL初始化失败: {e}")
        return False

def init_clickhouse():
    """初始化ClickHouse数据库"""
    try:
        print("正在初始化ClickHouse...")
        client = Client(host='localhost', port=9000)
        
        # 创建数据库
        client.execute("CREATE DATABASE IF NOT EXISTS sqli_lab;")
        
        # 创建表
        client.execute("""
            CREATE TABLE IF NOT EXISTS sqli_lab.users (
                id UInt32,
                username String,
                password String
            ) ENGINE = MergeTree()
            ORDER BY id;
        """)
        
        # 插入测试数据
        client.execute("TRUNCATE TABLE sqli_lab.users;")
        client.execute("INSERT INTO sqli_lab.users VALUES", [
            (1, 'admin', 'admin123'),
            (2, 'user1', 'pass1')
        ])
        
        print("ClickHouse初始化完成")
        return True
    except Exception as e:
        print(f"ClickHouse初始化失败: {e}")
        return False

def main():
    """主函数"""
    print("开始数据库初始化...")
    
    # 初始化各数据库
    mysql_ok = init_mysql()
    pg_ok = init_postgresql()
    ch_ok = init_clickhouse()
    
    if mysql_ok and pg_ok and ch_ok:
        print("所有数据库初始化成功！")
        return 0
    else:
        print("部分数据库初始化失败，但继续启动应用...")
        return 1

if __name__ == "__main__":
    sys.exit(main())