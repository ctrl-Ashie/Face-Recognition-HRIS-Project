from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
FACES_DIR = BASE_DIR / "data" / "faces"
MAX_SAMPLES = 10
FACE_SIZE = (128, 128)
DEFAULT_VERIFY_THRESHOLD = 0.88
IMPOSTOR_MARGIN = 0.08
REQUIRED_VERIFY_FRAMES = 5
MIN_PASS_FRAMES = 3
TEMPLATE_FILE = "template_vectors.npy"


def ensure_employee_folder(employee_id: str) -> Path:
    folder = FACES_DIR / employee_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def clear_employee_samples(employee_id: str) -> None:
    folder = FACES_DIR / employee_id
    if not folder.exists():
        return
    for item in folder.glob("*.png"):
        item.unlink(missing_ok=True)
    for item in folder.glob("*.npy"):
        item.unlink(missing_ok=True)


def save_face_sample(employee_id: str, face_bgr: np.ndarray, sample_index: int) -> Path:
    folder = ensure_employee_folder(employee_id)
    file_path = folder / f"sample_{sample_index:02d}.png"
    cv2.imwrite(str(file_path), face_bgr)
    return file_path


def _preprocess_face(face_bgr: np.ndarray) -> np.ndarray:
    # Build a richer embedding by using spatial LBP (local binary patterns) and a central pixel crop.
    # This spatial grid approach drastically reduces false positives compared to a flat global histogram.
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.resize(gray, FACE_SIZE)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    lbp_source = gray
    center = lbp_source[1:-1, 1:-1]
    lbp = np.zeros_like(center, dtype=np.uint8)
    neighbors = [
        lbp_source[:-2, :-2],
        lbp_source[:-2, 1:-1],
        lbp_source[:-2, 2:],
        lbp_source[1:-1, 2:],
        lbp_source[2:, 2:],
        lbp_source[2:, 1:-1],
        lbp_source[2:, :-2],
        lbp_source[1:-1, :-2],
    ]
    for idx, neighbor in enumerate(neighbors):
        lbp |= ((neighbor >= center).astype(np.uint8) << idx)

    # Compute spatial block histograms (e.g. 4x4 grid) for position-dependent texture matching
    h, w = lbp.shape
    grid_h, grid_w = h // 4, w // 4
    histograms = []
    
    for i in range(4):
        for j in range(4):
            block = lbp[i * grid_h:(i + 1) * grid_h, j * grid_w:(j + 1) * grid_w]
            hist, _ = np.histogram(block, bins=64, range=(0, 256), density=True)
            histograms.append(hist)

    # Add a downsampled center crop for direct structural/pixel matching
    center_crop = cv2.resize(gray[16:-16, 16:-16], (32, 32))
    pixel_vec = center_crop.astype(np.float32).flatten() / 255.0

    flat = np.concatenate([pixel_vec] + histograms).astype(np.float32)
    norm = float(np.linalg.norm(flat))
    if norm == 0:
        return flat
    return flat / norm


def load_employee_embeddings(employee_id: str) -> List[np.ndarray]:
    folder = FACES_DIR / employee_id
    if not folder.exists():
        return []

    embeddings: List[np.ndarray] = []
    for sample_file in sorted(folder.glob("sample_*.png")):
        img = cv2.imread(str(sample_file))
        if img is None:
            continue
        embeddings.append(_preprocess_face(img))
    return embeddings


def _employee_template_path(employee_id: str) -> Path:
    return FACES_DIR / employee_id / TEMPLATE_FILE


def build_employee_template(employee_id: str) -> Dict[str, int]:
    embeddings = load_employee_embeddings(employee_id)
    if not embeddings:
        raise RuntimeError("No valid face samples found to build template.")

    folder = ensure_employee_folder(employee_id)
    matrix = np.stack(embeddings).astype(np.float32)
    np.save(folder / TEMPLATE_FILE, matrix)
    return {"samples": int(matrix.shape[0]), "dim": int(matrix.shape[1])}


def load_employee_template(employee_id: str) -> Optional[np.ndarray]:
    template_path = _employee_template_path(employee_id)
    if template_path.exists():
        arr = np.load(template_path)
        if arr.ndim == 1:
            arr = np.expand_dims(arr, axis=0)
        return arr.astype(np.float32)

    embeddings = load_employee_embeddings(employee_id)
    if not embeddings:
        return None
    matrix = np.stack(embeddings).astype(np.float32)
    np.save(template_path, matrix)
    return matrix


def _max_similarity(live_embedding: np.ndarray, template_matrix: np.ndarray) -> float:
    similarities = template_matrix @ live_embedding
    return float(np.max(similarities)) if similarities.size else 0.0


def _mean_similarity(live_embedding: np.ndarray, template_matrix: np.ndarray) -> float:
    similarities = template_matrix @ live_embedding
    return float(np.mean(similarities)) if similarities.size else 0.0


