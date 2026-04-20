import cv2
import threading
import time
from flask import Flask, Response, render_template, jsonify, request
from config import CAMERA_INDEX
from sota import controller
from tracking import face_tracker

app = Flask(__name__)

# ========== カメラ ==========
_cap        = cv2.VideoCapture(CAMERA_INDEX)
_latest_frame = None
_frame_lock   = threading.Lock()

def _camera_loop():
    """カメラ映像を取得し続けるスレッド"""
    global _latest_frame
    while True:
        ret, frame = _cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        # フェイストラッキング処理
        frame, _ = face_tracker.process_frame(frame)
        with _frame_lock:
            _latest_frame = frame

threading.Thread(target=_camera_loop, daemon=True).start()

# ========== ストリーミング ==========
def _generate():
    while True:
        with _frame_lock:
            frame = _latest_frame
        if frame is None:
            time.sleep(0.05)
            continue
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route('/video_feed')
def video_feed():
    return Response(
        _generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# ========== ページ ==========
@app.route('/')
def index():
    return render_template('index.html')

# ========== API ==========
@app.route('/api/tracking', methods=['POST'])
def api_tracking():
    """トラッキングON/OFF"""
    data    = request.get_json()
    enabled = data.get('enabled', True)
    face_tracker.set_tracking(enabled)
    return jsonify({"status": "ok", "tracking": enabled})

@app.route('/api/led', methods=['POST'])
def api_led():
    """LED色変更"""
    data  = request.get_json()
    color = data.get('color', 'green')
    controller.send(led=color)
    return jsonify({"status": "ok", "color": color})

@app.route('/api/motion', methods=['POST'])
def api_motion():
    """モーション実行"""
    data   = request.get_json()
    motion = data.get('motion', 'nod')
    threading.Thread(
        target=controller.send,
        kwargs={"motion": motion},
        daemon=True
    ).start()
    return jsonify({"status": "ok", "motion": motion})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """初期姿勢に戻す"""
    controller.reset_posture()
    return jsonify({"status": "ok"})

@app.route('/api/status')
def api_status():
    """現在の状態を返す"""
    return jsonify({
        "tracking": face_tracker.is_tracking(),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)