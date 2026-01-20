# 本地 Docker 测试步骤

## 准备工作
```bash
# 1. 停止本地运行的 Python 服务（避免端口冲突）
# 在运行 main.py 的终端按 Ctrl+C

# 2. 确保 Docker Desktop 已启动
docker --version
```

## 构建并运行

### 方法一：快速构建测试（推荐）
```bash
# 构建镜像
docker-compose -f docker-compose.test.yml build

# 启动容器
docker-compose -f docker-compose.test.yml up -d

# 查看日志（实时跟踪）
docker-compose -f docker-compose.test.yml logs -f

# 或单独查看容器日志
docker logs -f music-monitor-test
```

### 方法二：分步构建
```bash
# 1. 构建镜像（带标签）
docker build -t music-monitor:local-test .

# 2. 手动运行容器
docker run -d \
  --name music-monitor-test \
  -p 18001:8000 \
  -v ${PWD}/config:/config \
  -v ${PWD}/cache:/audio_cache \
  -v ${PWD}/favorites:/favorites \
  -e DATABASE_URL=sqlite:////config/music_monitor.db \
  -e TZ=Asia/Shanghai \
  music-monitor:local-test

# 3. 查看日志
docker logs -f music-monitor-test
```

## 访问测试

### Web 界面
打开浏览器访问：http://localhost:18001

### API 测试
```bash
# 检查服务状态
curl http://localhost:18001/api/status

# 查看历史记录（测试修复效果）
curl http://localhost:18001/api/history
```

### 微信测试
修改 `config.yaml` 中的回调地址为：
```yaml
notify:
  wecom:
    callback_url: http://你的公网IP:18001/api/wecom/callback
```

## 验证修复

### 1. 测试"刷新页面报错"修复
- 访问 http://localhost:18001
- 打开开发者工具网络面板
- 刷新页面
- 检查 `/api/history` 请求是否返回 200 而非 500

### 2. 测试"添加歌手"修复
- 在微信中发送：`任素汐`
- 查看是否返回搜索结果（带头像卡片）
- 回复序号（如 `1`）
- 观察容器日志是否有错误

### 3. 测试 QQ 音乐搜索
- 在微信搜索歌手
- 查看容器日志中是否有：
  ```
  INFO - QQ Search Result: X artists found
  ```
- 如果为 0 或报错，记录具体错误信息

## 停止和清理

```bash
# 停止容器
docker-compose -f docker-compose.test.yml down

# 或手动停止
docker stop music-monitor-test
docker rm music-monitor-test

# 清理镜像（可选）
docker rmi music-monitor:local-test
```

## 常见问题

### 1. 构建失败：npm install 超时
- 检查网络连接
- 或在 Dockerfile 中添加国内镜像源

### 2. 容器启动后立即退出
```bash
# 查看退出原因
docker logs music-monitor-test

# 检查配置文件权限
ls -la config/
```

### 3. 端口已被占用
- 修改 `docker-compose.test.yml` 中的端口映射
- 例如改为 `"18002:8000"`

## 部署到远程 NAS

测试通过后，推送代码并在 NAS 上：
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose down
docker-compose up -d --build

# 查看日志
docker logs -f music-monitor
```
