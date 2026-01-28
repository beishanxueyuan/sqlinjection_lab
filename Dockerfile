FROM ubuntu:22.04

# 国内镜像源
RUN sed -i 's|ports.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list && \
    sed -i 's|archive.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list && \
    sed -i 's|security.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list

# 设置环境变量避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV MYSQL_HOST=localhost
ENV POSTGRES_HOST=localhost
ENV CLICKHOUSE_HOST=localhost
ENV ORACLE_HOST=localhost

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y wget curl gnupg lsb-release software-properties-common supervisor locales sudo && \
    locale-gen zh_CN.UTF-8 && \
    update-locale LANG=zh_CN.UTF-8

# 安装 MySQL Server
RUN apt-get install -y mysql-server && \
    chown -R mysql:mysql /var/lib/mysql /var/log/mysql /var/run/mysqld

# 配置MySQL root密码
RUN echo "[mysqld]\nbind-address = 0.0.0.0\ndefault_authentication_plugin=mysql_native_password\n" > /etc/mysql/conf.d/custom.cnf && \
    echo "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'rootpassword';" > /tmp/mysql-init.sql && \
    echo "FLUSH PRIVILEGES;" >> /tmp/mysql-init.sql

# 安装 PostgreSQL
RUN apt-get install -y postgresql postgresql-contrib && \
    service postgresql start && \
    su - postgres -c "createuser --superuser root" && \
    su - postgres -c "psql -c \"ALTER USER root PASSWORD 'rootpassword';\"" && \
    su - postgres -c "createdb -O root sqli_lab"

# 安装 Python 和相关工具
RUN apt-get install -y python3 python3-pip python3-dev && \
    ln -sf python3 /usr/bin/python && \
    ln -sf pip3 /usr/bin/pip

# 安装 ClickHouse
RUN apt-get install -y ca-certificates curl gnupg && \
    curl -fsSL 'https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key' | gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" > /etc/apt/sources.list.d/clickhouse.list && \
    apt-get update && \
    apt-get install -y clickhouse-server clickhouse-client && \
    sed -i 's/<listen_host>127.0.0.1<\/listen_host>/<listen_host>0.0.0.0<\/listen_host>/g' /etc/clickhouse-server/config.xml

# 安装 Oracle Instant Client (using the basiclite version which doesn't require authentication)
RUN apt-get install -y wget unzip libaio1 libaio-dev && \
    cd /tmp && \
    wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip && \
    unzip instantclient-basiclite-linuxx64.zip -d /opt/ && \
    rm -f instantclient-basiclite-linuxx64.zip && \
    sh -c "echo /opt/oracle/instantclient* > /etc/ld.so.conf.d/oracle-instantclient.conf" && \
    ldconfig

# 设置 Oracle 环境变量
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_8:$LD_LIBRARY_PATH
ENV TNS_ADMIN=/opt/oracle/network/admin

# 创建必要的目录
RUN mkdir -p /app /var/log/supervisor /opt/oracle/oradata /var/lib/clickhouse /var/log/clickhouse && \
    chown -R mysql:mysql /var/lib/mysql /var/log/mysql && \
    chown -R postgres:postgres /var/lib/postgresql /etc/postgresql

WORKDIR /app

# 复制应用代码
COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 配置 supervisord
RUN apt-get install -y supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create initialization script for MySQL
RUN echo '#!/bin/bash\n\
# 启动MySQL服务\n\
mysqld_safe --user=mysql --init-file=/tmp/mysql-init.sql &\n\
\n\
# 等待MySQL服务完全启动\n\
echo "等待MySQL服务启动..."\n\
for i in {1..30}; do\n\
  if mysql -u root -prootpassword -e "SELECT 1;" &> /dev/null; then\n\
    echo "MySQL服务已启动"\n\
    break\n\
  else\n\
    echo "等待MySQL启动... ($i/30)"\n\
    sleep 2\n\
  fi\n\
done\n\
\n\
# 初始化数据库\n\
mysql -u root -prootpassword -e "CREATE DATABASE IF NOT EXISTS sqli_lab; USE sqli_lab; CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50), password VARCHAR(50)); INSERT INTO users (username, password) VALUES ('\''admin'\'', '\''admin123'\''), ('\''user1'\'', '\''pass1'\'');"\n\
\n\
echo "MySQL初始化完成"\n\
while true; do sleep 30; done\n\
' > /init_mysql.sh && chmod +x /init_mysql.sh

# Create initialization script for ClickHouse
RUN echo '#!/bin/bash\n\
# 启动ClickHouse服务\n\
service clickhouse-server start\n\
\n\
# 等待ClickHouse服务完全启动\n\
echo "等待ClickHouse服务启动..."\n\
for i in {1..30}; do\n\
  if clickhouse-client --host=localhost --port=9000 --query="SELECT 1;" &> /dev/null; then\n\
    echo "ClickHouse服务已启动"\n\
    break\n\
  else\n\
    echo "等待ClickHouse启动... ($i/30)"\n\
    sleep 2\n\
  fi\n\
done\n\
\n\
# 初始化数据库\n\
clickhouse-client --host=localhost --port=9000 --query="CREATE DATABASE IF NOT EXISTS sqli_lab;"\n\
clickhouse-client --host=localhost --port=9000 --query="CREATE TABLE IF NOT EXISTS sqli_lab.users (id UInt32, username String, password String) ENGINE = MergeTree() ORDER BY id;"\n\
clickhouse-client --host=localhost --port=9000 --query="INSERT INTO sqli_lab.users VALUES (1, '\''admin'\'', '\''admin123'\''), (2, '\''user1'\'', '\''pass1'\'');"\n\
\n\
echo "ClickHouse初始化完成"\n\
while true; do sleep 30; done\n\
' > /init_clickhouse.sh && chmod +x /init_clickhouse.sh

# Create initialization script for PostgreSQL
RUN echo '#!/bin/bash\n\
# 启动PostgreSQL服务\n\
service postgresql start\n\
\n\
# 等待PostgreSQL服务完全启动\n\
echo "等待PostgreSQL服务启动..."\n\
for i in {1..30}; do\n\
  if su - postgres -c "psql -c '\''SELECT 1;'\''" &> /dev/null; then\n\
    echo "PostgreSQL服务已启动"\n\
    break\n\
  else\n\
    echo "等待PostgreSQL启动... ($i/30)"\n\
    sleep 2\n\
  fi\n\
done\n\
\n\
# 初始化数据库\n\
su - postgres -c "psql -d sqli_lab -c \"CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50), password VARCHAR(50));\""\n\
su - postgres -c "psql -d sqli_lab -c \"INSERT INTO users (username, password) SELECT '\''admin'\'', '\''admin123'\'' WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='\''admin'\'');\""\n\
su - postgres -c "psql -d sqli_lab -c \"INSERT INTO users (username, password) SELECT '\''user1'\'', '\''pass1'\'' WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='\''user1'\'');\""\n\
\n\
echo "PostgreSQL初始化完成"\n\
while true; do sleep 30; done\n\
' > /init_postgres.sh && chmod +x /init_postgres.sh



# 开放必要的端口
EXPOSE 8888

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]