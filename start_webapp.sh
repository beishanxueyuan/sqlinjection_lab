#!/bin/bash

echo "等待数据库服务完全启动..."

# 等待MySQL
for i in {1..30}; do
  if mysql -h localhost -u root -prootpassword -e "SELECT 1;" &> /dev/null; then
    echo "MySQL 已就绪"
    break
  else
    echo "等待 MySQL 就绪... ($i/30)"
    sleep 2
  fi
done

# 等待PostgreSQL
for i in {1..30}; do
  if su - postgres -c "psql -c 'SELECT 1;'" &> /dev/null; then
    echo "PostgreSQL 已就绪"
    break
  else
    echo "等待 PostgreSQL 就绪... ($i/30)"
    sleep 2
  fi
done

# 等待ClickHouse
for i in {1..30}; do
  if clickhouse-client --host=localhost --port=9000 --query="SELECT 1;" &> /dev/null; then
    echo "ClickHouse 已就绪"
    break
  else
    echo "等待 ClickHouse 就绪... ($i/30)"
    sleep 2
  fi
done

echo "所有数据库服务已就绪，启动Web应用..."
python3 app.py