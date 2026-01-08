#!/bin/bash

# SQL注入实验室单容器构建和运行脚本

echo "正在构建SQL注入实验室单容器镜像..."
docker build -f Dockerfile-single -t sqlinjection-lab .

if [ $? -eq 0 ]; then
    echo "构建成功！正在启动容器..."
    echo "Web界面将在 http://localhost:8888 可用"
    echo "按 Ctrl+C 停止容器"
    docker run -p 8888:8888 -p 3306:3306 -p 5432:5432 -p 8123:8123 -p 9000:9000 --name sqlinjection-lab-container sqlinjection-lab
else
    echo "构建失败，请检查错误信息"
fi