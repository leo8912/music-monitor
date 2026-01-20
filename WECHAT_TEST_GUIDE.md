# 微信功能本地测试指南

## 概述
`test_wechat_local.py` 是一个完整的微信企业号功能测试工具，可以在本地模拟微信回调，无需真实的公网地址和微信服务器交互。

## 前提条件

### 1. 配置 WeChat 信息
编辑 `config.yaml`，确保以下配置存在：

```yaml
notify:
  wecom:
    enabled: true
    corpid: "ww6xxxxxxxxxxxxx"      # 企业ID
    corpsecret: "xxxxxxxxxxxxxxxx"  # 应用Secret
    agentid: "1000002"              # 应用AgentID
    token: "YourToken123"           # 自定义Token（随机字符串）
    encoding_aes_key: "YourBase64AESKey..."  # 43位Base64字符
```

**获取方式**：
- 登录企业微信管理后台：https://work.weixin.qq.com
- 进入 应用管理 → 自建应用
- 查看应用详情获取上述参数

### 2. 启动服务

**方式一：本地开发**
```bash
# 激活虚拟环境
.venv\Scripts\activate

# 启动服务
python main.py

# 服务运行在 http://127.0.0.1:8000
```

**方式二：Docker 容器**
```bash
# 启动容器
docker compose -f docker-compose.test.yml up -d

# 查看日志
docker logs -f music-monitor-test

# 服务运行在 http://127.0.0.1:18001
```

## 使用测试工具

### 启动测试工具
```bash
# 激活虚拟环境（如果还没激活）
.venv\Scripts\activate

# 运行测试工具
python test_wechat_local.py
```

### 主菜单界面
```
============================================================
 📱 微信企业号本地测试工具
============================================================
目标地址: http://127.0.0.1:18001
Corp ID: ww6582ddf3c02fd7fc
Token: YourT***
============================================================

请选择测试场景:
  1. 🎤 测试歌手搜索
  2. ➕ 测试添加歌手
  3. 🎵 测试歌曲下载
  4. 💬 交互模式 (自由输入)
  5. 🔧 切换目标地址
  q. 退出

选择 (1-5/q):
```

## 测试场景

### 场景1: 测试歌手搜索 🎤

**操作流程**:
1. 选择 `1`
2. 按回车依次测试预设歌手（任素汐、周杰伦、李荣浩）

**预期结果**:
```
📤 发送消息: 任素汐
   用户ID: TestUser001

📩 图文回复 (2 项):
  1. 任素汐
     来源: 网易 / QQ
     🔗 https://music.163.com
  2. 其他同名歌手...
```

**验证点**:
- ✅ 返回图文消息（News类型）
- ✅ 包含歌手头像
- ✅ 显示来源平台（网易/QQ）
- ✅ 查看Docker日志确认 `QQ Search Result: X artists found`

### 场景2: 测试添加歌手 ➕

**操作流程**:
1. 选择 `2`
2. 输入歌手名（如 `任素汐`）
3. 等待搜索结果
4. 输入序号（如 `1`）选择歌手

**预期结果**:
```
📤 发送消息: 任素汐
📩 图文回复 (2 项): ...

📤 发送消息: 1
📩 文本回复:
⏳ 正在处理 '任素汐' 的全平台监控添加...

（稍后收到）
✅ 已添加 '任素汐' 到监控：
网易云 / QQ音乐
🚀 正在触发全网同步...
```

**验证点**:
- ✅ 成功添加到 `config/config.yaml`
- ✅ 无 "系统错误" 提示
- ✅ 日志显示 `run_check` 被触发
- ✅ 刷新 http://localhost:18001 查看歌手列表

### 场景3: 测试歌曲下载 🎵

**操作流程**:
1. 选择 `3`
2. 输入歌曲名（如 `成都`）
3. 等待搜索结果
4. 输入序号下载

