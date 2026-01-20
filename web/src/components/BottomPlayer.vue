<template>
  <div class="bottom-player-wrapper" v-if="audioUrl || isLoading">
    <!-- 悬浮艺术歌词 (Dock 上方) -->
    <div class="floating-lyrics">
      <div class="lyrics-container">
        <transition-group name="lyric-scroll" tag="div" class="lyrics-inner">
          <div v-for="line in visibleLyrics" :key="line.time" 
               class="lyric-item" 
               :class="{ 'current': line.time === currentLyricTime }"
               :style="{ '--prog': line.time === currentLyricTime ? (lyricProgress + '%') : '0%' }">
            {{ line.text }}
          </div>
        </transition-group>
      </div>
    </div>

    <!-- 播放器 Dock -->
    <div class="player-dock">
      <!-- 频谱可视化背景 -->
      <canvas ref="visualizerCanvas" class="visualizer-canvas"></canvas>
      
      <!-- 交互式进度条 -->
      <div class="seek-bar-container" @click="handleSeek" @mousemove="handleSeekHover" @mouseleave="handleSeekLeave">
        <div class="seek-bar-bg"></div>
        <div class="seek-bar-fill" :style="{ width: progress + '%' }">
          <div class="seek-bar-thumb"></div>
        </div>
      </div>

      <!-- 控制栏 -->
      <div class="control-bar">
        <!-- 左：封面 + 歌曲信息 -->
        <div class="left-section">
          <div class="cover-wrapper" :class="{ 'is-loading': isLoading }">
            <img :src="info.cover || 'https://ui-avatars.com/api/?name=M&size=96&background=random'" class="album-cover" />
            <div class="loading-overlay" v-if="isLoading">
              <div class="mini-spinner"></div>
            </div>
          </div>
          <div class="song-info">
            <div class="song-title-row">
              <div class="song-title" :title="info.title">{{ info.title || '未知歌曲' }}</div>
              <div class="song-title" :title="info.title">{{ info.title || '未知歌曲' }}</div>
              <!-- Heart moved to right section -->
              <button class="action-btn repair-btn" @click.stop="$emit('repair')" title="歌曲错误？点击修复"><i class="fas fa-exclamation-triangle"></i></button>
            </div>
            <div class="song-artist" :title="info.author || info.artist">{{ info.author || info.artist || '未知歌手' }}</div>
          </div>
        </div>

        <!-- 中：播放控制 -->
        <div class="center-section">
          <button @click="$emit('prev')" title="上一首"><i class="fas fa-backward-step"></i></button>
          <button class="btn-play" @click="togglePlay" :disabled="isLoading">
            <i :class="isLoading ? 'fas fa-spinner fa-spin' : (isPlaying ? 'fas fa-pause' : 'fas fa-play')"></i>
          </button>
          <button @click="$emit('next')" title="下一首"><i class="fas fa-forward-step"></i></button>
          <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
        </div>

        <!-- 右：音量 -->
        <div class="right-section">
          <!-- 收藏按钮移至此处, 靠近中间 -->
          <button class="action-btn fav-btn is-in-right" @click.stop="$emit('toggle-favorite')" :title="info.is_favorite ? '取消收藏' : '添加收藏'">
            <i :class="info.is_favorite ? 'fas fa-heart' : 'far fa-heart'"></i>
          </button>
          
          <span class="quality-badge" v-if="(info.quality || info.audio_quality || 0) >= 320">{{ (info.quality || info.audio_quality || 0) >= 999 ? 'Hi-Res' : 'HQ' }}</span>
          <button class="vol-btn" @click="toggleMute"><i :class="volumeIcon"></i></button>
          <div class="vol-slider-container">
             <input type="range" class="vol-slider" min="0" max="100" :value="isMuted ? 0 : volume" @input="handleVolumeChange" />
          </div>
        </div>
      </div>
      
      <audio ref="audioRef" :src="audioUrl" autoplay crossorigin="anonymous"
        @timeupdate="onTimeUpdate" @loadedmetadata="onLoadedMetadata" @ended="onEnded" @error="onError"></audio>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue';
import axios from 'axios';

const props = defineProps({
  audioUrl: String,
  info: { type: Object, default: () => ({}) },
  source: String,
  mediaId: String,
  isLoading: Boolean
});

