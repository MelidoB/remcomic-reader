<template>
    <div>
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
                    <span class="shortcut-hint">(Press 'A' to toggle)</span>
                </label>
            </div>
        </div>

        <div v-if="error" class="error-message">
             <h3>❌ Could not load chapter data</h3>
            <p>{{ error }}</p>
        </div>
        
        <div v-for="(page, index) in visiblePages" :key="index" class="comic-page-container">
            <div class="page-header">Page {{ index + 1 }}</div>
            <Spinner v-if="!pageDataCache[index]" text="Loading page..." />
            <div v-else class="image-container">
                <img :src="pageDataCache[index].visualization" class="visualization-image" :alt="`Page ${index + 1}`" />
                
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
        <Spinner v-if="isLoadingMore" text="Loading more pages..." />
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { RouterLink } from 'vue-router';
import Spinner from '@/components/Spinner.vue';
import BubbleOverlay from '@/components/BubbleOverlay.vue';

const props = defineProps({
    webtoonTitle: { type: String, required: true },
    chapterName: { type: String, required: true },
});
const assetsUrl = import.meta.env.VITE_ASSETS_URL;
const loadMoreTrigger = ref(null);

const allPages = ref([]);
const pageDataCache = ref({});
const error = ref(null);
const pagesToRenderCount = ref(2);
const isLoadingMore = ref(false);
const visiblePages = computed(() => allPages.value.slice(0, pagesToRenderCount.value));

const availableSpeeds = [1.0, 1.5, 2.0];
const playbackSpeed = ref(1.0);
const isScrollAutoplayEnabled = ref(false);
const playedByScrollBubbles = ref(new Set());
let currentAudio = null;
const activeBubbleId = ref(null);

let pageLoadObserver = null;
let bubbleObserver = null;
let cleanupKeyboardListener = null;

async function fetchChapterInfo() {
  if (!assetsUrl) {
      error.value = "FATAL: VITE_ASSETS_URL environment variable is not set.";
      return;
  }
  try {
    const manifestUrl = `${assetsUrl}/public/${props.webtoonTitle}/chapters.json`;
    const response = await fetch(manifestUrl);
    if (!response.ok) throw new Error(`Could not fetch chapter list. Status: ${response.status}`);
    const allChapters = await response.json();
    const currentChapter = allChapters.find(c => c.name === props.chapterName);

    if (currentChapter && currentChapter.pages) {
        // Fix: extract the correct property from each page object
        // Try data_key, fallback to name, or use the whole object if it's a string
        allPages.value = currentChapter.pages.map(page =>
            typeof page === 'string' ? page : (page.data_key || page.name || page)
        );
        fetchPageData(0);
        fetchPageData(1);
    } else {
        throw new Error(`Chapter "${props.chapterName}" not found in manifest.`);
    }
  } catch (e) { error.value = e.message; }
}

async function fetchPageData(pageIndex) {
    if (pageIndex >= allPages.value.length || pageDataCache.value[pageIndex]) return;
    try {
        const pageStem = allPages.value[pageIndex];
        const baseChapterPath = `${assetsUrl}/public/${props.webtoonTitle}/${props.chapterName}`;
        // Extract page number from pageStem (e.g., "chapter-1\01.jpg" -> "01")
        const pageFile = pageStem.split('\\').pop(); // "01.jpg"
        const pageNum = pageFile.replace('.jpg', ''); // "01"
        const pageDataUrl = `${baseChapterPath}/${pageNum}.json`;
        console.log('[fetchPageData] pageIndex:', pageIndex, 'pageStem:', pageStem, 'pageFile:', pageFile, 'pageNum:', pageNum, 'baseChapterPath:', baseChapterPath, 'pageDataUrl:', pageDataUrl);
        
        const response = await fetch(pageDataUrl);
        const data = await response.json();
        
        // Debug: log bubble data structure
        console.log('[fetchPageData] pageIndex:', pageIndex, 'data.bubbles:', data.bubbles);
        
        // Build visualization URL: use extracted page number
        data.visualization = `${baseChapterPath}/${pageNum}.jpg`;
        // Debug
        console.debug('[ChapterView] pageDataUrl=', pageDataUrl, 'pageNum=', pageNum, 'final=', data.visualization);
        
        // Build audio URLs
        for (const bubble of data.bubbles) {
            console.log('[fetchPageData] bubble:', bubble.order, 'existing audio_urls keys:', Object.keys(bubble.audio_urls || {}), 'values:', bubble.audio_urls);
            if (bubble.audio_paths) {
                bubble.audio_urls = {};
                for (const speed in bubble.audio_paths) {
                    const relativePath = bubble.audio_paths[speed];
                    bubble.audio_urls[speed] = relativePath.includes('/') ? `${assetsUrl}/public/${props.webtoonTitle}/${relativePath}` : `${baseChapterPath}/${relativePath}`;
                }
            } else if (bubble.audio_urls && Object.keys(bubble.audio_urls).length > 0) {
                // If audio_urls already exists, ensure URLs are absolute and correct the path
                for (const speed in bubble.audio_urls) {
                    let url = bubble.audio_urls[speed];
                    if (!url.startsWith('http')) {
                        // Fix the path: remove 'chapters_result/', adjust filename, and remove leading slashes
                        url = url.replace('chapters_result/', '').replace(/chapter-\d+_(\d+_bubble_\d+_speed_[\d_]+\.mp3)/, '$1').replace(/^\/+/, '');
                        bubble.audio_urls[speed] = url.includes('/') ? `${assetsUrl}/public/${props.webtoonTitle}/${url}` : `${baseChapterPath}/${url}`;
                    }
                }
            } else {
                console.warn('[fetchPageData] No audio data found for bubble', bubble.order);
            }
            console.log('[fetchPageData] final audio_urls:', bubble.audio_urls);
        }
        pageDataCache.value[pageIndex] = data;

    } catch (e) { console.error(`Error fetching page ${pageIndex}:`, e); }
}

