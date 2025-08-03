<template>
  <div>
    <Spinner v-if="isLoading" text="Loading Chapters..." />
    <div v-if="error" class="error-message">
        <h3>❌ Could not load chapters</h3>
        <p>Please ensure the backend server is running and accessible at the configured URL.</p>
        <p><code>{{ backendUrl }}</code></p>
    </div>
    <div v-if="chapters.length > 0" class="chapter-list">
      <RouterLink
        v-for="chapter in chapters"
        :key="chapter.name"
        :to="`/chapter/${chapter.name}`"
        class="chapter-link"
      >
        {{ chapter.name.replace(/-/g, ' ') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import Spinner from '@/components/Spinner.vue';

const isLoading = ref(true);
const chapters = ref([]);
const error = ref(null);
const backendUrl = import.meta.env.VITE_BACKEND_URL;

onMounted(async () => {
  try {
    const response = await fetch(`${backendUrl}/api/chapters`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    const fetchedChapters = await response.json();

    // --- THIS IS THE FIX ---
    // We sort the array using localeCompare with the numeric option, which handles "1", "2", "10" correctly.
    fetchedChapters.sort((a, b) => 
        a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
    );

    chapters.value = fetchedChapters;

  } catch (e) {
    console.error("Failed to fetch chapters:", e);
    error.value = e;
  } finally {
    isLoading.value = false;
  }
});
</script>