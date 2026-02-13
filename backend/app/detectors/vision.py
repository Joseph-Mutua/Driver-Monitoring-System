from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    import mediapipe as mp
except Exception:
    mp = None

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class DriverFaceMonitor:
    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]
    MOUTH = [13, 14, 78, 308]

    def __init__(self, fps: float):
        self.fps = max(fps, 1.0)
        self.closed_frames = 0
        self.yawn_frames = 0
        self.look_away_frames = 0
        self.limitations: list[str] = []
        if mp:
            self.mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4,
            )
        else:
            self.mesh = None
            self.limitations.append("MediaPipe unavailable: fatigue and distraction reliability reduced.")

    def _ear(self, lm, idx, w, h) -> float:
        p = [(lm[i].x * w, lm[i].y * h) for i in idx]
        a = math.dist(p[1], p[5])
        b = math.dist(p[2], p[4])
        c = math.dist(p[0], p[3]) + 1e-6
        return (a + b) / (2.0 * c)

    def _mar(self, lm, w, h) -> float:
        up = (lm[self.MOUTH[0]].x * w, lm[self.MOUTH[0]].y * h)
        low = (lm[self.MOUTH[1]].x * w, lm[self.MOUTH[1]].y * h)
        left = (lm[self.MOUTH[2]].x * w, lm[self.MOUTH[2]].y * h)
        right = (lm[self.MOUTH[3]].x * w, lm[self.MOUTH[3]].y * h)
        return math.dist(up, low) / (math.dist(left, right) + 1e-6)

    def detect_metrics(self, frame: np.ndarray) -> dict:
        if not self.mesh:
            return {
                "fatigue": False,
                "fatigue_conf": 0.0,
                "distracted": False,
                "distracted_conf": 0.0,
                "ear": 0.0,
                "mar": 0.0,
                "yaw_ratio": 0.0,
                "eyes_closed": False,
            }

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out = self.mesh.process(rgb)
        if not out.multi_face_landmarks:
            return {
                "fatigue": False,
                "fatigue_conf": 0.0,
                "distracted": False,
                "distracted_conf": 0.0,
                "ear": 0.0,
                "mar": 0.0,
                "yaw_ratio": 0.0,
                "eyes_closed": False,
            }

        lm = out.multi_face_landmarks[0].landmark
        ear = (self._ear(lm, self.LEFT_EYE, w, h) + self._ear(lm, self.RIGHT_EYE, w, h)) / 2.0
        mar = self._mar(lm, w, h)

        nose_x = lm[1].x * w
        left_eye = lm[33].x * w
        right_eye = lm[263].x * w
        eye_mid = (left_eye + right_eye) / 2.0
        yaw_ratio = abs(nose_x - eye_mid) / max(abs(right_eye - left_eye), 1.0)

        eyes_closed = ear < 0.20

        if eyes_closed:
            self.closed_frames += 1
        else:
            self.closed_frames = 0

        if mar > 0.65:
            self.yawn_frames += 1
        else:
            self.yawn_frames = 0

        if yaw_ratio > 0.30:
            self.look_away_frames += 1
        else:
            self.look_away_frames = 0

        fatigue = self.closed_frames > 2.0 * self.fps or self.yawn_frames > 1.5 * self.fps
        fatigue_conf = min(1.0, max((0.24 - ear) * 6.0, (mar - 0.55) * 2.0)) if fatigue else 0.0

        distracted = self.look_away_frames > 1.2 * self.fps
        distracted_conf = min(1.0, (yaw_ratio - 0.20) * 3.0) if distracted else 0.0
        return {
            "fatigue": fatigue,
            "fatigue_conf": max(fatigue_conf, 0.0),
            "distracted": distracted,
            "distracted_conf": max(distracted_conf, 0.0),
            "ear": ear,
            "mar": mar,
            "yaw_ratio": yaw_ratio,
            "eyes_closed": eyes_closed,
        }


