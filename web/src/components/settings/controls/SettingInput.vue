<script setup>
/**
 * 设置项输入框控件
 */
defineProps({
    modelValue: { type: [String, Number], default: '' },
    label: { type: String, required: true },
    type: { type: String, default: 'text' }, // text, number, password
    placeholder: { type: String, default: '' },
    suffix: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
    description: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
    <div class="setting-row-wrapper" :class="{ disabled }">
        <div class="setting-row">
            <span class="setting-label">{{ label }}</span>
            <div class="input-wrapper">
                <input 
                    :type="type"
                    :value="modelValue"
                    :placeholder="placeholder"
                    :disabled="disabled"
                    class="setting-input"
                    @input="emit('update:modelValue', type === 'number' ? Number($event.target.value) : $event.target.value)"
                />
                <span v-if="suffix" class="input-suffix">{{ suffix }}</span>
            </div>
        </div>
        <div v-if="description" class="setting-description">
            {{ description }}
        </div>
    </div>
</template>

<style scoped>
.setting-row-wrapper {
    padding: 14px 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.setting-row-wrapper:last-child {
    border-bottom: none;
}

.setting-row-wrapper.disabled {
    opacity: 0.5;
    pointer-events: none;
}

.setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.setting-label {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary, #1d1d1f);
    flex-shrink: 0;
}

.input-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
}

.setting-input {
    width: 300px;
    padding: 8px 12px;
    font-size: 14px;
    border: none;
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.04);
    color: var(--text-primary, #1d1d1f);
    text-align: right;
    transition: all 0.15s;
}

.setting-input:focus {
    outline: none;
    background: rgba(0, 0, 0, 0.06);
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.setting-input[type="number"] {
    -moz-appearance: textfield;
}

.setting-input[type="number"]::-webkit-outer-spin-button,
.setting-input[type="number"]::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
}

.input-suffix {
    font-size: 14px;
    color: var(--text-secondary, #86868b);
}

.setting-description {
    font-size: 12px;
    color: var(--text-secondary, #86868b);
    margin-top: 6px;
    line-height: 1.4;
    white-space: pre-wrap;
}

/* 深色模式 */
:root[data-theme="dark"] .setting-label {
    color: #f5f5f7;
}

:root[data-theme="dark"] .setting-row-wrapper {
    border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .setting-input {
    background: rgba(255, 255, 255, 0.08);
    color: #f5f5f7;
}

:root[data-theme="dark"] .setting-input:focus {
    background: rgba(255, 255, 255, 0.12);
}
</style>
