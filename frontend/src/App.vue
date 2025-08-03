<template>
  <div class="container">
    <header>
      <h1>🗨️ Comic Reader</h1>
      <p>{{ subtitle }}</p>
    </header>
    <main>
      <!-- Vue Router will render the current page's component here -->
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const subtitle = computed(() => {
  if (route.name === 'chapter-view') {
    return `Reading: ${route.params.chapterName.replace(/-/g, ' ')}`;
  }
  return 'Select a chapter to start reading';
});
</script>