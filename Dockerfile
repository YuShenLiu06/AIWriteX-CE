# AIWriteX Server Docker Image
# Python 3.11 slim 基础镜像
FROM python:3.11-slim

# 环境变量配置
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# 工作目录
WORKDIR /app

# 安装系统依赖并清理缓存
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（分层缓存优化）
COPY requirements-server.txt /app/

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements-server.txt

# 复制源代码
COPY src ./src
COPY main.py ./

# 数据卷（持久化目录）
VOLUME ["/app/output", "/app/image", "/app/logs", "/app/temp", "/app/src/ai_write_x/config"]

# 默认环境变量
ENV AIWRITEX_RUN_MODE=server \
    AIWRITEX_HOST=0.0.0.0 \
    AIWRITEX_PORT=8888 \
    AIWRITEX_AUTH_ENABLED=true

# 暴露端口
EXPOSE 8888

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8888/health || exit 1

# 启动命令
CMD ["python", "main.py"]