const emit = defineEmits(['play', 'pause', 'next', 'prev', 'ended', 'error', 'repair', 'toggle-favorite']);

const audioRef = ref(null);
const visualizerCanvas = ref(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const progress = ref(0);
const volume = ref(80);
const isMuted = ref(false);
const lyrics = ref([]);
const currentLyricIndex = ref(-1);

let audioContext = null;
let analyser = null;
let dataArray = null;
let animationId = null;

const volumeIcon = computed(() => {
  if (isMuted.value || volume.value === 0) return 'fas fa-volume-xmark';
  if (volume.value < 50) return 'fas fa-volume-low';
  return 'fas fa-volume-high';
});

const currentLyricTime = computed(() => {
  return currentLyricIndex.value >= 0 && lyrics.value[currentLyricIndex.value] 
    ? lyrics.value[currentLyricIndex.value].time : -1;
});

const visibleLyrics = computed(() => {
  if (lyrics.value.length === 0) return [];
  const idx = currentLyricIndex.value;
  // 显示当前行和下一行
  const showIdx = idx < 0 ? 0 : idx;
  return lyrics.value.slice(showIdx, showIdx + 2);
});

const initVisualizer = () => {
  if (!audioRef.value || audioContext) return;
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.75;
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    // Check if source node already created to avoid error
    // Note: createMediaElementSource can only be called once per element
    // We assume it's clean here for simplicity in this context
    const source = audioContext.createMediaElementSource(audioRef.value);
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    startDrawing();
  } catch (e) { 
    // console.warn('频谱初始化(可能是重复初始化):', e); 
    if (audioContext && analyser) startDrawing(); // Retry drawing if context exists
  }
};

const startDrawing = () => {
    if (!visualizerCanvas.value || !analyser) return;
    const canvas = visualizerCanvas.value;
    const ctx = canvas.getContext('2d');
    
    const draw = () => {
        animationId = requestAnimationFrame(draw);
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
        analyser.getByteFrequencyData(dataArray);
        ctx.clearRect(0, 0, rect.width, rect.height);
        
        const barCount = 32;
        const totalBars = barCount * 2;
        const barWidth = rect.width / totalBars;
        const centerX = rect.width / 2;
        const gap = 2;
        
        for (let i = 0; i < barCount; i++) {
            const dataIndex = Math.floor(i * dataArray.length / barCount);
            const value = dataArray[dataIndex] || 0;
            const barHeight = (value / 255) * rect.height * 0.7;
            
            const gradient = ctx.createLinearGradient(0, rect.height, 0, rect.height - barHeight);
            // 蓝色系频谱 - 提亮
            gradient.addColorStop(0, 'rgba(130, 220, 255, 1.0)');   // Lighter, brighter Blue
            gradient.addColorStop(0.5, 'rgba(0, 140, 255, 0.8)');   // Vibrant Apple Blue
            gradient.addColorStop(1, 'rgba(0, 122, 255, 0.3)');
            ctx.fillStyle = gradient;
            
            ctx.fillRect(centerX + i * barWidth + gap / 2, rect.height - barHeight, barWidth - gap, barHeight);
            ctx.fillRect(centerX - (i + 1) * barWidth + gap / 2, rect.height - barHeight, barWidth - gap, barHeight);
        }
        
        ctx.setTransform(1, 0, 0, 1, 0, 0);
    };
    draw();
};

watch(() => props.audioUrl, (newVal) => {
  if (newVal) {
    isPlaying.value = true;
    fetchLyrics();
    currentLyricIndex.value = -1;
    nextTick(() => {
      if (!audioContext) initVisualizer();
      else if (audioContext.state === 'suspended') audioContext.resume();
    });
  } else {
    isPlaying.value = false;
    currentTime.value = 0;
    progress.value = 0;
    lyrics.value = [];
  }
});

// ...
let uiAnimationId = null;

