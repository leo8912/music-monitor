<script setup>
/**
 * 设置项下拉选择控件
 */
defineProps({
    modelValue: { type: [String, Number], default: '' },
    label: { type: String, required: true },
    options: { 
        type: Array, 
        required: true 
        // 格式: [{ value: 'xxx', label: '显示文本' }]
    },
    disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
    <div class="setting-row" :class="{ disabled }">
        <span class="setting-label">{{ label }}</span>
        <div class="select-wrapper">
            <select 
                :value="modelValue"
                :disabled="disabled"
                class="setting-select"
                @change="emit('update:modelValue', $event.target.value)"
            >
                <option 
                    v-for="opt in options" 
                    :key="opt.value" 
                    :value="opt.value"
                >
                    {{ opt.label }}
                </option>
            </select>
            <span class="select-arrow">›</span>
        </div>
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

.setting-label {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary, #1d1d1f);
}

.select-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}

.setting-select {
    appearance: none;
    -webkit-appearance: none;
    border: none;
    background: transparent;
    font-size: 14px;
    color: var(--text-secondary, #86868b);
    padding: 8px 24px 8px 12px;
    cursor: pointer;
    text-align: right;
}

.setting-select:focus {
    outline: none;
}

.select-arrow {
    position: absolute;
    right: 4px;
    font-size: 16px;
    color: var(--text-secondary, #86868b);
    pointer-events: none;
    transform: rotate(90deg);
}

/* 深色模式 */
:root[data-theme="dark"] .setting-label {
    color: #f5f5f7;
}

:root[data-theme="dark"] .setting-row {
    border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .setting-select {
    color: #98989D;
}
</style>