class LaneDeviationDetector:
    def __init__(self, fps: float):
        self.fps = max(fps, 1.0)
        self.offset_frames = 0
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def detect(self, frame: np.ndarray) -> tuple[bool, float, float]:
        h, w = frame.shape[:2]
        roi = frame[int(h * 0.55):, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = self.clahe.apply(gray)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=40, maxLineGap=30)

        if lines is None:
            self.offset_frames = max(0, self.offset_frames - 1)
            return False, 0.0, 0.0

        left_x, right_x = [], []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            if slope < -0.35:
                left_x.extend([x1, x2])
            elif slope > 0.35:
                right_x.extend([x1, x2])

        if not left_x or not right_x:
            self.offset_frames = max(0, self.offset_frames - 1)
            return False, 0.0, 0.0

        lane_center = (np.mean(left_x) + np.mean(right_x)) / 2.0
        car_center = w / 2.0
        offset_ratio = abs(car_center - lane_center) / w

        if offset_ratio > 0.12:
            self.offset_frames += 1
        else:
            self.offset_frames = max(0, self.offset_frames - 1)

        detected = self.offset_frames > 1.0 * self.fps
        conf = min(1.0, (offset_ratio - 0.07) * 6.0) if detected else 0.0
        return detected, max(conf, 0.0), float(offset_ratio)


class ObjectDetector:
    VEHICLE_CLASSES = {2, 3, 5, 7}
    PHONE_CLASS = 67

    def __init__(self, model_path: str = "yolov8n.pt"):
        self.limitations: list[str] = []
        self.model = None
        if YOLO:
            try:
                self.model = YOLO(model_path)
            except Exception:
                self.limitations.append(f"YOLO model failed to load ({model_path}): phone/obstruction/tailgating reduced.")
        else:
            self.limitations.append("Ultralytics unavailable: phone/obstruction/tailgating disabled.")

    def detect(self, frame: np.ndarray, conf: float = 0.35) -> list[dict]:
        if not self.model:
            return []
        res = self.model.predict(frame, verbose=False, imgsz=640, conf=conf)
        out = []
        for r in res:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls = int(box.cls.item())
                conf = float(box.conf.item())
                x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                out.append({"class": cls, "conf": conf, "bbox": (x1, y1, x2, y2)})
        return out


class SeatbeltDetector:
    def __init__(self, model_path: str | None = None):
        self.limitations: list[str] = [
            "Seatbelt detection is heuristic; use a seatbelt-specific model for production certification."
        ]
        self.model = None
        if model_path and YOLO and Path(model_path).exists():
            try:
                self.model = YOLO(model_path)
                self.limitations = []
            except Exception:
                self.model = None

    def detect(self, frame: np.ndarray) -> tuple[bool, float]:
        if self.model is not None:
            # Expected custom model classes: seatbelt_on / seatbelt_off (or similar)
            try:
                res = self.model.predict(frame, verbose=False, imgsz=640, conf=0.35)
                off_conf = 0.0
                for r in res:
                    if r.boxes is None:
                        continue
                    names = r.names if hasattr(r, "names") else {}
                    for box in r.boxes:
                        cls = int(box.cls.item())
                        conf = float(box.conf.item())
                        label = str(names.get(cls, str(cls))).lower()
                        if "off" in label or "no" in label:
                            off_conf = max(off_conf, conf)
                if off_conf >= 0.4:
                    return True, min(1.0, off_conf)
                return False, 0.0
            except Exception:
                pass

        h, w = frame.shape[:2]
        roi = frame[int(h * 0.35): int(h * 0.85), int(w * 0.15): int(w * 0.70)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 180)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=60, maxLineGap=20)
        if lines is None:
            return True, 0.55

        diag = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            if -2.4 < slope < -0.25:
                diag += 1

        if diag < 2:
            return True, 0.65
        return False, 0.0