const uiLoop = () => {
  uiAnimationId = requestAnimationFrame(uiLoop);
  
  if (!isPlaying.value || !audioRef.value) return;
  
  const time = audioRef.value.currentTime;
  // 60FPS Smooth Progress Bar
  if (duration.value > 0) {
     progress.value = (time / duration.value) * 100;
  }
  
  // 60FPS Karaoke Calculation
  if (lyrics.value.length) {
      let idx = -1;
      // Fast lookup optimization could be added, but loop is small usually
      for (let i = 0; i < lyrics.value.length; i++) {
        if (lyrics.value[i].time <= time) idx = i; else break;
      }
      
      if (idx !== currentLyricIndex.value) {
        currentLyricIndex.value = idx;
        lyricProgress.value = 0;
      }
      
      if (idx >= 0) {
        const currentLine = lyrics.value[idx];
        const nextLine = lyrics.value[idx + 1];
        const endTime = nextLine ? nextLine.time : (currentLine.time + 5);
        const duration = endTime - currentLine.time;
        const elapsed = time - currentLine.time;
        let p = (elapsed / duration) * 100;
        if (p < 0) p = 0; if (p > 100) p = 100;
        lyricProgress.value = p;
      }
  }
};

watch(() => props.audioUrl, (newVal) => {
  if (newVal) {
    isPlaying.value = true;
    fetchLyrics();
    currentLyricIndex.value = -1;
     // Resume visualizer if needed
    nextTick(() => {
      if (!audioContext) initVisualizer();
      else if (audioContext.state === 'suspended') audioContext.resume();
    });
  } else {
    isPlaying.value = false;
    currentTime.value = 0;
    progress.value = 0;
    lyrics.value = [];
  }
});



const lyricProgress = ref(0);

const fetchLyrics = async () => {
  if (!props.source || !props.mediaId) { lyrics.value = []; return; }
  try {
    const params = new URLSearchParams();
    if (props.info?.title) params.append('title', props.info.title);
    if (props.info?.author || props.info?.artist) params.append('artist', props.info.author || props.info.artist);
    const url = `/api/lyric/${props.source}/${props.mediaId}${params.toString() ? '?' + params.toString() : ''}`;
    const res = await axios.get(url);
    lyrics.value = res.data?.lyric ? parseLrc(res.data.lyric) : [];
    console.log(`歌词来源: ${res.data?.source || 'unknown'}`);
  } catch { lyrics.value = []; }
};

const parseLrc = (lrcText) => {
  const result = [];
  const reg = /\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\]/;
  for (const line of lrcText.split('\n')) {
    const m = reg.exec(line);
    if (m) {
      const time = parseInt(m[1]) * 60 + parseInt(m[2]) + (m[3] ? parseInt(m[3].padEnd(3, '0')) / 1000 : 0);
      const text = line.replace(reg, '').trim();
      if (text) result.push({ time, text });
    }
  }
  return result.sort((a, b) => a.time - b.time);
};

const togglePlay = () => {
  if (!audioRef.value) return;
  if (audioContext?.state === 'suspended') audioContext.resume();
  if (isPlaying.value) { audioRef.value.pause(); isPlaying.value = false; emit('pause'); }
  else { audioRef.value.play().then(() => { isPlaying.value = true; emit('play'); }).catch(console.error); }
};

const onTimeUpdate = () => {
  if (!audioRef.value) return;
  currentTime.value = audioRef.value.currentTime;
  if (duration.value > 0) progress.value = (currentTime.value / duration.value) * 100;
};

const onLoadedMetadata = () => {
  duration.value = audioRef.value.duration;
  if (audioRef.value) audioRef.value.volume = volume.value / 100;
  if (!audioContext) initVisualizer();
};

const onEnded = () => { isPlaying.value = false; emit('ended'); };
const onError = (e) => { console.error("Audio Error:", e); emit('error', e); };

const handleSeek = (e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  if (audioRef.value && duration.value) audioRef.value.currentTime = ((e.clientX - rect.left) / rect.width) * duration.value;
};

const handleSeekHover = (e) => {
  // Can add hover logic here if needed, currently CSS handles hover styles
};
const handleSeekLeave = () => {
};

const handleVolumeChange = (e) => {
  volume.value = parseInt(e.target.value);
  isMuted.value = false;
  if (audioRef.value) audioRef.value.volume = volume.value / 100;
};

const toggleMute = () => {
  isMuted.value = !isMuted.value;
  if (audioRef.value) audioRef.value.volume = isMuted.value ? 0 : volume.value / 100;
};

const formatTime = (s) => s ? `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}` : '0:00';

