# Stage 1: Build Frontend
FROM node:22-alpine AS frontend
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Stage 2: Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (if any needed for numpy/cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Backend Code
COPY . .

# Ensure config.yaml exists (use example if not provided in build context)
# Since we .dockerignore config.yaml, this essentially always copies example to config.yaml
# But user is expected to mount their own config.yaml at runtime overlaying this.
RUN cp config.example.yaml config.yaml

# Copy Built Frontend from Stage 1
COPY --from=frontend /app/web/dist /app/web/dist

# Environment defaults
ENV DATABASE_URL=sqlite:////config/music_monitor.db
ENV TZ=Asia/Shanghai

VOLUME /config

EXPOSE 8000

CMD ["python", "main.py"]
