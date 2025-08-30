<template>
  <div class="spinner-container">
    <div class="spinner"></div>
    <p v-if="text">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  text: String,
});
</script>

<style scoped>
.spinner-container {
  color: #6b7280;
}
.spinner {
    width: 50px; height: 50px;
    border: 5px solid #e5e7eb;
    border-top: 5px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}
@keyframes spin { 
  0% { transform: rotate(0deg); } 
  100% { transform: rotate(360deg); } 
}
</style>