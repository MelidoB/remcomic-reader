<template>
    <div>
        <!-- Header Controls (No changes here) -->
        <div class="chapter-view-header">
            <RouterLink to="/" class="btn btn-primary">← Back to Chapters</RouterLink>
            <div class="chapter-controls">
                <div class="speed-controller">
                    <span>Speed:</span>
                    <button v-for="speed in availableSpeeds" :key="speed" @click="playbackSpeed = speed"
                        class="btn btn-speed" :class="{ active: playbackSpeed === speed }">
                        {{ speed }}x
                    </button>
                </div>
                <label class="scroll-autoplay-control">
                    <input type="checkbox" v-model="isScrollAutoplayEnabled">
                    Autoplay on Scroll
                </label>
            </div>
        </div>

        <!-- Page Content (Only one line changes here) -->
        <div v-if="error" class="error-message">
             <h3>❌ Could not load chapter data</h3>
            <p>{{ error }}</p>
        </div>
        
        <div v-for="(page, index) in visiblePages" :key="page" class="comic-page-container">
            <div class="page-header">Page {{ index + 1 }}</div>
            <Spinner v-if="!pageDataCache[index]" text="Loading page..." />
            <div v-else class="image-container">
                <img :src="backendUrl + pageDataCache[index].visualization" class="visualization-image" />

                <!-- 
                  THE FIX IS HERE: 
                  The @play event now passes the index directly. 
                -->
                <BubbleOverlay 
                    v-for="bubble in pageDataCache[index].bubbles" 
                    :key="bubble.order" 
                    :bubble="bubble" 
                    :is-playing="activeBubbleId === `${index}-${bubble.order}`"
                    @play="bubbleData => playAudio(bubbleData, index)"
                    :data-bubble-id="`${index}-${bubble.order}`"
                 />

            </div>
        </div>

        <div ref="loadMoreTrigger"></div>
        <Spinner v-if="isLoadingMore" text="Loading more..." />
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import Spinner from '@/components/Spinner.vue';
import BubbleOverlay from '@/components/BubbleOverlay.vue';

// --- Basic Setup ---
const route = useRoute();
const chapterName = route.params.chapterName;
const backendUrl = import.meta.env.VITE_BACKEND_URL;
const loadMoreTrigger = ref(null);

// --- State Management ---
const allPages = ref([]);
const pageDataCache = ref({});
const error = ref(null);
const pagesToRenderCount = ref(2);
const isLoadingMore = ref(false);

const availableSpeeds = [1.0, 1.5, 2.0];
const playbackSpeed = ref(1.0);
const isScrollAutoplayEnabled = ref(false);
const playedByScrollBubbles = ref(new Set());

let currentAudio = null;
const activeBubbleId = ref(null);
let pollingIntervals = {};
let pageLoadObserver = null;
let bubbleObserver = null;

const visiblePages = computed(() => allPages.value.slice(0, pagesToRenderCount.value));

// --- Fetching Logic (No changes here) ---
async function fetchChapterInfo() {
  try {
    const response = await fetch(`${backendUrl}/api/chapters`);
    const allChapters = await response.json();
    const currentChapter = allChapters.find(c => c.name === chapterName);
    if (currentChapter) {
      allPages.value = currentChapter.pages;
      fetchPageData(0);
      fetchPageData(1);
    } else {
      throw new Error("Chapter not found.");
    }
  } catch (e) {
    error.value = e.message;
  }
}
async function fetchPageData(pageIndex) {
    if (!allPages.value[pageIndex] || pageDataCache.value[pageIndex]) return;
    try {
        const response = await fetch(`${backendUrl}/api/page_data/${chapterName}/${pageIndex}`);
        const data = await response.json();
        if (response.status === 202 && data.status === 'processing') {
            pollForPageData(pageIndex, data.cache_key);
        } else if (response.ok && data.status === 'success') {
            pageDataCache.value[pageIndex] = data;
        }
    } catch(e) { console.error(`Error fetching page ${pageIndex}:`, e); }
}
function pollForPageData(pageIndex, cacheKey) {
    if (pollingIntervals[pageIndex]) return;
    pollingIntervals[pageIndex] = setInterval(async () => {
        try {
            const response = await fetch(`${backendUrl}/api/page_status/${cacheKey}`);
            const data = await response.json();
            if (response.ok && data.status === 'success') {
                clearInterval(pollingIntervals[pageIndex]);
                delete pollingIntervals[pageIndex];
                pageDataCache.value[pageIndex] = data;
            }
        } catch(e) {
            console.error(`Polling error for page ${pageIndex}:`, e)
            clearInterval(pollingIntervals[pageIndex]);
        }
    }, 2500);
}


// --- Audio Playback (THE FIX IS HERE) ---
// The function now receives the pageIndex directly.
function playAudio(bubble, pageIndex) {
    // We can now construct the ID reliably without searching.
    const bubbleId = `${pageIndex}-${bubble.order}`;

    if (currentAudio && activeBubbleId.value === bubbleId) {
        currentAudio.pause();
        return;
    }
    if (currentAudio) currentAudio.pause();
    
    // Fallback logic for selecting URL
    let url = bubble.audio_urls[playbackSpeed.value.toString()] || bubble.audio_urls['1.0'];
    if (!url) {
        console.error("No audio URL found for this bubble.", bubble.audio_urls);
        return;
    }

    currentAudio = new Audio(backendUrl + url);
    currentAudio.playbackRate = playbackSpeed.value;
    currentAudio.play();

    activeBubbleId.value = bubbleId;

    // Event listeners
    currentAudio.onended = () => { activeBubbleId.value = null; currentAudio = null; };
    currentAudio.onpause = () => { if (currentAudio && !currentAudio.ended) { activeBubbleId.value = null; currentAudio = null; } };
}


// --- Observers (No changes here, but logic is now more robust) ---
function setupObservers() {
    pageLoadObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && pagesToRenderCount.value < allPages.value.length) {
            isLoadingMore.value = true;
            pagesToRenderCount.value += 1;
            fetchPageData(pagesToRenderCount.value - 1);
            setTimeout(() => { isLoadingMore.value = false; }, 1000);
        }
    }, { threshold: 1.0 });
    
    if (loadMoreTrigger.value) pageLoadObserver.observe(loadMoreTrigger.value);

    bubbleObserver = new IntersectionObserver((entries) => {
        if (!isScrollAutoplayEnabled.value) return;
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const bubbleId = entry.target.dataset.bubbleId;
                if (!playedByScrollBubbles.value.has(bubbleId)) {
                    playedByScrollBubbles.value.add(bubbleId);
                    const [pageIndex, bubbleOrder] = bubbleId.split('-').map(Number);
                    const bubbleData = pageDataCache.value[pageIndex]?.bubbles.find(b => b.order == bubbleOrder);
                    // Pass the index directly here as well
                    if(bubbleData) playAudio(bubbleData, pageIndex);
                }
            }
        });
    }, { rootMargin: '-30% 0px -30% 0px', threshold: 0.5 });
}

watch(pageDataCache, () => {
    setTimeout(() => {
        document.querySelectorAll('.bubble-overlay').forEach(el => bubbleObserver.observe(el));
    }, 100);
}, { deep: true });


// --- Lifecycle Hooks (No changes here) ---
onMounted(() => {
    fetchChapterInfo();
    setupObservers();
});
onUnmounted(() => {
    if (currentAudio) currentAudio.pause();
    Object.values(pollingIntervals).forEach(clearInterval);
    if(pageLoadObserver) pageLoadObserver.disconnect();
    if(bubbleObserver) bubbleObserver.disconnect();
});
</script>