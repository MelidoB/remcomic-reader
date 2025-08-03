from typing import List, Tuple, Dict, Any, Iterator
import cv2
import numpy as np
import os
import json
from pathlib import Path
from PIL import Image
from src.processor.bubble_detector import BubbleDetector
from src.processor.ocr_engine import OCREngine
from src.processor.tts_generator import TTSGenerator
from config.settings import OUTPUT_DIR, MAX_WIDTH, BATCH_SIZE, CACHE_DIR
from concurrent.futures import ThreadPoolExecutor

class ImageProcessor:
    def __init__(self) -> None:
        self.detector: BubbleDetector = BubbleDetector()
        self.ocr: OCREngine = OCREngine()
        self.tts: TTSGenerator = TTSGenerator()
        self.output_dir: str = OUTPUT_DIR
        self.max_width: int = MAX_WIDTH
        self.batch_size: int = BATCH_SIZE
        # Ensure a reasonable number of threads for TTS, which is I/O bound
        self.tts_executor = ThreadPoolExecutor(max_workers=(os.cpu_count() or 1) * 2)

    def preprocess_image(self, image_path: str) -> Tuple[np.ndarray, float]:
        # ... (this method is unchanged)
        img: np.ndarray = np.array(Image.open(image_path).convert('RGB'))
        h, w = img.shape[:2]
        if w > self.max_width:
            scale: float = self.max_width / w
            img = cv2.resize(img, (self.max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
            return img, scale
        return img, 1.0

    def get_cache_filepath(self, image_path: str) -> Path:
        """Helper to construct the persistent cache path, matching server.py."""
        image_path_obj = Path(image_path)
        cache_filename = f"{image_path_obj.stem}.json"
        # Correctly navigate from OUTPUT_DIR to project root then to CACHE_DIR
        cache_path = Path(CACHE_DIR) / image_path_obj.parent.name / cache_filename
        return cache_path
        
    def process(self, image_path: str) -> Iterator[Dict[str, Any]]:
        img, scale = self.preprocess_image(image_path)
        boxes: List[Tuple[int, int, int, int]] = self.detector.detect(img)
        img_h, img_w = img.shape[:2]
        image_path_obj = Path(image_path)
        unique_prefix = f"{image_path_obj.parent.name}_{image_path_obj.stem}"
        
        output_data = []
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            bubble_img: np.ndarray = img[y1:y2, x1:x2]
            if bubble_img.size == 0: continue
            raw_text, corrected_text = self.ocr.extract(bubble_img)
            
            # Prepare bubble data, setting audio_urls to a default empty dict
            output_data.append({
                "order": i + 1,
                "bbox_percent": {"left": (x1/img_w)*100, "top": (y1/img_h)*100, "width": ((x2-x1)/img_w)*100, "height": ((y2-y1)/img_h)*100},
                "raw_text": raw_text,
                "corrected_text": corrected_text,
                "audio_urls": {} # <-- CHANGED: from audio_url: ""
            })

        # This inner function is now updated
        def generate_audio_for_bubble(bubble_data):
            text = bubble_data['corrected_text']
            if text:
                # The tts.generate function now returns a dictionary or None
                urls_dict = self.tts.generate(text, bubble_data['order'], unique_prefix)
                if urls_dict:
                    bubble_data['audio_urls'] = urls_dict
            return bubble_data

        futures = [self.tts_executor.submit(generate_audio_for_bubble, data) for data in output_data]
        processed_bubbles = [future.result() for future in futures]
        
        viz_filename = f"viz_{unique_prefix}{image_path_obj.suffix}"
        final_viz_path: str = os.path.join(self.output_dir, viz_filename)
        final_viz_url: str = f"/static/results/{viz_filename}"
        cv2.imwrite(final_viz_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        
        final_result = {
            "status": "success",
            "bubbles": processed_bubbles,
            "visualization": final_viz_url
        }

        # NEW: Save the result to the persistent cache
        try:
            cache_filepath = self.get_cache_filepath(image_path)
            os.makedirs(cache_filepath.parent, exist_ok=True)
            with open(cache_filepath, 'w') as f:
                json.dump(final_result, f, indent=2)
            print(f" -> Saved to persistent cache: {cache_filepath.name}")
        except Exception as e:
            print(f"ERROR: Could not save result to persistent cache for {image_path}: {e}")

        yield final_result