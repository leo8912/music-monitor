# Stage 1: Build Frontend
FROM node:22-alpine AS frontend
WORKDIR /app/web

# 配置 npm 使用国内镜像（可选，加速构建）
RUN npm config set registry https://registry.npmmirror.com

COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Stage 2: Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# APT mirror optimization and runtime dependency installation
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python dependencies installation
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt && \
    chmod -R a+rX /usr/local/lib/python3.11/site-packages

# Fix qqmusic_api cache permission
RUN mkdir -p /usr/local/lib/python3.11/site-packages/qqmusic_api/.cache && \
    chmod -R 777 /usr/local/lib/python3.11/site-packages/qqmusic_api/.cache

# Copy application code
COPY . /app
RUN chmod +x /app/scripts/entrypoint.sh && \
    cp config.example.yaml config.yaml

# Copy Built Frontend from Stage 1
COPY --from=frontend /app/web/dist /app/web/dist

# Setup volume and env
RUN mkdir -p /library /config
ENV DATABASE_URL=sqlite+aiosqlite:////config/music_monitor.db
ENV TZ=Asia/Shanghai
VOLUME /config
EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "main.py"]
