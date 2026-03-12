# MeetLove 後端配置

# 伺服器綁定位址
HOST = "0.0.0.0"
PORT = 8000

# CORS 允許的來源（用逗號分隔，* 表示允許所有）
# 範例: "http://localhost:5173,http://192.168.1.100:5173"
CORS_ORIGINS = "*"

# Socket.IO 設定
SOCKET_PING_TIMEOUT = 60000
SOCKET_PING_INTERVAL = 25000