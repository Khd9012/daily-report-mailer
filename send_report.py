import argparse
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def format_task_blocks(tasks: list[dict]) -> str:
    if not tasks:
        return "없음"

    blocks = []
    for index, task in enumerate(tasks, 1):
        project = task.get("project", "프로젝트명")
        lines = [f"{index}. {project}"]

        for item in task.get("items", []):
            lines.append(f"- {item}")

        links = task.get("links", [])
        if links:
            lines.append("* 관련 링크/파일")
            for link in links:
                lines.append(f"  - {link}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def format_list(items: list[str]) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item}" for item in items)


def build_sender() -> dict:
    smtp_user = os.environ.get("SMTP_USER", "")
    fallback_name = smtp_user.split("@", 1)[0] if smtp_user else "이름"
    return {
        "displayName": os.environ.get("SENDER_NAME") or fallback_name,
        "team": os.environ.get("SENDER_TEAM") or "OO팀",
        "title": os.environ.get("SENDER_TITLE") or "",
        "email": smtp_user,
    }


def build_daily(sender: dict, report: dict) -> tuple[str, str]:
    name = sender["displayName"]
    team = sender.get("team", "OO팀")
    date = report["date"]
    day = report.get("day", "")
    date_label = f"{date} ({day})" if day else date

    subject = f"[일일보고] {date_label} 일일보고 - {name}"
    body = f"""안녕하세요, {team} {name}입니다.
{date_label} 일일보고를 작성하여 송부드립니다.

하기 내용 확인 부탁드립니다.

[금일 진행 업무]

{format_task_blocks(report.get("todayTasks", []))}

[이슈사항]

{format_task_blocks(report.get("issues", []))}

[명일 예정 업무]

{format_task_blocks(report.get("tomorrowTasks", []))}
"""
    return subject, body.strip() + "\n"


def build_weekly(sender: dict, report: dict) -> tuple[str, str]:
    name = sender["displayName"]
    team = sender.get("team", "OO팀")
    month = report["month"]
    week = report["week"]
    week_label = f"{month} {week}"

    subject = f"[주간보고] {week_label} 주간보고 - {name}"
    body = f"""안녕하세요, {team} {name}입니다.
{week_label} 주간보고를 작성하여 송부드립니다.

하기 내용 확인 부탁드립니다.

[금주 진행 업무]

{format_task_blocks(report.get("thisWeekTasks", []))}

[이슈사항]

{format_task_blocks(report.get("issues", []))}

[차주 예정 업무]

{format_task_blocks(report.get("nextWeekTasks", []))}

[종합 의견]

{format_list(report.get("summary", []))}
"""
    return subject, body.strip() + "\n"


def normalize_addresses(values: list[str] | None) -> list[str]:
    return [value.strip() for value in values or [] if value.strip()]


def parse_env_addresses(name: str) -> list[str] | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def get_recipients(report_type: str) -> tuple[list[str], list[str], list[str]]:
    prefix = "DAILY_REPORT" if report_type == "daily" else "WEEKLY_REPORT"
    report_to = parse_env_addresses(f"{prefix}_TO")
    report_cc = parse_env_addresses(f"{prefix}_CC")
    report_bcc = parse_env_addresses(f"{prefix}_BCC")

    if report_to is None and report_cc is None and report_bcc is None:
        report_to = parse_env_addresses("REPORT_TO")
        report_cc = parse_env_addresses("REPORT_CC")
        report_bcc = parse_env_addresses("REPORT_BCC")

    return report_to or [], report_cc or [], report_bcc or []


def build_message(report_type: str, sender: dict, subject: str, body: str) -> tuple[EmailMessage, list[str]]:
    smtp_user = os.environ.get("SMTP_USER") or sender.get("email") or "no-reply@example.com"
    from_name = os.environ.get("DEFAULT_FROM_NAME") or sender.get("displayName") or smtp_user
    to, cc, bcc = get_recipients(report_type)

    if not to and not cc and not bcc:
        raise SystemExit("No recipients found. Add at least one to/cc/bcc address.")

    msg = EmailMessage()
    msg["From"] = formataddr((from_name, smtp_user))
    if to:
        msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body)

    return msg, to + cc + bcc


def send_message(msg: EmailMessage, all_recipients: list[str]) -> None:
    host = require_env("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "465"))
    secure = os.environ.get("SMTP_SECURE", "true").lower() in {"1", "true", "yes", "y"}
    user = require_env("SMTP_USER")
    password = require_env("SMTP_PASSWORD")

    if secure:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg, to_addrs=all_recipients)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(user, password)
            smtp.send_message(msg, to_addrs=all_recipients)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and send daily/weekly report email.")
    parser.add_argument("--type", choices=["daily", "weekly"], required=True)
    parser.add_argument("--report", required=True, help="Path to report JSON file.")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env(ROOT / args.env)

    report = read_json(ROOT / args.report)
    sender = build_sender()
    if args.type == "daily":
        subject, body = build_daily(sender, report)
    else:
        subject, body = build_weekly(sender, report)

    msg, all_recipients = build_message(args.type, sender, subject, body)

    if args.dry_run:
        print("----- EMAIL PREVIEW -----")
        print(f"From: {msg['From']}")
        print(f"To: {msg.get('To', '')}")
        print(f"Cc: {msg.get('Cc', '')}")
        print(f"Subject: {msg['Subject']}")
        print()
        print(body)
        print("----- END PREVIEW -----")
        return

    send_message(msg, all_recipients)
    print("Sent successfully.")


if __name__ == "__main__":
    main()
