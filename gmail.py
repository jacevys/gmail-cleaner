from email.utils import parseaddr
from googleapiclient.discovery import build


def build_service(creds):
    return build("gmail", "v1", credentials=creds)


def get_total_messages(service):
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("messagesTotal", 0)


def count_messages(service, query):
    result = service.users().messages().list(
        userId="me", q=query, maxResults=1
    ).execute()
    return result.get("resultSizeEstimate", 0)


def search_messages(service, query, limit=None):
    messages = []
    page_token = None
    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": min(500, limit or 500)}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.users().messages().list(**kwargs).execute()
        batch = result.get("messages", [])
        messages.extend(batch)
        if limit and len(messages) >= limit:
            messages = messages[:limit]
            break
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return messages


def get_message_info(service, msg_id):
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject", "Date"])
        .execute()
    )
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
    }


def get_senders(service, on_progress=None):
    all_ids = search_messages(service, query="")
    sender_counts = {}
    chunk_size = 100

    for i in range(0, len(all_ids), chunk_size):
        chunk = all_ids[i : i + chunk_size]
        results = {}

        def make_callback(req_id):
            def callback(_, response, exception):
                if exception or not response:
                    return
                headers = {h["name"]: h["value"] for h in response["payload"]["headers"]}
                raw = headers.get("From", "")
                name, addr = parseaddr(raw)
                key = addr.lower() if addr else raw
                sender_counts[key] = sender_counts.get(key, {"name": name or raw, "email": addr or raw, "count": 0})
                sender_counts[key]["count"] += 1
            return callback

        batch = service.new_batch_http_request()
        for msg in chunk:
            batch.add(
                service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From"]),
                callback=make_callback(msg["id"]),
            )
        batch.execute()

        if on_progress:
            on_progress(min(i + chunk_size, len(all_ids)), len(all_ids))

    return sorted(sender_counts.values(), key=lambda x: x["count"], reverse=True)


def batch_delete(service, message_ids):
    # Gmail API 每次最多刪 1000 封
    for i in range(0, len(message_ids), 1000):
        chunk = message_ids[i : i + 1000]
        service.users().messages().batchDelete(userId="me", body={"ids": chunk}).execute()
