import numpy as np
from ultralytics import YOLO
import torch
from config.settings import MODEL_PATH
from typing import List, Tuple


class BubbleDetector:
    def __init__(self) -> None:
        self.model: YOLO = YOLO(MODEL_PATH)
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        if self.device == "cuda":
            self.model.fuse()

    def detect(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        # Ensure the image array is C-contiguous to prevent CUDA memory errors.
        image = np.ascontiguousarray(image)
        
        use_half = self.device == "cuda"
        inputs = self.model.predict(source=image, conf=0.6, verbose=False, half=use_half)
        boxes: List[Tuple[int, int, int, int]] = [tuple(map(int, box)) for box in inputs[0].boxes.xyxy]
        return self.sort_reading_order(self.validate_boxes(boxes))

    def validate_boxes(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        return [box for box in boxes if box[0] < box[2] and box[1] < box[3]]

    def sort_reading_order(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        y_tolerance: int = 20
        box_groups: List[List[Tuple[int, int, int, int]]] = []
        current_group: List[Tuple[int, int, int, int]] = []
        for box in sorted(boxes, key=lambda x: x[1]):
            if current_group and abs(box[1] - current_group[-1][1]) > y_tolerance:
                box_groups.append(current_group)
                current_group = []
            current_group.append(box)
        if current_group:
            box_groups.append(current_group)
        
        sorted_boxes: List[Tuple[int, int, int, int]] = []
        for group in box_groups:
            sorted_boxes.extend(sorted(group, key=lambda x: -x[0]))
            
        return sorted_boxes