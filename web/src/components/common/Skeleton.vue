<template>
  <div class="skeleton" :class="[shape, { 'is-animated': animated }]" :style="style"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  width: { type: [String, Number], default: '100%' },
  height: { type: [String, Number], default: '100%' },
  shape: { type: String, default: 'rect', validator: (v: string) => ['rect', 'circle', 'text'].includes(v) },
  animated: { type: Boolean, default: true }
})

const style = computed(() => ({
  width: typeof props.width === 'number' ? `${props.width}px` : props.width,
  height: typeof props.height === 'number' ? `${props.height}px` : props.height
}))
</script>

<style scoped>
.skeleton {
  background-color: var(--sp-card-hover);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.skeleton.circle {
  border-radius: 50%;
}

.skeleton.text {
  height: 1em;
  margin-bottom: 0.5em;
  border-radius: 4px;
}

.skeleton.is-animated::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.05) 50%,
    transparent 100%
  );
  animation: loading 1.5s infinite;
}

@keyframes loading {
  100% {
    transform: translateX(100%);
  }
}
</style>
