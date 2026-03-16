# HTTPS 設定指南

## 為什麼需要 HTTPS？

瀏覽器的 `getUserMedia` API（相機/麥克風）需要安全上下文（Secure Context），也就是 HTTPS 或 localhost。

## 快速設定

### 1. 安裝 mkcert（Windows）

管理員權限打開 PowerShell：
```powershell
choco install mkcert
```

或下載 exe：https://github.com/FiloSottile/mkcert/releases

### 2. 產生憑證

```cmd
cd frontend
mkcert -install
mkcert 172.20.10.5
```

這會產生：
- `172.20.10.5.pem`（憑證）
- `172.20.10.5-key.pem`（密鑰）

### 3. 重新命名檔案

```cmd
copy 172.20.10.5.pem cert.pem
copy 172.20.10.5-key.pem key.pem
```

### 4. 啟動前端

```bash
npm run dev
```

現在用 `https://172.20.10.5:5173` 訪問就能使用相機了！

---

## 或者：使用 ngrok（更簡單）

```bash
ngrok http 5173
```

它會給你一個 HTTPS URL，直接給手機訪問即可。