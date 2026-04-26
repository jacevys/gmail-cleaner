import click
from auth import get_credentials
from gmail import build_service, search_messages, get_message_info, batch_delete, get_total_messages, get_senders


def build_query(sender, subject, older_than, exclude_subject=()):
    parts = []
    if sender:
        parts.append(f"from:{sender}")
    if subject:
        parts.append(f"subject:{subject}")
    if older_than:
        parts.append(f"older_than:{older_than}")
    for ex in exclude_subject:
        parts.append(f"-subject:{ex}")
    return " ".join(parts) if parts else None


@click.group()
def cli():
    """Gmail 郵件清理工具"""


@cli.command()
def auth():
    """OAuth2 登入授權"""
    get_credentials()
    click.echo("授權成功")


@cli.command("list")
@click.option("--from", "sender", help="寄件人，例如 medium.com")
@click.option("--subject", help="主旨關鍵字")
@click.option("--older-than", help="早於多久，例如 30d、1y")
@click.option("--exclude-subject", multiple=True, help="排除含此主旨關鍵字的郵件（可多次使用）")
@click.option("--limit", default=50, show_default=True, help="最多顯示幾封")
def list_cmd(sender, subject, older_than, exclude_subject, limit):
    """列出符合條件的郵件"""
    query = build_query(sender, subject, older_than, exclude_subject)
    if not query:
        click.echo("請至少提供一個過濾條件（--from / --subject / --older-than）")
        return

    creds = get_credentials()
    service = build_service(creds)

    click.echo(f"搜尋：{query}")
    messages = search_messages(service, query, limit=limit)
    if not messages:
        click.echo("沒有符合的郵件")
        return

    click.echo(f"找到 {len(messages)} 封：\n")
    for msg in messages:
        info = get_message_info(service, msg["id"])
        click.echo(f"  [{info['date'][:16]}]  {info['from'][:40]:<40}  {info['subject'][:60]}")


@cli.command()
@click.option("--from", "sender", help="寄件人，例如 medium.com")
@click.option("--subject", help="主旨關鍵字")
@click.option("--older-than", help="早於多久，例如 30d、1y")
@click.option("--exclude-subject", multiple=True, help="排除含此主旨關鍵字的郵件（可多次使用）")
@click.option("--limit", default=None, type=int, help="最多刪幾封（預設全部）")
@click.option("--dry-run", is_flag=True, help="只顯示數量，不實際刪除")
def delete(sender, subject, older_than, exclude_subject, limit, dry_run):
    """批次刪除符合條件的郵件"""
    query = build_query(sender, subject, older_than, exclude_subject)
    if not query:
        click.echo("請至少提供一個過濾條件（--from / --subject / --older-than）")
        return

    creds = get_credentials()
    service = build_service(creds)

    total_before = get_total_messages(service)
    click.echo(f"信箱總郵件數：{total_before}")

    click.echo(f"搜尋：{query}")
    all_messages = search_messages(service, query, limit=None)
    if not all_messages:
        click.echo("沒有符合的郵件")
        return

    messages = all_messages[:limit] if limit else all_messages
    click.echo(f"符合過濾器：{len(all_messages)} 封，本次處理：{len(messages)} 封")

    newest = get_message_info(service, messages[0]["id"])
    oldest = get_message_info(service, messages[-1]["id"])
    click.echo(f"日期範圍：{oldest['date'][:16]}  ~  {newest['date'][:16]}")

    click.echo("前 5 封：")
    previews = [newest] + [get_message_info(service, messages[i]["id"]) for i in range(1, min(5, len(messages)))]
    for info in previews:
        click.echo(f"  [{info['date'][:16]}]  {info['subject'][:60]}")

    if dry_run:
        click.echo("（dry-run 模式，不執行刪除）")
        return

    click.confirm("確定要刪除這些郵件？", abort=True)
    ids = [m["id"] for m in messages]
    batch_delete(service, ids)

    total_after = get_total_messages(service)
    click.echo(f"已刪除 {len(ids)} 封，剩餘總郵件數：{total_after}")


@cli.command()
@click.option("--limit", default=50, show_default=True, help="顯示前幾名")
def senders(limit):
    """統計信箱中每個寄件人的郵件數量"""
    creds = get_credentials()

    click.echo("掃描中，請稍候...")

    def on_progress(done, total):
        click.echo(f"\r處理中：{done}/{total}", nl=False)

    results = get_senders(creds, on_progress=on_progress)
    click.echo()

    name_w, email_w = 30, 35
    click.echo(f"{'寄件人名稱':<{name_w}}  {'Email':<{email_w}}  郵件數")
    click.echo("-" * (name_w + email_w + 12))
    for s in results[:limit]:
        name = s["name"][:name_w]
        email = s["email"][:email_w]
        click.echo(f"{name:<{name_w}}  {email:<{email_w}}  {s['count']}")


if __name__ == "__main__":
    cli()
