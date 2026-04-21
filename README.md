# sota-face-tracking

Sotaロボット向けのリアルタイム顔追従システムです。  
PCがWebカメラで顔を検出し、頭部の角度をローカルで計算してUDP経由でSotaに送信します。

## システム概要

```
PC (Python)
  └─ Webカメラ → 顔検出 (OpenCV)
              → 角度計算
              → UDP (JSON) ──→ Sota (Java)
                                  └─ サーボ制御
                                  └─ LED制御
                                  └─ モーション制御
```

## 機能

- リアルタイム顔追従（画面内で最も大きい顔を追従）
- デッドゾーン・最小角度変化による振動抑制
- LED色変更（green / blue / red / white / off）
- モーション制御（nod / shake / 右手上げ / 両手上げ / bye bye）
- FlaskによるWeb UI（カメラ映像 + コントロールパネル）
- レスポンシブデザイン対応

## 必要環境

### PC側
- Python 3.10+
- Webカメラ

### Sota側
- Sotaロボット
- Java実行環境（Edison上に搭載）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/futosawaguchi/sota-face-tracking.git
cd sota-face-tracking
```

### 2. 仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. .envファイルの作成

```bash
cp .env.example .env
```

`.env`を編集してください：

```
SOTA_IP=192.168.xx.xx
SOTA_PORT=9980
CAMERA_INDEX=0
```

### 4. Sotaのセットアップ

**Sotaの起動：**
1. 電源ボタンを押す
2. 上下ボタンを3秒長押し
3. IPアドレスを取得
4. SSHで接続：

```bash
ssh root@<SOTA_IP>
# password: edison00
```

**Javaファイルの転送とコンパイル：**

`java/SotaController.java`をSotaに転送してコンパイルしてください。  
コンパイルコマンドやディレクトリ構成はご自身のSota環境に合わせてください。

```bash
# PC側からSotaへ転送する例
scp java/SotaController.java root@<SOTA_IP>:/path/to/your/src/SotaController.java
```

> ⚠️ Sota内のディレクトリ構成や既存のSotaサンプルの場所は環境によって異なります。  
> 各自の環境に合わせてコンパイル・配置してください。

**Sotaで実行：**

```bash
./java_run.sh jp.vstone.sotatest.SotaController
```

### 5. PC側の起動

```bash
source venv/bin/activate
python app.py
```

ブラウザで開く: [http://localhost:5001](http://localhost:5001)

## ディレクトリ構成

```
sota-face-tracking/
├── app.py                  # Flaskエントリーポイント
├── config.py               # 設定ファイル
├── .env                    # 環境変数（Gitに含まれません）
├── .env.example            # 環境変数テンプレート
├── requirements.txt
├── sota/
│   └── controller.py       # UDP送信
├── tracking/
│   └── face_tracker.py     # 顔検出・角度計算
├── templates/
│   └── index.html          # Web UI
├── static/
│   └── style.css           # スタイル
└── java/
    └── SotaController.java # Sota側Javaプログラム
```

## パラメータ設定

`config.py`を編集することでトラッキングの挙動を調整できます：

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `SEND_INTERVAL` | `0.4` | UDP送信間隔（秒） |
| `DEAD_ZONE` | `30` | この範囲内の顔のズレは無視（ピクセル） |
| `SMOOTHING_ALPHA` | `0.0` | ローパスフィルタ係数（0.0=raw値そのまま） |
| `MIN_ANGLE_CHANGE` | `5.0` | 送信する最小角度変化量 |
| `HEAD_Y_MAX` | `300.0` | 首の左右最大角度 |
| `HEAD_P_MAX` | `100.0` | 首の前後最大角度 |
