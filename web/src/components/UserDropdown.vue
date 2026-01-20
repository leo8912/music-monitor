<script setup>
/**
 * 👤 用户下拉菜单组件
 * 整合头像、用户名及常用系统操作
 */
import { h, computed } from 'vue'
import { NDropdown, NAvatar, NIcon, NText } from 'naive-ui'
import { 
    PersonCircleOutline, 
    SettingsOutline, 
    LogOutOutline,
    ChevronDownOutline 
} from '@vicons/ionicons5'

const props = defineProps({
    username: { type: String, default: 'My Music' },
    avatar: { type: String, default: '' },
    isAdmin: { type: Boolean, default: true }
})

const emit = defineEmits(['select', 'logout', 'open-settings', 'open-profile'])

const renderIcon = (icon) => {
    return () => h(NIcon, null, { default: () => h(icon) })
}

const options = [
    {
        label: '个人中心',
        key: 'profile',
        icon: renderIcon(PersonCircleOutline)
    },
    {
        label: '系统设置',
        key: 'settings',
        icon: renderIcon(SettingsOutline)
    },
    {
        type: 'divider'
    },
    {
        label: '退出登录',
        key: 'logout',
        icon: renderIcon(LogOutOutline)
    }
]

const handleSelect = (key) => {
    if (key === 'settings') {
        emit('open-settings')
    } else if (key === 'profile') {
        emit('open-profile')
    } else if (key === 'logout') {
        emit('logout')
    }
    emit('select', key)
}
</script>

<template>
    <n-dropdown trigger="click" :options="options" @select="handleSelect">
        <div class="user-trigger">
            <n-avatar 
                round 
                :size="28" 
                :src="avatar" 
                class="user-avatar"
                v-if="avatar"
            />
            <n-avatar round :size="28" class="user-avatar" v-else>
                <n-icon><PersonCircleOutline /></n-icon>
            </n-avatar>
            <span class="username">{{ username }}</span>
            <n-icon size="14" class="arrow-icon">
                <ChevronDownOutline />
            </n-icon>
        </div>
    </n-dropdown>
</template>

<style scoped>
.user-trigger {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px 4px 4px;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    user-select: none;
    background: transparent; /* Changed from grey */
    border: 1px solid transparent;
}

.user-trigger:hover {
    background: rgba(0, 0, 0, 0.04);
}

.username {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.arrow-icon {
    color: var(--text-tertiary);
    transition: transform 0.2s;
}

/* 深色模式适配 */
/* 深色模式适配 */
:root[data-theme="dark"] .user-trigger {
    background: transparent;
}

:root[data-theme="dark"] .user-trigger:hover {
    background: rgba(255, 255, 255, 0.1);
}
</style>
