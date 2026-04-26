import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def get_senders(creds, on_progress=None):
    main_service = build_service(creds)
    all_ids = search_messages(main_service, query="")
    total = len(all_ids)

    sender_counts = {}
    lock = threading.Lock()
    processed_count = 0
    chunk_size = 100
    chunks = [all_ids[i : i + chunk_size] for i in range(0, total, chunk_size)]

    def process_chunk(chunk):
        nonlocal processed_count
        service = build_service(creds)
        local_counts = {}

        def make_callback(req_id):
            def callback(_, response, exception):
                if exception or not response:
                    return
                headers = {h["name"]: h["value"] for h in response["payload"]["headers"]}
                raw = headers.get("From", "")
                name, addr = parseaddr(raw)
                key = addr.lower() if addr else raw
                local_counts[key] = local_counts.get(key, {"name": name or raw, "email": addr or raw, "count": 0})
                local_counts[key]["count"] += 1
            return callback

        batch = service.new_batch_http_request()
        for msg in chunk:
            batch.add(
                service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata", metadataHeaders=["From"]
                ),
                callback=make_callback(msg["id"]),
            )
        batch.execute()

        with lock:
            for key, data in local_counts.items():
                if key in sender_counts:
                    sender_counts[key]["count"] += data["count"]
                else:
                    sender_counts[key] = data
            processed_count += len(chunk)
            if on_progress:
                on_progress(processed_count, total)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            future.result()

    return sorted(sender_counts.values(), key=lambda x: x["count"], reverse=True)


def batch_delete(service, message_ids):
    # Gmail API 每次最多刪 1000 封
    for i in range(0, len(message_ids), 1000):
        chunk = message_ids[i : i + 1000]
        service.users().messages().batchDelete(userId="me", body={"ids": chunk}).execute()
