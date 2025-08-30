<template>
  <div>
    <Spinner v-if="isLoading" text="Loading..." />
    
    <div v-if="error" class="error-message">
        <h3>❌ Could not load webtoons</h3>
        <p>{{ error }}</p>
        <p v-if="!assetsUrl">Please ensure `VITE_ASSETS_URL` is set correctly in your <code>.env.local</code> file or in your Vercel/Netlify deployment settings.</p>
    </div>

    <div v-if="!isLoading && !error && webtoons.length === 0" class="error-message">
        <h3>No Webtoons Found</h3>
        <p>Your `webtoons_titles.json` file was loaded successfully but appears to be empty.</p>
        <p>Please run the `remcomic-processor` to generate your comic assets and upload them to your cloud storage.</p>
    </div>

    <!-- Webtoon Selection -->
    <div v-if="!selectedWebtoon && webtoons.length > 0" class="webtoon-list">
      <h1>Select a Webtoon</h1>
      <div class="webtoon-buttons">
        <button
          v-for="webtoon in webtoons"
          :key="webtoon.webtoonTitle"
          @click="selectWebtoon(webtoon)"
          class="webtoon-button"
        >
          {{ webtoon.webtoonTitle ? webtoon.webtoonTitle.replace(/-/g, ' ') : 'Untitled Webtoon' }}
        </button>
      </div>
    </div>

    <!-- Chapter List for Selected Webtoon -->
    <div v-if="selectedWebtoon" class="chapter-list">
      <button @click="selectedWebtoon = null" class="back-button">← Back to Webtoons</button>
      <h1>{{ selectedWebtoon.webtoonTitle ? selectedWebtoon.webtoonTitle.replace(/-/g, ' ') : 'Untitled Webtoon' }}</h1>
      <div class="chapter-links">
        <RouterLink
          v-for="ch in selectedWebtoon.chapters"
          :key="ch.name"
          :to="`/${selectedWebtoon.webtoonTitle}/${ch.name}`"
          class="chapter-link"
        >
          {{ ch.name ? ch.name.replace(/-/g, ' ') : 'Untitled Chapter' }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import Spinner from '@/components/Spinner.vue';

const isLoading = ref(true);
const webtoons = ref([]);
const error = ref(null);
const assetsUrl = import.meta.env.VITE_ASSETS_URL;
const selectedWebtoon = ref(null);

function selectWebtoon(webtoon) {
  selectedWebtoon.value = webtoon;
}

onMounted(async () => {
  if (!assetsUrl) {
    error.value = "Configuration error: The VITE_ASSETS_URL is not defined.";
    isLoading.value = false;
    return;
  }
  try {
    // Fetch webtoon titles from online JSON
    const titlesUrl = `${assetsUrl}/public/webtoons_titles.json`;
    const titlesRes = await fetch(titlesUrl);
    if (!titlesRes.ok) throw new Error(`Failed to fetch webtoon titles (Status: ${titlesRes.status})`);
    const webtoonTitles = await titlesRes.json();

    // For each title, fetch its chapters.json from /public/[webtoon-title]/chapters.json
    const webtoonData = [];
    for (const title of webtoonTitles) {
      try {
        const manifestUrl = `${assetsUrl}/public/${title}/chapters.json`;
        const manifestRes = await fetch(manifestUrl);
        if (!manifestRes.ok) continue;
        const manifest = await manifestRes.json();
        webtoonData.push({
          webtoonTitle: title,
          chapters: manifest.chapters || manifest // support both {chapters:[]} and []
        });
      } catch (e) {
        // skip folders with missing/invalid manifest
      }
    }
    webtoons.value = webtoonData;
  } catch (e) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
});
</script>