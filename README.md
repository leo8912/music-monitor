# 🎵 Music Monitor (音乐人新歌监控系统)

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![Vue 3](https://img.shields.io/badge/Frontend-Vue%203%20%2B%20Vite-42b883?logo=vue.js)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ed?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

Music Monitor 是一个集成了 **多平台音乐监控、自动下载、智能Web管理** 的全栈解决方案。它能自动追踪你关注的歌手在 **网易云音乐** 和 **QQ音乐** 的最新发布动态，并通过企业微信或 Telegram 即时推送通知，甚至可以直接在网页端播放和收藏。

## ✨ 核心特性

- **🎧 多源监控**: 同时支持网易云音乐、QQ音乐的专辑与单曲更新。
- **❤️ 收藏与下载**: 
  - **红心收藏**: 网页端一键收藏喜欢的歌曲。
  - **自动归档**: 收藏的歌曲会自动下载并复制到指定目录 (`/favorites`)。
  - **本地缓存**: 自动管理试听缓存，支持定期清理 (`/audio_cache`)。
- **🔔 智能通知**:
  - **企业微信**: 图文卡片推送，支持点击直接播放。
  - **交互指令**: 在企业微信中发送 `喜欢 晴天` 或 `下载 七里香` 进行远程控制。
- **💻 现代化 Web UI**:
  - **Apple Music 风格**: 精美的毛玻璃与动态效果。
  - **Dock 播放器**: 底部悬浮播放器，支持歌词显示和频谱可视化。
  - **设置中心**: 可视化配置监控源、通知、存储路径和系统主题。
- **🚀 易于部署**: 完善的 Docker 支持，数据持久化无忧。

## 🐳 Docker 部署 (推荐)

### 1. 准备目录
在服务器上创建所需的持久化目录：
```bash
mkdir -p music-monitor/config
mkdir -p music-monitor/cache
mkdir -p music-monitor/favorites
cd music-monitor
```

### 2. 配置文件
在 `music-monitor/config` 目录中创建 `config.yaml` 配置文件：
```yaml
# config.yaml
global:
  check_interval_minutes: 60
  # 部署后的外网访问地址，用于生成消息通知的跳转链接
  external_url: "http://your-domain:18000" 
  
auth:
  enabled: true
  username: "admin"
  password: "password"
  secret_key: "CHANGE_ME_TO_RANDOM_STRING"
  
storage:
  cache_dir: /audio_cache
  favorites_dir: /favorites
  retention_days: 180

notify:
  wecom:
    enabled: true
    corpid: "ww..."
    corpsecret: "..."
    agentid: "100001"
    # 用于接收回调指令
    token: "..."
    encoding_aes_key: "..."
```

### 3. 启动容器
```bash
docker run -d \
  --name music-monitor \
  --restart always \
  -p 18000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/data:/data \
  -v $(pwd)/cache:/audio_cache \
  -v $(pwd)/favorites:/favorites \
  -v $(pwd)/uploads:/app/uploads \
  -e TZ=Asia/Shanghai \
  lbh1230/music-monitor:latest
```

### 📂 目录映射说明 (持久化)

| 容器内路径 | 宿主机路径 (示例) | 说明 |
| :--- | :--- | :--- |
| `/app/config.yaml` | `./config.yaml` | **配置文件** (必须) |
| `/data` | `./data` | **数据库** (SQLite) |
| `/audio_cache` | `./cache` | **缓存目录** (存放临时试听文件) |
| `/favorites` | `./favorites` | **收藏目录** (存放永久保存的红心歌曲) |
| `/app/uploads` | `./uploads` | **上传目录** (用户头像等) |

---

## 💬 企业微信指令交互

配置好 **API 接收消息** (MyServer 回调) 后，你可以直接与应用对话：

| 指令格式 | 示例 | 作用 |
| :--- | :--- | :--- |
| `[歌手名]` | `周杰伦` | **搜索歌手**，回复序号可 **添加监控** |
| `喜欢 [歌名]` | `喜欢 七里香` | **搜索歌曲**，返回结果列表 |
| `下载 [歌名]` | `下载 七里香` | 同上 |
| `[数字 1-3]` | `1` | 回复 **序号**，根据上一步搜索结果执行 **添加监控** 或 **下载收藏** |

## 🛠️ 本地开发

1. **后端 (Python 3.11+)**:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
2. **前端 (Node.js 18+)**:
   ```bash
   cd web
   npm install
   npm run dev
   ```

## 📄 License

MIT License
