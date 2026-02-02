#!/bin/bash
set -e

# 获取 PUID 和 PGID，默认为 0（root）
PUID=${PUID:-0}
PGID=${PGID:-0}

echo "Starting with PUID=${PUID} PGID=${PGID}"

echo "🔍 ROOT DEBUG: Listing site-packages:"
ls -la /usr/local/lib/python3.11/site-packages | head -n 20
python -c "import site; print(site.getsitepackages())"
python -c "import yaml; print('✅ Root can import yaml')" || echo "❌ Root CANNOT import yaml"

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
    chown -R abc:abc /app /config /audio_cache /favorites
    
    # 切换用户运行
    echo "Running as user: abc ($PUID:$PGID)"
    exec gosu abc "$@"
else
    # Root 运行
    echo "Running as root"
    exec "$@"
fi
