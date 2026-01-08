#!/bin/bash
# 测试脚本，验证所有服务是否正常运行

echo "正在测试SQL注入实验室的所有服务..."

# 测试Web应用是否响应
echo "测试Web应用..."
if curl -s http://localhost:8888 | grep -q "SQL Injection Lab"; then
    echo "✓ Web应用正在运行"
else
    echo "✗ Web应用可能未运行"
fi

# 测试MySQL连接（如果安装了mysql客户端）
if command -v mysql &> /dev/null; then
    echo "测试MySQL连接..."
    if mysql -h localhost -P 3306 -u root -prootpassword -e "SHOW DATABASES;" &> /dev/null; then
        echo "✓ MySQL服务正在运行"
    else
        echo "✗ MySQL服务可能未运行"
    fi
else
    echo "! 未找到MySQL客户端，跳过MySQL测试"
fi

# 测试PostgreSQL连接（如果安装了psql客户端）
if command -v psql &> /dev/null; then
    echo "测试PostgreSQL连接..."
    if PGPASSWORD=123456 psql -h localhost -p 5432 -U test -c "SELECT version();" &> /dev/null; then
        echo "✓ PostgreSQL服务正在运行"
    else
        echo "✗ PostgreSQL服务可能未运行"
    fi
else
    echo "! 未找到PostgreSQL客户端，跳过PostgreSQL测试"
fi

# 测试ClickHouse连接（如果安装了clickhouse-client）
if command -v clickhouse-client &> /dev/null; then
    echo "测试ClickHouse连接..."
    if clickhouse-client --host=localhost --port=9000 --query="SELECT version()" &> /dev/null; then
        echo "✓ ClickHouse服务正在运行"
    else
        echo "✗ ClickHouse服务可能未运行"
    fi
else
    echo "! 未找到ClickHouse客户端，跳过ClickHouse测试"
fi

echo "服务测试完成！"