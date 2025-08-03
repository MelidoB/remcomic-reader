import re
import os
import json
import hashlib
import atexit
import threading
import queue
import time
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import OrderedDict
from os.path import basename, dirname
from config.settings import CHAPTERS_DIR, PROJECT_ROOT, CACHE_DIR, BACKGROUND_PROCESSING
from src.processor.image_processor import ImageProcessor

processor = ImageProcessor()
app = Flask(__name__)

# --- CORS and Header Configuration ---
origins = "*"
CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

@app.after_request
def add_ngrok_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

app.secret_key = 'super-secret-key'
app.jinja_env.filters['basename'] = basename

# --- Global Caches and Helpers ---
CHAPTER_CACHE: List[Dict[str, Any]] = []
CACHE_KEY_TO_PATH_MAP: Dict[str, str] = {}

def get_cache_filepath(image_path: str) -> Path:
    """Helper function to get the standardized persistent cache file path for a given page image."""
    image_path_obj = Path(image_path)
    cache_filename = f"{image_path_obj.stem}.json"
    cache_path = Path(CACHE_DIR) / image_path_obj.parent.name / cache_filename
    return cache_path

# --- Background Processor Class ---
class BackgroundProcessor:
    def __init__(self, max_workers=4):
        self.processing_queue = queue.PriorityQueue()
        self.processing_cache = OrderedDict()
        self.processing_status = {}
        self.max_cache_size = BACKGROUND_PROCESSING.get('max_cache_size', 50)
        self.max_workers = max_workers
        self.workers = []
        self.running = True
        self.lock = threading.Lock()
        self.start_workers()
    
    def start_workers(self):
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker(self):
        while self.running:
            try:
                priority, task_data = self.processing_queue.get(timeout=1)
                if task_data is None: break
                image_path, cache_key = task_data
                with self.lock:
                    if cache_key in self.processing_cache:
                        self.processing_queue.task_done()
                        continue
                    self.processing_status[cache_key] = 'processing'
                try:
                    # The image processor now saves the result to the file cache internally
                    result = next(res for res in processor.process(image_path) if res['status'] == 'success')
                    with self.lock:
                        if len(self.processing_cache) >= self.max_cache_size:
                            oldest_key, _ = self.processing_cache.popitem(last=False)
                            if oldest_key in self.processing_status: del self.processing_status[oldest_key]
                            if oldest_key in CACHE_KEY_TO_PATH_MAP: del CACHE_KEY_TO_PATH_MAP[oldest_key]
                        self.processing_cache[cache_key] = result
                        self.processing_status[cache_key] = 'completed'
                except Exception as e:
                    print(f"Error processing {image_path}: {str(e)}")
                    with self.lock: self.processing_status[cache_key] = 'error'
                self.processing_queue.task_done()
            except queue.Empty: continue
            except Exception as e: print(f"Worker error: {str(e)}")

    def get_cache_key(self, image_path: str) -> str:
        cache_key = hashlib.md5(image_path.encode()).hexdigest()
        if cache_key not in CACHE_KEY_TO_PATH_MAP:
             CACHE_KEY_TO_PATH_MAP[cache_key] = image_path
        return cache_key
    
    def add_to_queue(self, image_path: str, priority: int = 3):
        cache_key = self.get_cache_key(image_path)
        with self.lock:
            if cache_key in self.processing_cache or self.processing_status.get(cache_key) in ['processing', 'queued']:
                if cache_key in self.processing_cache: self.processing_cache.move_to_end(cache_key)
                return cache_key
            self.processing_status[cache_key] = 'queued'
        self.processing_queue.put((priority, (image_path, cache_key)))
        return cache_key
    
    def get_result(self, image_path: str) -> Optional[Dict]:
        cache_key = self.get_cache_key(image_path)
        with self.lock:
            result = self.processing_cache.get(cache_key)
            if result: self.processing_cache.move_to_end(cache_key)
            return result

    def shutdown(self):
        self.running = False
        for _ in self.workers: self.processing_queue.put((99, None))

bg_processor = BackgroundProcessor(max_workers=BACKGROUND_PROCESSING['max_workers'])
atexit.register(bg_processor.shutdown)

# --- Chapter Loading ---
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}

def natural_sort_key(path_obj: Path) -> int:
    try: return int(path_obj.stem)
    except (ValueError, TypeError): return float('inf') 

def _load_chapter_data() -> List[Dict[str, Any]]:
    # ... (this function's content remains unchanged)
    chapters = []
    chapters_path = Path(CHAPTERS_DIR)
    if not chapters_path.exists(): return []
    chapter_dirs = sorted([p for p in chapters_path.iterdir() if p.is_dir()], key=lambda p: p.name)
    for chapter_dir in chapter_dirs:
        image_files = [f for f in chapter_dir.iterdir() if f.is_file() and allowed_file(f.name)]
        sorted_files = sorted(image_files, key=natural_sort_key)
        images = [str(f) for f in sorted_files]
        if images:
            image_urls = [os.path.join(chapter_dir.name, os.path.basename(f)) for f in images]
            chapters.append({"chapter": chapter_dir.name, "images": images, "image_urls": image_urls})
    return chapters

