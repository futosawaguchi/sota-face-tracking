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
)
from sota import controller

# ========== 状態管理 ==========
_tracking_enabled = True
_last_send_time   = 0.0
_prev_yaw         = 0.0
_prev_pitch       = 0.0
_searching        = False  # キョロキョロ中フラグ
_search_thread    = None

# ========== Haar Cascade 初期化 ==========
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def set_tracking(enabled: bool):
    """トラッキングのON/OFFを切り替える"""
    global _tracking_enabled
    _tracking_enabled = enabled

def is_tracking() -> bool:
    return _tracking_enabled

def process_frame(frame: np.ndarray) -> tuple[np.ndarray, list]:
    """
    フレームを受け取り、顔検出・角度計算・SOTA送信を行う

    Parameters
    ----------
    frame : np.ndarray  カメラから取得したフレーム

    Returns
    -------
    frame : np.ndarray  描画済みフレーム
    faces : list        検出された顔のリスト [(x, y, w, h), ...]
    """
    global _prev_yaw, _prev_pitch, _last_send_time, _searching, _search_thread

    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2

    # 中心十字線
    cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (255, 0, 0), 1)
    cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (255, 0, 0), 1)

    # グレースケール変換・顔検出
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5
    )

    if len(faces) == 0:
        # 顔が消えたらキョロキョロ開始
        if _tracking_enabled and not _searching:
            _searching = True
            _search_thread = threading.Thread(
                target=_search_loop, daemon=True
            )
            _search_thread.start()

        cv2.putText(frame, "No Face", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return frame, []

    # 顔が見つかったらキョロキョロ停止
    _searching = False

    # 一番大きい顔を選択
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_cx = x + fw // 2
    face_cy = y + fh // 2

    # 描画
    cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
    cv2.circle(frame, (face_cx, face_cy), 5, (0, 255, 0), -1)
    cv2.putText(frame, f"Face ({face_cx}, {face_cy})", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, f"Faces: {len(faces)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    if not _tracking_enabled:
        return frame, list(faces)

    # ========== 角度計算 ==========
    now = time.time()
    if now - _last_send_time < 0.1:
        return frame, list(faces)

    dx = face_cx - cx
    dy = face_cy - cy

    # デッドゾーン
    if abs(dx) < DEAD_ZONE: dx = 0
    if abs(dy) < DEAD_ZONE: dy = 0

    # 正規化 → 角度変換
    raw_yaw   = -(dx / (w / 2)) * HEAD_Y_MAX
    raw_pitch =  (dy / (h / 2)) * HEAD_P_MAX

    # ローパスフィルタ（指数移動平均）
    yaw   = SMOOTHING_ALPHA * raw_yaw   + (1 - SMOOTHING_ALPHA) * _prev_yaw
    pitch = SMOOTHING_ALPHA * raw_pitch + (1 - SMOOTHING_ALPHA) * _prev_pitch

    # 最小変化量チェック（振動抑制）
    if abs(yaw - _prev_yaw) < MIN_ANGLE_CHANGE and \
       abs(pitch - _prev_pitch) < MIN_ANGLE_CHANGE:
        return frame, list(faces)

    # 送信
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
        if not _searching:
            return
        controller.send(servo={"Head_Y": angle, "Head_P": 0})
        _prev_yaw   = float(angle)
        _prev_pitch = 0.0
        time.sleep(SEARCH_INTERVAL)

    # 見つからなければ正面に戻る
    if _searching:
        controller.send(servo={"Head_Y": 0, "Head_P": 0})
        _prev_yaw   = 0.0
        _prev_pitch = 0.0
        _searching  = False