def verify_claimed_employee(
    claimed_employee_id: str,
    face_crops: List[np.ndarray],
    all_employee_ids: List[str],
    threshold: float = DEFAULT_VERIFY_THRESHOLD,
    impostor_margin: float = IMPOSTOR_MARGIN,
    required_frames: int = REQUIRED_VERIFY_FRAMES,
    min_pass_frames: int = MIN_PASS_FRAMES,
) -> Dict[str, object]:
    # Multi-frame consensus: each frame must pass threshold + impostor margin checks.
    if len(face_crops) < required_frames:
        return {
            "matched": False,
            "score": 0.0,
            "best_other": 0.0,
            "frames_passed": 0,
            "frames_total": len(face_crops),
            "reason": f"Need at least {required_frames} recent face frames.",
        }

    claimed_template = load_employee_template(claimed_employee_id)
    if claimed_template is None or len(claimed_template) == 0:
        return {
            "matched": False,
            "score": 0.0,
            "best_other": 0.0,
            "frames_passed": 0,
            "frames_total": len(face_crops),
            "reason": "No enrolled template found for employee.",
        }

    other_ids = [employee_id for employee_id in all_employee_ids if employee_id != claimed_employee_id]
    other_templates = {employee_id: load_employee_template(employee_id) for employee_id in other_ids}

    pass_count = 0
    frame_scores: List[float] = []
    best_other_overall = 0.0
    threshold_fail_count = 0
    margin_fail_count = 0

    for crop in face_crops[-required_frames:]:
        live_embedding = _preprocess_face(crop)
        peak_score = _max_similarity(live_embedding, claimed_template)
        mean_score = _mean_similarity(live_embedding, claimed_template)
        claimed_score = (0.7 * peak_score) + (0.3 * mean_score)

        other_scores = []
        for template in other_templates.values():
            if template is None or len(template) == 0:
                continue
            other_peak = _max_similarity(live_embedding, template)
            other_mean = _mean_similarity(live_embedding, template)
            other_scores.append((0.7 * other_peak) + (0.3 * other_mean))
        best_other = max(other_scores) if other_scores else 0.0
        best_other_overall = max(best_other_overall, best_other)

        if claimed_score >= threshold and (claimed_score - best_other) >= impostor_margin:
            pass_count += 1
        else:
            if claimed_score < threshold:
                threshold_fail_count += 1
            else:
                margin_fail_count += 1
        frame_scores.append(claimed_score)

    avg_score = float(np.mean(frame_scores)) if frame_scores else 0.0
    matched = pass_count >= min_pass_frames
    if matched:
        reason = "Verification passed with local multi-frame consensus."
    elif margin_fail_count > threshold_fail_count:
        reason = "Verification failed: impostor margin violations detected."
    else:
        reason = "Verification failed: threshold consensus not met."

    return {
        "matched": matched,
        "score": avg_score,
        "best_other": best_other_overall,
        "frames_passed": pass_count,
        "frames_total": required_frames,
        "reason": reason,
    }


def verifier_status() -> Dict[str, str]:
    return {"ready": "true", "message": "Local verifier ready."}


def get_face_region(frame_bgr: np.ndarray, face_rect: Tuple[int, int, int, int], margin: int = 10) -> Optional[np.ndarray]:
    x, y, w, h = face_rect
    h_frame, w_frame = frame_bgr.shape[:2]

    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(w_frame, x + w + margin)
    y2 = min(h_frame, y + h + margin)

    if x2 <= x1 or y2 <= y1:
        return None

    return frame_bgr[y1:y2, x1:x2].copy()


def has_enough_samples(employee_id: str, required: int = MAX_SAMPLES) -> bool:
    folder = FACES_DIR / employee_id
    if not folder.exists():
        return False
    return len(list(folder.glob("sample_*.png"))) >= required


def list_employee_photo_paths(employee_id: str) -> List[Path]:
    folder = FACES_DIR / employee_id
    if not folder.exists():
        return []
    return sorted(folder.glob("sample_*.png"))


def rename_employee_face_folder(old_employee_id: str, new_employee_id: str) -> None:
    old_folder = FACES_DIR / old_employee_id
    if not old_folder.exists() or old_employee_id == new_employee_id:
        return

    new_folder = FACES_DIR / new_employee_id
    if new_folder.exists():
        for item in new_folder.glob("*.png"):
            item.unlink(missing_ok=True)
        new_folder.rmdir()
    old_folder.rename(new_folder)


def delete_employee_face_data(employee_id: str) -> None:
    folder = FACES_DIR / employee_id
    if not folder.exists():
        return

    for item in folder.glob("*.png"):
        item.unlink(missing_ok=True)
    for other in folder.glob("*"):
        if other.is_file():
            other.unlink(missing_ok=True)
    folder.rmdir()
