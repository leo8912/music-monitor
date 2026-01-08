# 🎵 Music Monitor (音乐人新歌监控系统)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![Vue 3](https://img.shields.io/badge/Frontend-Vue%203%20%2B%20Vite-42b883?logo=vue.js)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ed?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

Music Monitor 是一个集成了 **多平台音乐监控、自动提醒、智能Web管理** 的全栈解决方案。它能自动追踪你关注的歌手在 **网易云音乐**、**QQ音乐** 和 **Bilibili** 的最新发布动态，并通过企业微信或 Telegram 即时推送通知。

<!-- ![Dashboard Preview](docs/screenshot_dashboard.png) -->
<!-- *(这里可以放一张界面截图)* -->

## ✨ 核心特性

- **🎧 多源监控**: 同时支持网易云音乐(专辑/单曲)、QQ音乐、Bilibili(UP主动态)。
- **🔔 即时通知**:
  - **企业微信**: 支持精美的图文卡片 (TextCard)，包含封面图和直达链接。
  - **Telegram**: 支持 Bot 消息推送。
- **💻 现代化 Web UI**:
  - **"Premium Light" 设计**: 仿 Apple Music 的高质感界面。
  - **响应式布局**: 完美适配桌面与移动端。
  - **智能歌手添加**: 只需输入名字，自动搜索并匹配歌手 ID。
  - **设置中心**: 可视化管理监控源、通知渠道和 API 状态。
- **🛡️ 安全鉴权**: 内置登录系统，保护你的隐私数据。
- **🧠 智能去重**: 基于 SQLite 数据库，精准过滤重复通知和幽灵数据。
- **🚀 易于部署**: 支持 Docker 一键启动，开箱即用。

## 🚀 快速开始

### 方式一：Docker 部署 (推荐)

1.  **拉取代码**
    ```bash
    git clone https://github.com/your-username/music-monitor.git
    cd music-monitor
    ```

2.  **配置**
    复制 `config.yaml` 并填入你的信息（为了安全，默认配置中已隐藏敏感信息）：
    ```bash
    # config.yaml 已经包含示例模板
    nano config.yaml
    ```
    *请务必修改 `auth.secret_key` 和 `notify.wecom` 中的凭证。*

3.  **启动**
    ```bash
    docker-compose up -d --build
    ```
    访问: `http://localhost:8000`
    默认账号: `admin` / `password`

### 方式二：本地 Python 运行

1.  **环境准备**
    *   Python 3.10+
    *   Node.js 16+ (如果需要编译前端)

2.  **后端启动**
    ```bash
    # 安装依赖
    pip install -r requirements.txt
    
    # 启动服务
    python main.py
    ```

3.  **前端 (开发者模式)**
    ```bash
    cd web
    npm install
    npm run dev
    ```

## ⚙️ 配置文件说明 (`config.yaml`)

```yaml
global:
  check_interval_minutes: 60  # 全局默认检查间隔
  log_level: INFO

auth:
  enabled: true             # 是否开启登录鉴权
  username: "admin"
  password: "password"      # 登录密码
  secret_key: "CHANGE_ME"   # Session 加密密钥 (重要!)

monitor:
  netease:
    enabled: true
    interval: 60            # 检查间隔 (分钟)
    users:
      - id: '6452'          # 歌手ID
        name: 周杰伦
  qqmusic:
    enabled: true
    interval: 60
    users:
    # 示例: QQ音乐歌手ID (mid)
    # - id: 0025NhlN2yWrP4
    #   name: 周杰伦
  bilibili:
    enabled: true
    interval: 30
    users:
      - id: '546195'        # UP主 UID
        name: Old Tomato

notify:
  wecom:
    enabled: true
    corp_id: "ww..."        # 企业ID
    agent_id: "1000001"     # 应用ID
    secret: "..."           # 应用Secret
  telegram:
    enabled: false
    bot_token: "..."
    chat_id: "..."
```

## 💬 企业微信交互指令

配置好企业微信回调后，你可以在应用中直接发送消息来管理监控列表：

| 指令 | 示例 | 说明 |
| :--- | :--- | :--- |
| **🔍 添加/搜索** | `周杰伦` | 直接发送歌手姓名，自动搜索并添加 |
| **📋 查看列表** | `列表` / `list` | 查看当前已关注的所有歌手 |
| **🗑️ 删除/取消** | `删除周杰伦` | 取消关注指定歌手 |
| **🤖 获取帮助** | `菜单` / `帮助` | 查看所有可用指令 |

## 🛠️ 技术栈

*   **Backend**: Python, FastAPI, SQLAlchemy, APScheduler
*   **Frontend**: Vue 3, Vite, Naive UI, Axios
*   **Database**: SQLite
*   **Container**: Docker

## 🤝 贡献 (Contributing)

欢迎提交 Issue 和 Pull Request！

1.  Fork 本项目
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交改动 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  提交 Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