def get_chapters() -> List[Dict[str, Any]]:
    return CHAPTER_CACHE

# --- API Endpoints ---
@app.route('/api/chapters', methods=['GET'])
def get_all_chapters():
    # ... (this function's content remains unchanged)
    chapters_data = get_chapters()
    frontend_chapters = [{"name": c["chapter"], "pages": c["image_urls"]} for c in chapters_data]
    return jsonify(frontend_chapters)

@app.route('/api/page_data/<chapter_name>/<int:page_index>')
def get_page_data(chapter_name: str, page_index: int):
    # --- MODIFIED to check persistent cache first ---
    all_chapters = get_chapters()
    chapter = next((c for c in all_chapters if c['chapter'] == chapter_name), None)
    if not chapter or page_index >= len(chapter['images']):
        return jsonify({"error": "Page not found."}), 404

    current_image_path = chapter['images'][page_index]
    cache_filepath = get_cache_filepath(current_image_path)
    
    # 1. THE FAST PATH: Check for the persistent file cache
    if cache_filepath.exists():
        print(f"PERSISTENT CACHE HIT for {os.path.basename(current_image_path)}")
        try:
            with open(cache_filepath, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            print(f"Error reading from persistent cache: {e}. Reprocessing.")
            cache_filepath.unlink() # Delete corrupt cache file

    # 2. Check for "hot" in-memory cache (already processed in this session)
    cached_result = bg_processor.get_result(current_image_path)
    if cached_result:
        print(f"HOT CACHE HIT for {os.path.basename(current_image_path)}")
        return jsonify(cached_result)

    # 3. If not cached anywhere, queue it for processing and tell the frontend
    print(f"CACHE MISS for {os.path.basename(current_image_path)}. Queueing for processing.")
    bg_processor.add_to_queue(current_image_path, priority=BACKGROUND_PROCESSING['priority_levels']['immediate'])
    
    # Preload pages ahead in the CURRENT chapter
    for i in range(1, BACKGROUND_PROCESSING.get('preload_ahead', 3) + 1):
        if (page_index + i) < len(chapter['images']):
            bg_processor.add_to_queue(chapter['images'][page_index + i], priority=BACKGROUND_PROCESSING['priority_levels']['next_page'])
    
    cache_key = bg_processor.get_cache_key(current_image_path)
    return jsonify({"status": "processing", "cache_key": cache_key}), 202

@app.route('/api/page_status/<cache_key>')
def get_page_status(cache_key: str):
    # ... (this function's content remains unchanged)
    image_path_to_check = CACHE_KEY_TO_PATH_MAP.get(cache_key)
    if not image_path_to_check:
        return jsonify({"status": "processing"}), 202
    page_result = bg_processor.get_result(image_path_to_check)
    if page_result:
        return jsonify(page_result)
    else:
        return jsonify({"status": "processing"}), 202

# --- Static File Serving ---
@app.route('/chapters/<path:filename>')
def serve_chapter_image(filename):
    return send_from_directory(CHAPTERS_DIR, filename)

@app.route('/static/results/<path:filename>')
def serve_result_file(filename):
    results_dir = Path(PROJECT_ROOT) / "src" / "web" / "static" / "results"
    return send_from_directory(results_dir, filename)

# --- Startup ---
def initial_content_processing():
    """NEW: Scans all chapters and queues any new or modified pages for background processing."""
    print("🚀 Kicking off initial content scan...")
    all_chapters = _load_chapter_data()
    for chapter in all_chapters:
        for image_path_str in chapter['images']:
            image_path = Path(image_path_str)
            cache_filepath = get_cache_filepath(image_path_str)
            
            # If cache file doesn't exist OR the image file is newer, queue it
            if not cache_filepath.exists() or image_path.stat().st_mtime > cache_filepath.stat().st_mtime:
                print(f"  -> Queuing for processing: {image_path.name}")
                bg_processor.add_to_queue(image_path_str, priority=BACKGROUND_PROCESSING['priority_levels']['background'])
    print("✅ Initial content scan complete. Processing will continue in the background.")

if __name__ == '__main__':
    with app.app_context():
        os.makedirs(CACHE_DIR, exist_ok=True)
        for chapter_dir in Path(CHAPTERS_DIR).iterdir():
            if chapter_dir.is_dir():
                os.makedirs(Path(CACHE_DIR) / chapter_dir.name, exist_ok=True)

        CHAPTER_CACHE = _load_chapter_data()
        if not CHAPTER_CACHE:
            print("⚠️ WARNING: No chapters found in 'backend/chapters/'")
        else:
            print(f"✅ Loaded {len(CHAPTER_CACHE)} chapters.")
            # Run pre-processing in a separate thread to not block server startup
            preprocessing_thread = threading.Thread(target=initial_content_processing, daemon=True)
            preprocessing_thread.start()
    
    print(f"🗨️  Comic Reader API starting with {BACKGROUND_PROCESSING['max_workers']} workers.")
    print(f"🌐 Backend accessible at: http://0.0.0.0:5000")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    finally:
        bg_processor.shutdown()