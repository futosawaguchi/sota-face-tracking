import cv2
import time
import threading
import numpy as np
from config import (
    DEAD_ZONE,
    SMOOTHING_ALPHA,
    MIN_ANGLE_CHANGE,
    HEAD_Y_MAX,
    HEAD_P_MAX,
    SEARCH_ANGLES,
    SEARCH_INTERVAL,
    SEND_INTERVAL,
)
from sota import controller

# ========== 状態管理 ==========
_tracking_enabled = True
_last_send_time   = 0.0
_prev_yaw         = 0.0
_prev_pitch       = 0.0
_searching        = False
_search_thread    = None
_lock             = threading.Lock()

# ========== Haar Cascade 初期化 ==========
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def set_tracking(enabled: bool):
    global _tracking_enabled, _searching
    _tracking_enabled = enabled
    if not enabled:
        _searching = False

def is_tracking() -> bool:
    return _tracking_enabled

def process_frame(frame: np.ndarray):
    global _prev_yaw, _prev_pitch, _last_send_time, _searching, _search_thread

    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2

    # 中心十字線
    cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (180, 180, 180), 1)
    cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (180, 180, 180), 1)

    # 顔検出
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces) == 0:
        # 顔消失 → キョロキョロ開始（重複起動しない）
        if _tracking_enabled:
            with _lock:
                if not _searching:
                    _searching = True
                    _search_thread = threading.Thread(
                        target=_search_loop, daemon=True
                    )
                    _search_thread.start()

        cv2.putText(frame, "No Face", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
        return frame, []

    # 顔が見つかった → キョロキョロ停止
    with _lock:
        _searching = False

    # 一番大きい顔
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_cx = x + fw // 2
    face_cy = y + fh // 2

    # 描画
    cv2.rectangle(frame, (x, y), (x + fw, y + fh), (80, 80, 80), 2)
    cv2.circle(frame, (face_cx, face_cy), 4, (80, 80, 80), -1)
    cv2.putText(frame, f"tracking", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1)

    if not _tracking_enabled:
        return frame, list(faces)

    # ========== 送信間隔チェック ==========
    now = time.time()
    if now - _last_send_time < SEND_INTERVAL:
        return frame, list(faces)

    # ========== 角度計算 ==========
    dx = face_cx - cx
    dy = face_cy - cy

    # デッドゾーン
    if abs(dx) < DEAD_ZONE: dx = 0
    if abs(dy) < DEAD_ZONE: dy = 0

    # 正規化 → 角度変換
    raw_yaw   = -(dx / (w / 2)) * HEAD_Y_MAX
    raw_pitch =  (dy / (h / 2)) * HEAD_P_MAX

    # ローパスフィルタ
    yaw   = SMOOTHING_ALPHA * raw_yaw   + (1 - SMOOTHING_ALPHA) * _prev_yaw
    pitch = SMOOTHING_ALPHA * raw_pitch + (1 - SMOOTHING_ALPHA) * _prev_pitch

    # 最小変化量チェック
    if abs(yaw - _prev_yaw) < MIN_ANGLE_CHANGE and \
       abs(pitch - _prev_pitch) < MIN_ANGLE_CHANGE:
        return frame, list(faces)

    # キョロキョロ中は送信しない
    with _lock:
        if _searching:
            return frame, list(faces)

    controller.send(servo={
        "Head_Y": int(round(yaw)),
        "Head_P": int(round(pitch)),
    })

    _prev_yaw       = yaw
    _prev_pitch     = pitch
    _last_send_time = now

    return frame, list(faces)


def _search_loop():
    """顔消失時にゆっくりキョロキョロして探す"""
    global _searching, _prev_yaw, _prev_pitch

    for angle in SEARCH_ANGLES:
        with _lock:
            if not _searching:
                return
        controller.send(servo={"Head_Y": angle, "Head_P": 0})
        _prev_yaw   = float(angle)
        _prev_pitch = 0.0
        time.sleep(SEARCH_INTERVAL)

    # 見つからなければ正面に戻る
    with _lock:
        still_searching = _searching

    if still_searching:
        controller.send(servo={"Head_Y": 0, "Head_P": 0})
        _prev_yaw   = 0.0
        _prev_pitch = 0.0
        with _lock:
            _searching = False