onMounted(() => {
    // Start UI loop for smooth animation
    uiLoop();
    
    // Attempt init once
    document.addEventListener('click', () => {
        if (audioContext && audioContext.state === 'suspended') audioContext.resume();
    }, { once: true });
});
onUnmounted(() => { 
  if (animationId) cancelAnimationFrame(animationId);
  if (uiAnimationId) cancelAnimationFrame(uiAnimationId);
  if (audioContext) audioContext.close(); 
});
</script>

<style scoped>
.bottom-player-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  pointer-events: none;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 12px;
}

/* 🍎 双行滚动歌词 */
.floating-lyrics {
  pointer-events: none;
  margin-bottom: 12px;
  text-align: center;
  height: 90px; /* 增加高度容纳两行 */
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 100%);
  -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 100%);
}

.lyrics-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  width: 100%;
}

.lyric-item {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 20px;
  /* 预读行改为亮蓝色 */
  color: #5AC8FA; 
  opacity: 0.9;
  transition: all 0.6s cubic-bezier(0.25, 1, 0.5, 1);
  white-space: nowrap;
}

.lyric-item.current {
  font-size: 32px;
  font-weight: 900;
  height: 50px;
  opacity: 1;
  /* 卡拉OK 效果: 动态梯度 */
  background-image: linear-gradient(90deg, #0055ff 0%, #0088ff var(--prog), #5AC8FA var(--prog), #5AC8FA 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  
  filter: drop-shadow(0 0 10px rgba(0, 100, 255, 0.5));
}

/* 碎纸机/消散动画 - 优化版：上浮消散，不重叠 */
.lyric-scroll-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  /* 0.8s 缓慢消散 */
  animation: vanish 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  transform-origin: center center;
}

