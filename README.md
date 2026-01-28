# SQL注入实验室 - 单容器版本

此项目已整合为单个容器，包含Web应用程序和多种数据库(MySQL、PostgreSQL、ClickHouse)。由于许可限制，Oracle数据库不包含在此单容器版本中。

## 构建和运行

### 使用Docker构建镜像：
```bash
docker build -f Dockerfile -t sqlinjection-lab .
```

### 运行容器：
```bash
docker run -p 8888:8888 -p 3306:3306 -p 5432:5432 -p 8123:8123 -p 9000:9000 sqlinjection-lab
```

或者使用一次性命令构建并运行：
```bash
docker build -f Dockerfile-single -t sqlinjection-lab . && docker run -p 8888:8888 -p 3306:3306 -p 5432:5432 -p 8123:8123 -p 9000:9000 sqlinjection-lab
```

## 访问服务

- Web界面: http://localhost:8888
- MySQL: localhost:3306 (用户名: root, 密码: rootpassword, 数据库: sqli_lab)
- PostgreSQL: localhost:5432 (用户名: postgres, 密码: rootpassword, 数据库: sqli_lab)
- ClickHouse: localhost:9000 (默认用户: default)

## 功能

该容器提供针对3种不同数据库的SQL注入测试接口：
- MySQL
- PostgreSQL
- ClickHouse

每种数据库都提供多种类型的易受攻击的查询接口，包括字符型、整数型、LIKE和ORDER BY注入点。

## 说明

所有服务都在单个容器中运行，通过Supervisor进程管理器管理各个服务的启动和监控。

注意：Oracle数据库由于许可限制未包含在此单容器版本中。如需Oracle支持，请使用原始的多容器docker-compose设置。

所有服务（MySQL、PostgreSQL、ClickHouse和Web应用）现在都在单个容器内稳定运行。