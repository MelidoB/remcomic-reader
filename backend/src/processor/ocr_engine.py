from typing import List, Tuple
import cv2
import easyocr
import numpy as np
import torch
from collections import OrderedDict
from src.utils.grammar_corrector import GrammarCorrector
from config.settings import OCR_CACHE_SIZE

class OCREngine:
    def __init__(self) -> None:
        """Initializes the EasyOCR reader."""
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
        self.grammar_corrector: GrammarCorrector = GrammarCorrector()
        self.ocr_cache: OrderedDict = OrderedDict()
        self.ocr_cache.maxsize = OCR_CACHE_SIZE

    def enhance_v1_simple(self, img: np.ndarray) -> np.ndarray:
        """
        METHOD 1: THE SAFE FALLBACK
        Performs minimal processing. Just converts to grayscale. This is the most
        reliable method to not accidentally destroy text.
        """
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    def enhance_v2_redraw(self, img: np.ndarray) -> np.ndarray:
        """
        METHOD 2: THE HIGH-ACCURACY SPECIALIST
        Radically enhances the bubble by isolating and re-drawing text contours.
        Very accurate when it works, but can fail (erase text) on some bubbles.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create a new, clean canvas to draw the filtered text onto.
        clean_canvas = np.full_like(gray, 255) # Start with a white canvas
        
        bubble_area = img.shape[0] * img.shape[1]
        for contour in contours:
            contour_area = cv2.contourArea(contour)
            # Filter out contours that are too small (noise) or too large (art/borders).
            # These thresholds may need tweaking for different comic styles, but are a good start.
            if (bubble_area * 0.0001) < contour_area < (bubble_area * 0.40):
                # Draw the surviving contours in black on our white canvas.
                cv2.drawContours(clean_canvas, [contour], -1, (0), thickness=cv2.FILLED)

        # We return an inverted canvas because the re-drawn text is black, but we need
        # to process it in the same way our simple method would.
        return clean_canvas

    def extract(self, img: np.ndarray) -> Tuple[str, str]:
        """
        Extracts text using a multi-stage failsafe strategy.
        """
        # Caching logic is checked first, as always.
        hist: bytes = cv2.calcHist([img], [0], None, [32], [0, 256]).tobytes()
        key: Tuple[tuple, bytes] = (img.shape, hist)
        if key in self.ocr_cache:
            self.ocr_cache.move_to_end(key)
            return self.ocr_cache[key]
        
        final_text = ""

        # --- Stage 1: Attempt the high-accuracy "redraw" method first ---
        try:
            enhanced_img_v2 = self.enhance_v2_redraw(img)
            results_v2 = self.reader.readtext(enhanced_img_v2, paragraph=True, detail=0)
            text_v2 = " ".join(results_v2).strip()
            if text_v2:
                print("  -> OCR Success with Redraw Method")
                final_text = text_v2
        except Exception as e:
            print(f"  -> Redraw method produced an error: {e}")
            final_text = ""

        # --- Stage 2: If the first method failed, use the safe fallback ---
        if not final_text:
            print("  -> Redraw method failed to find text, trying Simple Fallback...")
            try:
                enhanced_img_v1 = self.enhance_v1_simple(img)
                results_v1 = self.reader.readtext(enhanced_img_v1, paragraph=True, detail=0)
                text_v1 = " ".join(results_v1).strip()
                if text_v1:
                    print("  -> OCR Success with Simple Fallback Method")
                    final_text = text_v1
            except Exception as e:
                print(f"  -> Simple Fallback method also produced an error: {e}")
                final_text = ""
            
        corrected_text: str = self.grammar_corrector.correct(final_text) if final_text else ""
        
        if final_text:
            if len(self.ocr_cache) >= self.ocr_cache.maxsize:
                self.ocr_cache.popitem(last=False)
            self.ocr_cache[key] = (final_text, corrected_text)
            
        return final_text, corrected_text