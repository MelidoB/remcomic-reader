<template>
    <div
      class="bubble-overlay"
      :class="{ playing: isPlaying }"
      :style="positionStyle"
      @click="onClick"
    ></div>
</template>
  
<script setup>
  import { computed } from 'vue';
  
  const props = defineProps({
    bubble: {
      type: Object,
      required: true
    },
    isPlaying: {
      type: Boolean,
      default: false
    }
  });
  
  const emit = defineEmits(['play']);
  
  const positionStyle = computed(() => ({
    left: `${props.bubble.bbox_percent.left}%`,
    top: `${props.bubble.bbox_percent.top}%`,
    width: `${props.bubble.bbox_percent.width}%`,
    height: `${props.bubble.bbox_percent.height}%`,
  }));
  
  function onClick() {
    emit('play', props.bubble);
  }
</script>
  
<style scoped>
  .bubble-overlay {
    position: absolute;
    cursor: pointer;
    box-sizing: border-box;
    border: 3px solid rgba(79, 70, 229, 0.5);
    background-color: rgba(79, 70, 229, 0.1);
    transition: all 0.2s ease;
    border-radius: 5px;
  }
  
  .bubble-overlay:hover,
  .bubble-overlay.playing {
    border: 4px solid var(--accent-color);
    background-color: rgba(245, 158, 11, 0.3);
    transform: scale(1.03);
    z-index: 10;
  }
</style>