function playAudio(bubble, pageIndex) {
    const bubbleId = `${pageIndex}-${bubble.order}`;
    if (currentAudio) currentAudio.pause();
    if (activeBubbleId.value === bubbleId) {
        activeBubbleId.value = null; return;
    }
    
    const url = bubble.audio_urls[playbackSpeed.value.toString()] || bubble.audio_urls['1.0'];
    console.log('[playAudio] bubbleId:', bubbleId, 'playbackSpeed:', playbackSpeed.value, 'url:', url, 'audio_urls:', bubble.audio_urls);
    if (!url) {
        console.error('[playAudio] No audio URL found for bubble', bubbleId);
        return;
    }
    
    currentAudio = new Audio(url);
    currentAudio.play();
    activeBubbleId.value = bubbleId;
    currentAudio.onended = () => { activeBubbleId.value = null; };
}

function setupObservers() {
    // Add keyboard shortcut for autoplay toggle
    const handleKeyPress = (event) => {
        // Toggle autoplay on scroll with 'A' key (case insensitive)
        if (event.key.toLowerCase() === 'a' && !event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            isScrollAutoplayEnabled.value = !isScrollAutoplayEnabled.value;
            console.log('[Keyboard] Autoplay on scroll toggled:', isScrollAutoplayEnabled.value);
        }
    };
    
    document.addEventListener('keydown', handleKeyPress);
    
    // Store cleanup function
    const cleanup = () => {
        document.removeEventListener('keydown', handleKeyPress);
    };
    
    pageLoadObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && pagesToRenderCount.value < allPages.value.length) {
            isLoadingMore.value = true;
            pagesToRenderCount.value++;
            fetchPageData(pagesToRenderCount.value - 1).finally(() => {
                isLoadingMore.value = false;
            });
        }
    }, { rootMargin: "200px" });
    
    if (loadMoreTrigger.value) pageLoadObserver.observe(loadMoreTrigger.value);

    bubbleObserver = new IntersectionObserver((entries) => {
        if (!isScrollAutoplayEnabled.value) return;
        for (const entry of entries) {
            if (entry.isIntersecting) {
                const bubbleId = entry.target.dataset.bubbleId;
                if (!playedByScrollBubbles.value.has(bubbleId)) {
                    playedByScrollBubbles.value.add(bubbleId);
                    const [pageIndex, bubbleOrder] = bubbleId.split('-').map(Number);
                    const bubbleData = pageDataCache.value[pageIndex]?.bubbles.find(b => b.order == bubbleOrder);
                    if (bubbleData) playAudio(bubbleData, pageIndex);
                }
            }
        }
    }, { rootMargin: '-40% 0px -40% 0px', threshold: 0.5 });
    
    // Return cleanup function to be called on unmount
    return cleanup;
}

watch(pageDataCache, () => {
    setTimeout(() => {
        document.querySelectorAll('[data-bubble-id]').forEach(el => bubbleObserver.observe(el));
    }, 100);
}, { deep: true });

onMounted(() => {
    fetchChapterInfo();
    cleanupKeyboardListener = setupObservers();
});

onUnmounted(() => {
    if (currentAudio) currentAudio.pause();
    if (pageLoadObserver) pageLoadObserver.disconnect();
    if (bubbleObserver) bubbleObserver.disconnect();
    if (cleanupKeyboardListener) cleanupKeyboardListener();
});
</script>