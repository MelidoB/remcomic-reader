from pathlib import Path
import os
import psutil

# --- Basic Project Paths ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CHAPTERS_DIR: str = str(PROJECT_ROOT / "chapters")
CACHE_DIR: str = str(PROJECT_ROOT / "cache")  # NEW: Persistent file cache
MODEL_PATH: str = str(PROJECT_ROOT / "src/models/bubble-detector/comic-speech-bubble-detector.pt")
PIPER_MODEL_PATH: str = str(PROJECT_ROOT / "src/models/v1_0/en_US-lessac-medium.onnx")
UPLOAD_FOLDER: str = str(PROJECT_ROOT / "src/uploads")
OUTPUT_DIR: str = str(PROJECT_ROOT / "src/web/static/results")

# --- Image and Processing Constants ---
MAX_WIDTH: int = 1200
BATCH_SIZE: int = 8 
ALLOWED_EXTENSIONS: set[str] = {'png', 'jpg', 'jpeg', 'webp'}
OCR_CACHE_SIZE: int = 200

# --- Dynamic Resource Allocation ---
def get_optimal_resources() -> dict:
    """Calculates optimal worker and cache sizes based on system resources."""
    cpu_count = os.cpu_count() or 1
    # Use half the system's cores, with a min of 1 and a max of 8
    workers = max(1, min(8, cpu_count // 2))
    
    # Estimate "hot" cache size based on available memory
    # Assume each cached item takes ~10MB in memory (a safe overestimate)
    try:
        available_mem_gb = psutil.virtual_memory().available / (1024**3)
        # Target up to 25% of available RAM for the hot cache, capping at 4GB
        target_mem_mb = min(4096, int(available_mem_gb * 0.25 * 1024))
        hot_cache_size = max(50, target_mem_mb // 10)
    except Exception:
        # Fallback if psutil fails for any reason
        hot_cache_size = 100

    return {'workers': workers, 'hot_cache_size': hot_cache_size}

RESOURCES = get_optimal_resources()

# --- Background Processing Settings ---
BACKGROUND_PROCESSING = {
    'enabled': True,
    'max_workers': RESOURCES['workers'],         # MODIFIED: Dynamic workers
    'max_cache_size': RESOURCES['hot_cache_size'], # MODIFIED: Dynamic in-memory cache size
    'preload_ahead': 5,
    'preload_chapters': 1,
    'priority_levels': {
        'immediate': 5,
        'next_page': 4,
        'current_chapter': 3,
        'next_chapter': 2,
        'background': 1 # For the initial startup scan
    },
    'processing_timeout': 30,
    'queue_check_interval': 1,
}

# --- Performance Settings ---
PERFORMANCE = {
    'enable_image_caching': True,
    'enable_result_caching': True,
    'max_session_cache': 50,
    'compress_images': True,
    'image_quality': 85,
    'lazy_load_audio': True,
}

# --- Logging Settings ---
LOGGING = {
    'level': 'INFO',
    'log_processing_times': True,
    'log_cache_hits': True,
    'log_background_tasks': True,
}