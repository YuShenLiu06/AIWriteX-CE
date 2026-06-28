# AIWriteX Server Docker Image
# Python 3.11 slim 基础镜像
FROM python:3.11-slim

# 环境变量配置
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

# 工作目录
WORKDIR /app

# 替换 apt 为清华源(大陆构建加速)
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖并清理缓存
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（分层缓存优化）
COPY requirements-server.txt /app/

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install -r requirements-server.txt

# 复制源代码
COPY src ./src
COPY main.py ./

# 复制知识库(默认文章模板/文本),确保容器内模板可用
COPY knowledge ./knowledge

# 预创建运行期需要的目录(dev 模式首次启动需可写,防缺目录报错)
RUN mkdir -p /app/knowledge/templates /app/knowledge/texts \
    /app/logs /app/output /app/image /app/temp

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