def detect_phone_obstruction_tailgating(dets: list[dict], frame_shape: tuple[int, int, int]) -> dict:
    h, w = frame_shape[:2]
    driver_roi = (0, 0, int(w * 0.55), int(h * 0.75))
    lane_roi = (int(w * 0.30), int(h * 0.35), int(w * 0.70), h)

    phone, phone_conf = False, 0.0
    obstruction, obstruction_conf = False, 0.0
    tailgating, tailgating_conf = False, 0.0
    lead_distance_m = 999.0

    for d in dets:
        x1, y1, x2, y2 = d["bbox"]
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        area_ratio = (bw * bh) / (w * h)

        if d["class"] == ObjectDetector.PHONE_CLASS:
            if x1 < driver_roi[2] and y1 < driver_roi[3]:
                phone = True
                phone_conf = max(phone_conf, d["conf"])

        in_lane = x1 > lane_roi[0] and x2 < lane_roi[2] and y2 > lane_roi[1]
        if d["class"] in ObjectDetector.VEHICLE_CLASSES and in_lane:
            focal_px = 850.0
            distance = (1.8 * focal_px) / bw
            lead_distance_m = min(lead_distance_m, distance)
            if area_ratio > 0.13:
                obstruction = True
                obstruction_conf = max(obstruction_conf, min(1.0, area_ratio * 3.0))
            if distance < 10.0:
                tailgating = True
                tailgating_conf = max(tailgating_conf, min(1.0, (10.0 - distance) / 8.0))

    return {
        "phone": phone,
        "phone_conf": phone_conf,
        "obstruction": obstruction,
        "obstruction_conf": obstruction_conf,
        "tailgating": tailgating,
        "tailgating_conf": tailgating_conf,
        "lead_distance_m": lead_distance_m if lead_distance_m < 999.0 else 0.0,
        "ttc_sec": 0.0,
    }


@dataclass
class LeadVehicleState:
    distance_m: float
    timestamp_sec: float


class LeadVehicleTracker:
    """Lightweight lead-vehicle tracker for TTC estimation."""

    def __init__(self) -> None:
        self.prev: LeadVehicleState | None = None

    def update(self, scene: dict, timestamp_sec: float) -> dict:
        distance = float(scene.get("lead_distance_m", 0.0))
        if distance <= 0:
            self.prev = None
            return {"ttc_sec": 0.0, "closing_speed_mps": 0.0}

        ttc = 0.0
        closing = 0.0
        if self.prev and timestamp_sec > self.prev.timestamp_sec:
            dt = timestamp_sec - self.prev.timestamp_sec
            rel = self.prev.distance_m - distance
            closing = rel / dt
            if closing > 0.05:
                ttc = distance / closing

        self.prev = LeadVehicleState(distance_m=distance, timestamp_sec=timestamp_sec)
        return {"ttc_sec": round(ttc, 2), "closing_speed_mps": round(closing, 2)}


class SceneProfiler:
    """Estimates lighting and frame reliability to adapt thresholds safely."""

    def __init__(self) -> None:
        self._light_hist: deque[float] = deque(maxlen=30)
        self._reliability_hist: deque[float] = deque(maxlen=30)

    def profile(self, frame: np.ndarray) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mean_luma = float(np.mean(gray))
        sat = float(np.mean(hsv[:, :, 1]))
        val = float(np.mean(hsv[:, :, 2]))

        edges = cv2.Canny(gray, 80, 160)
        edge_density = float(np.mean(edges > 0))
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if mean_luma >= 115 and sat >= 42:
            scenario = "day"
        elif mean_luma >= 72:
            scenario = "dusk"
        else:
            scenario = "night"

        reliability = min(1.0, max(0.0, (edge_density * 3.0) + min(0.5, blur_var / 350.0)))
        self._light_hist.append(mean_luma)
        self._reliability_hist.append(reliability)

        avg_luma = float(np.mean(self._light_hist)) if self._light_hist else mean_luma
        avg_reliability = float(np.mean(self._reliability_hist)) if self._reliability_hist else reliability
        return {
            "scenario": scenario,
            "mean_luma": round(mean_luma, 2),
            "mean_val": round(val, 2),
            "avg_luma": round(avg_luma, 2),
            "edge_density": round(edge_density, 4),
            "reliability": round(avg_reliability, 3),
        }
