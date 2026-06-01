from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import cv2

from tracker.calibration.data import CalibrationData


class CalibrationStore:
    def __init__(self, directory: str = "calibrations"):
        self.directory = directory

    def save(self, video_filename: str, calibration: CalibrationData) -> str:
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        safe_ts = timestamp.replace(":", "-")
        video_basename = Path(video_filename).stem
        filename = f"cal_{safe_ts}_{video_basename}.json"
        filepath = Path(self.directory) / filename

        data = calibration.to_dict()
        data["metadata"] = {
            "timestamp": timestamp,
            "video_filename": video_filename,
        }
        fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=self.directory)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(filepath))
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
        return str(filepath)

    def find_matching(self, video_path: str) -> Optional[CalibrationData]:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None

        frame_hash = hashlib.sha256(
            cv2.imencode(".png", frame)[1].tobytes()
        ).hexdigest()

        saved_dir = Path(self.directory)
        if not saved_dir.exists():
            return None

        for json_file in sorted(saved_dir.glob("*.json")):
            try:
                with open(json_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("video_frame0_hash") == frame_hash:
                return CalibrationData.from_dict(data)
            if data.get("video_frame0_hash"):
                continue

            stored_filename = data.get("metadata", {}).get("video_filename", "")
            if Path(stored_filename).stem == Path(video_path).stem:
                return CalibrationData.from_dict(data)

        return None

    def list_available(self) -> List[dict]:
        saved_dir = Path(self.directory)
        if not saved_dir.exists():
            return []

        entries = []
        for json_file in sorted(saved_dir.glob("*.json")):
            try:
                with open(json_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            metadata = data.get("metadata", {})
            entries.append({
                "filename": json_file.name,
                "timestamp": metadata.get("timestamp", ""),
                "video_filename": metadata.get("video_filename", ""),
            })
        return entries

    def delete(self, calibration_id: str) -> bool:
        saved_dir = Path(self.directory)
        for candidate in (calibration_id, f"{calibration_id}.json"):
            path = saved_dir / candidate
            if path.exists():
                os.remove(path)
                return True
        return False
