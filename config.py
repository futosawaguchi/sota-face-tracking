import os
from dotenv import load_dotenv

load_dotenv()

# ========== SOTA設定 ==========
SOTA_IP   = os.getenv("SOTA_IP", "192.168.11.5")
SOTA_PORT = int(os.getenv("SOTA_PORT", 9980))

# ========== カメラ設定 ==========
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))

# ========== フェイストラッキング設定 ==========
# 送信間隔（秒）
SEND_INTERVAL = 0.4

# デッドゾーン（ピクセル）：この範囲内のズレは無視
DEAD_ZONE = 30

# ローパスフィルタ係数（0.1〜0.3推奨：小さいほど滑らか）
SMOOTHING_ALPHA = 0.0

# 最小送信角度変化（この値未満の変化は送信しない）
MIN_ANGLE_CHANGE = 5.0

# 首の可動範囲
HEAD_Y_MAX = 300.0   # 左右
HEAD_P_MAX = 100.0   # 前後

# 顔消失時のキョロキョロ設定
SEARCH_ANGLES  = [-200, 200, -200, 0]  # キョロキョロの角度列
SEARCH_INTERVAL = 0.8                  # 各角度の待機時間（秒）