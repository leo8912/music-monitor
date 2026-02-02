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

# 配置国内镜像源（提高下载速度和成功率）
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Install runtime dependencies including gosu for PUID/PGID
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies (使用 pip cache 优化，但最后清理)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.11 -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type d -name '*.dist-info' -exec rm -rf {}/RECORD {} + 2>/dev/null || true

# Fix qqmusic_api cache permission (it tries to write to its own package dir)
RUN mkdir -p /usr/local/lib/python3.11/site-packages/qqmusic_api/.cache && \
    chmod -R 777 /usr/local/lib/python3.11/site-packages/qqmusic_api/.cache

# Copy only necessary backend files (order matters for cache)
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY config.example.yaml /app/config.example.yaml
COPY main.py /app/
COPY version.py /app/
COPY app/ /app/app/
COPY core/ /app/core/
COPY domain/ /app/domain/
COPY notifiers/ /app/notifiers/

# Create default config
RUN cp config.example.yaml config.yaml

# Copy Built Frontend from Stage 1
COPY --from=frontend /app/web/dist /app/web/dist

# Environment defaults
ENV DATABASE_URL=sqlite+aiosqlite:////config/music_monitor.db
ENV TZ=Asia/Shanghai

VOLUME /config

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "main.py"]
