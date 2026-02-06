#!/bin/bash
set -e

# 获取 PUID 和 PGID，默认为 0（root）
PUID=${PUID:-0}
PGID=${PGID:-0}

# 设置默认权限掩码 (002 => 775/664)
# 这样生成的文件对组用户(通常是NAS管理员组)也是可读写的，更优雅地解决权限问题
umask 002

echo "Starting with PUID=${PUID} PGID=${PGID}"



# 初始化配置文件 (如果不存在)
# 无论是否为 root 用户，都需要确保 /config/config.yaml 存在
if [ ! -f /config/config.yaml ] && [ -f /app/config.example.yaml ]; then
    echo "Initializing config file..."
    cp /app/config.example.yaml /config/config.yaml
fi

# 如果 PUID 不是 0 (root)，则创建用户并切换
if [ "$PUID" != "0" ]; then
    # 创建组（如果不存在）
    if ! getent group abc >/dev/null; then
        groupadd -g "$PGID" abc
    fi

    # 创建用户（如果不存在）
    if ! getent passwd abc >/dev/null; then
        useradd -u "$PUID" -g "$PGID" -m -s /bin/bash abc
    fi

    # 更改目录权限
    echo "Updating permissions..."
    chown -R abc:abc /app /config /audio_cache /favorites /library
    
    echo "Running database migrations..."
    gosu abc alembic upgrade head

    # 切换用户运行
    echo "Running as user: abc ($PUID:$PGID)"
    exec gosu abc "$@"
else
    # Root 运行
    echo "Running database migrations (root)..."
    alembic upgrade head

    echo "Running as root"
    exec "$@"
fi