**预期结果**:
```
📤 发送消息: 下载 成都
📩 文本回复:
🔎 找到以下歌曲（回复序号下载）：
1. 🎵 成都 - 赵雷
2. 🎵 成都 - 其他版本
...

📤 发送消息: 1
📩 文本回复:
🚀 已收到下载请求, 正在处理...

（下载完成后）
📩 图文回复 (1 项):
  1. 下载完成: 成都
     歌手: 赵雷
     点击立即播放 (72小时有效)
     🔗 http://.../#/mobile/play?id=...&sign=...
```

**验证点**:
- ✅ 返回带签名的播放链接（Magic Link）
- ✅ 链接包含 `sign` 和 `expires` 参数
- ✅ 点击链接打开移动端播放器
- ✅ 文件保存到 `config/favorites/`

### 场景4: 交互模式 💬

**用途**: 自由测试任意指令

**操作**: 
```
选择 (1-5/q): 4

🔧 输入指令: 列表
📩 文本回复: （显示当前监控的歌手）

🔧 输入指令: 删除 任素汐
📩 文本回复: （确认删除）

🔧 输入指令: q
（返回主菜单）
```

### 场景5: 切换目标 🔧

当需要测试不同环境时使用：

```
选择 (1-5/q): 5

当前目标:
  1. http://127.0.0.1:8000  (本地开发)
  2. http://127.0.0.1:18001 (Docker容器)
  3. 自定义

选择 (1-3): 1
✅ 已切换到: http://127.0.0.1:8000
```

## 高级调试

### 查看实时日志

**Docker 容器**:
```bash
# 实时跟踪
docker logs -f music-monitor-test

# 最近 50 行
docker logs --tail 50 music-monitor-test

# 保存到文件
docker logs music-monitor-test > logs.txt
```

**本地开发**:
查看控制台输出或 `config/logs/application.log`

### 调试特定错误

**问题: QQ 音乐搜索结果为空**

查看日志中的关键信息：
```bash
docker logs music-monitor-test | findstr "QQ Search"
```

期望输出：
```
INFO - QQ Search Result: 2 artists found
```

如果为 `0` 或有 `ERROR`，可能是：
- ✅ 网络问题（检查代理设置）
- ✅ API 限流（稍后重试）
- ✅ 依赖库版本问题（更新 `qqmusic_api`）

**问题: 添加歌手报错**

查看完整堆栈：
```bash
docker logs music-monitor-test | findstr "Bg add artist error"
```

常见原因：
- 配置文件格式错误（`config.yaml` 中 `monitor` 为空）
- 权限问题（Docker 无法写入配置文件）

### 手动验证修复

**验证1: 刷新页面不报错**
```powershell
# 直接调用 API
curl http://localhost:18001/api/history

# 期望: 状态码 200 或 401（未登录）
# 不应该: 500 (Internal Server Error)
```

**验证2: 配置文件正确保存**
```powershell
# 查看容器内配置
docker exec music-monitor-test cat /config/config.yaml

# 应包含新添加的歌手信息
```

## 常见问题 FAQ

**Q: 测试工具报 "❌ 错误: 缺少 WeChat 配置"**

A: 确保 `config.yaml` 中 `notify.wecom` 部分已配置完整。

**Q: 发送消息后无响应**

A: 检查服务是否运行：
```bash
curl http://localhost:18001/api/status
```

**Q: 图文消息解析失败**

A: 这是正常的，wechatpy 可能对 News 消息解析有限制，只要逻辑正确执行即可。

**Q: Docker 容器日志显示 "系统错误"**

A: 查看完整错误信息：
```bash
docker logs music-monitor-test | tail -100
```

常见错误通常是路径或权限问题。

## 生产环境测试

本地测试通过后，部署到 NAS 并使用真实微信回调：

1. **配置回调 URL**
   ```yaml
   notify:
     wecom:
       callback_url: https://your-domain.com/api/wecom/callback
   ```

2. **内网穿透**（可选，测试用）
   ```bash
   # 使用 frp 或 ngrok
   ngrok http 18001
   ```

3. **验证步骤**
   - 在企业微信应用中设置回调URL
   - 发送测试消息
   - 查看服务器日志确认收到回调

---

**提示**: 测试工具会自动处理加密/解密和签名验证，确保与真实微信服务器行为一致。
