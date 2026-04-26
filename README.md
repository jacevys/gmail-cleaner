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

### `senders` — 寄件人統計

掃描整個信箱，列出每個寄件人的郵件數量排行。

```bash
uv run python main.py senders
uv run python main.py senders --limit 20
```

### `list` — 預覽郵件

列出符合條件的郵件，不執行任何刪除。

```bash
uv run python main.py list --from medium.com
uv run python main.py list --from newsletter@example.com --older-than 1y --limit 20
```

### `delete` — 批次刪除

建議操作流程：先用 `list` 確認範圍，再加 `--dry-run` 模擬，最後正式執行。

**Step 1** — 用 `list` 預覽符合條件的郵件，再加 `--dry-run` 模擬確認：

```bash
uv run python main.py list --from medium.com --older-than 30d
```

```bash
uv run python main.py delete --from medium.com --older-than 30d --dry-run

# 排除特定主旨關鍵字（保留中獎通知，刪除其餘）
uv run python main.py delete --from example.com --exclude-subject "中獎" --dry-run

# 排除多個關鍵字
uv run python main.py delete --from example.com --exclude-subject "中獎" --exclude-subject "收據" --dry-run
```

> **注意：** `--exclude-subject` 使用 Gmail 的詞語匹配，需填入完整詞語（如 `中獎通知`），不支援模糊字串比對。

**Step 2** — 確認無誤後正式刪除（刪除前會顯示數量、日期範圍與前 5 封預覽，並要求確認）：

```bash
uv run python main.py delete --from medium.com --older-than 30d
uv run python main.py delete --subject "優惠"
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

## 注意事項

> **警告：郵件刪除後無法復原。**
>
> 執行 `delete` 前，請務必先以 `list` 或 `--dry-run` 確認符合條件的郵件皆為預期刪除的對象。本工具依過濾條件批次刪除郵件，作者不對任何誤刪造成的資料損失負責。
