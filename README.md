# gmail-cleaner

Gmail 郵件清理 CLI，透過 Gmail API 批次搜尋、預覽與刪除郵件，並支援寄件人統計。

## 安裝

需要 Python 3.11+，建議使用 [uv](https://github.com/astral-sh/uv)。

```bash
uv sync
```

## 授權設定

1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 建立 OAuth 2.0 憑證
2. 下載 `credentials.json` 放到專案根目錄
3. 執行授權：

```bash
uv run python main.py auth
```

授權完成後會產生 `token.json`，之後無需重新登入。

## 指令

### `list` — 預覽郵件

列出符合條件的郵件，不執行任何刪除。

```bash
uv run python main.py list --from medium.com
uv run python main.py list --from newsletter@example.com --older-than 1y --limit 20
```

### `delete` — 批次刪除

刪除前會顯示數量、日期範圍與前 5 封預覽，並要求確認。

```bash
uv run python main.py delete --from medium.com --older-than 30d
uv run python main.py delete --subject "優惠" --dry-run   # 模擬，不實際刪除
```

### `senders` — 寄件人統計

掃描整個信箱，列出每個寄件人的郵件數量排行。

```bash
uv run python main.py senders
uv run python main.py senders --limit 20
```

## 過濾條件

| 選項 | 說明 | 範例 |
|------|------|------|
| `--from` | 寄件人 | `medium.com`、`no-reply@example.com` |
| `--subject` | 主旨關鍵字 | `"每週報告"` |
| `--older-than` | 早於指定時間 | `30d`、`6m`、`1y` |
| `--exclude-subject` | 排除含此關鍵字的郵件（可多次使用） | `--exclude-subject 收據` |
| `--limit` | 限制數量 | `100` |
| `--dry-run` | 模擬執行，不實際刪除 | — |