@keyframes vanish {
  0% {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
  100% {
    opacity: 0;
    /* 向上漂浮 + 缩小 (避免遮挡) */
    transform: translateY(-30px) scale(0.9);
    filter: blur(10px); /* 强模糊模拟消散 */
    /* 淡淡的条纹破碎感 */
    mask-image: repeating-linear-gradient(90deg, black 0px, black 2px, transparent 2px, transparent 8px);
    -webkit-mask-image: repeating-linear-gradient(90deg, black 0px, black 2px, transparent 2px, transparent 8px);
  }
}

.lyric-scroll-move,
.lyric-scroll-enter-active {
  transition: all 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.lyric-scroll-enter-from {
  opacity: 0;
  transform: translateY(100%);
}

/* Player Dock - 增加透明度 */
.player-dock {
  pointer-events: auto;
  position: relative;
  width: calc(100% - 48px);
  max-width: 900px;
  height: 64px;
  /* 🖤 通透深黑 */
  background: rgba(10, 10, 15, 0.65); 
  backdrop-filter: blur(60px) saturate(180%);
  -webkit-backdrop-filter: blur(60px) saturate(180%);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: visible;
  box-shadow: 
    0 24px 60px rgba(0,0,0,0.8),
    0 0 0 1px rgba(255,255,255,0.05);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.visualizer-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  border-radius: 20px;
  opacity: 0.5;
}

/* 交互式进度条 - 极简模式 */
.seek-bar-container {
  position: absolute;
  top: -4px; /* 稍微贴近边缘 */
  left: 12px;
  right: 12px;
  height: 10px; /* 小的一块感应区域 */
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.seek-bar-bg {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px; /* 极简 2px */
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  transition: height 0.2s ease, background 0.2s;
}

.seek-bar-fill {
  position: absolute;
  left: 0;
  height: 2px; /* 极简 2px */
  /* 💙 蓝色进度条 */
  background: #0A84FF; 
  border-radius: 2px;
  pointer-events: none;
  transition: width 0.1s linear, height 0.2s ease, background 0.2s;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.seek-bar-thumb {
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  transform: scale(0); /* 默认完全隐藏 */
  transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  margin-right: -5px;
}

/* Hover 交互效果：变高，变亮，显示滑块 */
.seek-bar-container:hover .seek-bar-bg {
  height: 4px;
  background: rgba(255,255,255,0.2);
}
.seek-bar-container:hover .seek-bar-fill {
  height: 4px;
  background: #007AFF; /* 悬停时更亮 */
}
.seek-bar-container:hover .seek-bar-thumb {
  transform: scale(1.2); /* 出现并略微放大 */
}

/* 控制栏 */
.control-bar {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 2;
  margin-top: 4px;
}

/* Left Section */
.left-section { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
.album-cover { 
  width: 42px; height: 42px; 
  border-radius: 8px; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.4); 
  border: 1px solid rgba(255,255,255,0.1);
}

.song-info { display: flex; flex-direction: column; justify-content: center; }
.song-title-row { display: flex; align-items: center; gap: 8px; }
.song-title { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 2px; letter-spacing: 0.2px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* .btn-play ... */

.action-btn { background: none; border: none; font-size: 14px; cursor: pointer; padding: 4px; transition: all 0.2s; opacity: 0.6; }
.action-btn:hover { opacity: 1; transform: scale(1.1); }

.fav-btn { color: #FF2D55; font-size: 16px; margin-right: 8px; } /* Slightly larger in right section */
.fav-btn:hover { filter: drop-shadow(0 0 8px rgba(255, 45, 85, 0.4)); transform: scale(1.15); }
.fav-btn.is-in-right { padding: 6px; }

.repair-btn { color: #FF9500; font-size: 12px; }
.repair-btn:hover { filter: drop-shadow(0 0 5px rgba(255, 149, 0, 0.5)); }


.song-artist { font-size: 12px; color: rgba(255,255,255,0.55); letter-spacing: 0.2px; }

/* Center Controls */
.center-section { display: flex; align-items: center; gap: 24px; position: absolute; left: 50%; transform: translateX(-50%); }
.center-section button { color: rgba(255,255,255,0.7); font-size: 18px; padding: 8px; transition: all 0.2s; background: none; border: none; cursor: pointer; }
.center-section button:hover { color: #fff; transform: scale(1.15); }

.btn-play {
  width: 40px !important; height: 40px !important;
  font-size: 16px !important;
  box-shadow: 0 4px 16px rgba(255,255,255,0.2);
  background: #fff !important; color: #000 !important; border-radius: 50%;
  display: flex !important; align-items: center; justify-content: center;
  overflow: hidden; /* Prevent overflow */
}
.btn-play i {
    display: block;
    line-height: 1;
    text-align: center;
    width: auto;
    color: #000 !important; /* Force black icon */
}
.btn-play:hover { background: #E0E0E0 !important; transform: scale(1.05) !important; box-shadow: 0 6px 20px rgba(255,255,255,0.4); }
.btn-play:disabled { opacity: 0.8; cursor: wait; transform: none !important; }

/* Loading State for Cover */
.cover-wrapper { position: relative; width: 42px; height: 42px; }
.cover-wrapper.is-loading .album-cover { filter: blur(2px) grayscale(0.4); transform: scale(0.95); }
.loading-overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 2; }
.mini-spinner {
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.5);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Right Section */
.right-section { display: flex; align-items: center; gap: 12px; flex: 1; justify-content: flex-end; }
.time-display { font-size: 12px; color: rgba(255,255,255,0.3); font-family: 'SF Mono', 'Menlo', monospace; font-weight: 500; margin-right: 8px; }

.vol-btn { color: rgba(255,255,255,0.6); font-size: 14px; padding: 4px; background: none; border: none; cursor: pointer; }
.vol-btn:hover { color: #fff; }

.vol-slider-container { display: flex; align-items: center; width: 80px; }
.vol-slider { 
  width: 100%; height: 3px; 
  background: rgba(255,255,255,0.15); 
  border-radius: 2px;
  -webkit-appearance: none;
}
.vol-slider::-webkit-slider-thumb { 
  -webkit-appearance: none; width: 10px; height: 10px; 
  background: #fff; border-radius: 50%; 
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transform: scale(0.8); transition: 0.2s; 
}
.vol-slider:hover::-webkit-slider-thumb { transform: scale(1.2); }

.quality-badge { 
  font-size: 10px; font-weight: 800; 
  color: #FFD700; /* Gold */
  background: rgba(20, 20, 20, 0.8);
  border: 1px solid #FFD700;
  padding: 2px 6px; 
  border-radius: 4px; 
  letter-spacing: 0.5px;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.2);
}
</style>
