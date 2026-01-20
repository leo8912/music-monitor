<script setup>
/**
 * 设置项开关控件
 * 模拟 iOS 风格的开关
 */
const props = defineProps({
    modelValue: { type: Boolean, default: false },
    label: { type: String, required: true },
    description: { type: String, default: '' },
    disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
    <div class="setting-row" :class="{ disabled }">
        <div class="setting-info">
            <span class="setting-label">{{ label }}</span>
            <span v-if="description" class="setting-desc">{{ description }}</span>
        </div>
        <label class="ios-switch" :class="{ checked: modelValue, disabled }">
            <input 
                type="checkbox" 
                :checked="modelValue" 
                :disabled="disabled"
                @change="emit('update:modelValue', $event.target.checked)"
            />
            <span class="switch-slider"></span>
        </label>
    </div>
</template>

<style scoped>
.setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.setting-row:last-child {
    border-bottom: none;
}

.setting-row.disabled {
    opacity: 0.5;
    pointer-events: none;
}

.setting-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}

.setting-label {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary, #1d1d1f);
}

.setting-desc {
    font-size: 12px;
    color: var(--text-secondary, #86868b);
}

/* iOS 风格开关 */
.ios-switch {
    position: relative;
    width: 51px;
    height: 31px;
    flex-shrink: 0;
    cursor: pointer;
}

.ios-switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.switch-slider {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #E9E9EB;
    border-radius: 31px;
    transition: all 0.25s ease;
}

.switch-slider::before {
    content: '';
    position: absolute;
    width: 27px;
    height: 27px;
    left: 2px;
    bottom: 2px;
    background: white;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
    transition: all 0.25s ease;
}

.ios-switch.checked .switch-slider {
    background: #34C759; /* iOS 绿色 */
}

.ios-switch.checked .switch-slider::before {
    transform: translateX(20px);
}

.ios-switch.disabled .switch-slider {
    opacity: 0.6;
}

/* 深色模式 */
:root[data-theme="dark"] .setting-label {
    color: #f5f5f7;
}

:root[data-theme="dark"] .setting-row {
    border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .switch-slider {
    background: #39393D;
}

:root[data-theme="dark"] .ios-switch.checked .switch-slider {
    background: #30D158; /* iOS Dark Mode Green */
    opacity: 1;
}
</style>
