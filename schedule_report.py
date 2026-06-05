import argparse
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
TASK_DIR = ROOT / ".scheduled"
KST = ZoneInfo("Asia/Seoul")


def parse_clock(value: str) -> time:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not match:
        raise argparse.ArgumentTypeError("Use HH:MM format, for example 13:00.")

    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise argparse.ArgumentTypeError("Time must be between 00:00 and 23:59.")

    return time(hour=hour, minute=minute)


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD format, for example 2026-06-05.") from exc


def resolve_existing_path(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    return path


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sanitize_task_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return normalized or "report"


def build_runner(
    python_path: Path,
    report_type: str,
    report_path: Path,
    env_path: Path,
    task_name: str,
    scheduled_at: datetime,
) -> Path:
    TASK_DIR.mkdir(exist_ok=True)

    safe_name = sanitize_task_name(task_name)
    runner_path = TASK_DIR / f"{safe_name}.cmd"
    log_path = TASK_DIR / f"{safe_name}.log"
    send_args = [
        str(python_path),
        str(ROOT / "send_report.py"),
        "--type",
        report_type,
        "--report",
        relative_or_absolute(report_path),
        "--env",
        relative_or_absolute(env_path),
    ]
    send_command = subprocess.list2cmdline(send_args)
    root_arg = subprocess.list2cmdline([str(ROOT)])
    log_arg = subprocess.list2cmdline([str(log_path)])

    runner_path.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                "chcp 65001 > nul",
                "set PYTHONUTF8=1",
                f"cd /d {root_arg}",
                f"echo ===== {scheduled_at.isoformat()} ===== >> {log_arg}",
                f"{send_command} >> {log_arg} 2>&1",
                "set EXIT_CODE=%ERRORLEVEL%",
                f"echo Exit code: %EXIT_CODE% >> {log_arg}",
                "exit /b %EXIT_CODE%",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return runner_path


def run_preview(python_path: Path, report_type: str, report_path: Path, env_path: Path) -> None:
    preview_args = [
        str(python_path),
        str(ROOT / "send_report.py"),
        "--type",
        report_type,
        "--report",
        relative_or_absolute(report_path),
        "--env",
        relative_or_absolute(env_path),
        "--dry-run",
    ]
    result = subprocess.run(preview_args, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def create_task(task_name: str, runner_path: Path, scheduled_at: datetime, force: bool) -> None:
    schtasks = shutil.which("schtasks")
    if not schtasks:
        raise SystemExit("Windows Task Scheduler command not found: schtasks")

    command = [
        schtasks,
        "/Create",
        "/SC",
        "ONCE",
        "/TN",
        task_name,
        "/TR",
        subprocess.list2cmdline([str(runner_path)]),
        "/ST",
        scheduled_at.strftime("%H:%M"),
        "/SD",
        scheduled_at.strftime("%m/%d/%Y"),
    ]
    if force:
        command.append("/F")

    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Schedule a one-time report email with Windows Task Scheduler.")
    parser.add_argument("--type", choices=["daily", "weekly", "remote"], required=True)
    parser.add_argument("--report", required=True, help="Report JSON path.")
    parser.add_argument("--at", required=True, type=parse_clock, help="Send time in HH:MM, for example 13:00.")
    parser.add_argument("--date", type=parse_date, help="Send date in YYYY-MM-DD. Defaults to today in Asia/Seoul.")
    parser.add_argument("--env", default=".env", help="Env file path. Defaults to .env.")
    parser.add_argument("--name", help="Windows task name.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used by the scheduled task.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing task with the same name.")
    parser.add_argument("--dry-run", action="store_true", help="Preview and print the schedule command without creating it.")
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("schedule_report.py currently supports Windows Task Scheduler only.")

    send_date = args.date or datetime.now(KST).date()
    scheduled_at = datetime.combine(send_date, args.at, tzinfo=KST)
    now = datetime.now(KST)
    if scheduled_at <= now:
        raise SystemExit(f"Scheduled time is in the past: {scheduled_at.strftime('%Y-%m-%d %H:%M')}")

    report_path = resolve_existing_path(args.report, "Report")
    env_path = resolve_existing_path(args.env, "Env file")
    python_path = resolve_existing_path(args.python, "Python executable")

    task_name = args.name or f"daily-report-mailer-{args.type}-{send_date.isoformat()}-{args.at.strftime('%H%M')}"

    if args.dry_run:
        runner_path = TASK_DIR / f"{sanitize_task_name(task_name)}.cmd"
        run_preview(python_path, args.type, report_path, env_path)
        print("----- SCHEDULE PREVIEW -----")
        print(f"Task: {task_name}")
        print(f"Run at: {scheduled_at.strftime('%Y-%m-%d %H:%M')} Asia/Seoul")
        print(f"Runner: {runner_path}")
        print("No task or runner file was created because --dry-run was used.")
        return

    run_preview(python_path, args.type, report_path, env_path)
    runner_path = build_runner(python_path, args.type, report_path, env_path, task_name, scheduled_at)
    create_task(task_name, runner_path, scheduled_at, args.force)
    print(f"Scheduled: {task_name}")
    print(f"Run at: {scheduled_at.strftime('%Y-%m-%d %H:%M')} Asia/Seoul")
    print(f"Runner: {runner_path}")


if __name__ == "__main__":
    main()
