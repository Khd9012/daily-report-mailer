import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]
WEEK_LABELS_KO = ["첫째주", "둘째주", "셋째주", "넷째주", "다섯째주", "여섯째주"]
REMOTE_WORK_TIME_SLOTS = {
    "morning": ("1", "09:00~12:00", "오전"),
    "afternoon": ("2", "13:00~15:30", "오후"),
    "final-short": ("3", "15:30~17:00", "마감/단축근무"),
    "final-normal": ("4", "15:30~18:00", "마감/일반근무"),
}


def today_kst() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul"))


def week_of_month(dt: datetime) -> str:
    week_index = (dt.day - 1) // 7
    return WEEK_LABELS_KO[min(week_index, len(WEEK_LABELS_KO) - 1)]


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_multiline(prompt: str) -> list[str]:
    print(prompt)
    print("  - 한 줄에 하나씩 입력하세요. 빈 줄이면 종료합니다.")
    items = []
    while True:
        value = input("  > ").strip()
        if not value:
            break
        items.append(value)
    return items


def ask_task_blocks(section_name: str) -> list[dict]:
    print(f"\n[{section_name}]")
    print("프로젝트를 여러 개 입력할 수 있습니다. 프로젝트명이 비어 있으면 종료합니다.")

    blocks = []
    while True:
        project = ask("프로젝트명: ")
        if not project:
            break

        items = ask_multiline("업무 내용")
        links = ask_multiline("관련 링크/파일")
        blocks.append(
            {
                "project": project,
                "items": items,
                "links": links,
            }
        )

    return blocks


def resolve_remote_work_time(slot: str) -> tuple[str, str]:
    normalized = slot.strip()
    for key, (number, work_time, _label) in REMOTE_WORK_TIME_SLOTS.items():
        if normalized in {key, number}:
            return key, work_time

    valid_slots = ", ".join(REMOTE_WORK_TIME_SLOTS)
    raise SystemExit(f"Invalid remote work time slot: {slot}. Use one of: {valid_slots}")


def ask_remote_work_time() -> tuple[str, str]:
    print("\n[재택업무보고 시간]")
    for key, (number, work_time, label) in REMOTE_WORK_TIME_SLOTS.items():
        print(f"{number}. {work_time} ({label}, --slot {key})")

    selected = ask("시간대 선택 [기본: 1]: ") or "1"
    return resolve_remote_work_time(selected)


def build_daily() -> dict:
    now = today_kst()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "day": WEEKDAYS_KO[now.weekday()],
        "yesterdayTasks": ask_task_blocks("작일 예정 업무"),
        "todayTasks": ask_task_blocks("금일 예정 업무"),
        "issues": ask_task_blocks("이슈사항"),
        "tomorrowTasks": ask_task_blocks("명일 예정 업무"),
    }


def build_weekly() -> dict:
    now = today_kst()
    return {
        "month": now.strftime("%Y-%m"),
        "week": week_of_month(now),
        "thisWeekTasks": ask_task_blocks("금주 진행 업무"),
        "issues": ask_task_blocks("이슈사항"),
        "nextWeekTasks": ask_task_blocks("차주 예정 업무"),
        "summary": ask_multiline("\n[종합 의견]"),
    }


def build_remote(slot: str | None = None) -> dict:
    now = today_kst()
    work_time_slot, work_time = resolve_remote_work_time(slot) if slot else ask_remote_work_time()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "day": WEEKDAYS_KO[now.weekday()],
        "workTimeSlot": work_time_slot,
        "workTime": work_time,
        "morningTasks": ask_task_blocks("오전 업무"),
        "issues": ask_task_blocks("이슈사항"),
    }


def default_output_path(report_type: str) -> Path:
    now = today_kst()
    if report_type == "daily":
        return ROOT / "reports" / f"daily.{now.strftime('%Y-%m-%d')}.json"
    if report_type == "remote":
        return ROOT / "reports" / f"remote.{now.strftime('%Y-%m-%d')}.json"
    return ROOT / "reports" / f"weekly.{now.strftime('%Y-%m')}.{week_of_month(now)}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a report JSON file interactively.")
    parser.add_argument("--type", choices=["daily", "weekly", "remote"], required=True)
    parser.add_argument("--out", help="Output JSON path. Defaults to reports/<type>.<date>.json")
    parser.add_argument(
        "--slot",
        help="Remote report time slot: morning, afternoon, final-short, final-normal. Numeric aliases 1-4 are also accepted.",
    )
    args = parser.parse_args()

    if args.type == "daily":
        report = build_daily()
    elif args.type == "weekly":
        report = build_weekly()
    else:
        report = build_remote(args.slot)
    out_path = Path(args.out) if args.out else default_output_path(args.type)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nCreated: {out_path}")


if __name__ == "__main__":
    main()
