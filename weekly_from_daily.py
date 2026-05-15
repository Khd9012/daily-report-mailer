import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
WEEK_LABELS_KO = ["첫째주", "둘째주", "셋째주", "넷째주", "다섯째주", "여섯째주"]


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def today_kst() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def week_of_month(day: date) -> str:
    week_index = (day.day - 1) // 7
    return WEEK_LABELS_KO[min(week_index, len(WEEK_LABELS_KO) - 1)]


def week_range(base_day: date, mode: str) -> tuple[date, date]:
    monday = base_day - timedelta(days=base_day.weekday())
    if mode == "previous":
        monday -= timedelta(days=7)
    friday = monday + timedelta(days=4)
    return monday, friday


def date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def daily_path(day: date) -> Path:
    return ROOT / "reports" / f"daily.{day.isoformat()}.json"


def prefix_blocks(day: date, blocks: list[dict]) -> list[dict]:
    prefixed = []
    for block in blocks:
        project = block.get("project", "프로젝트명")
        prefixed.append(
            {
                "project": f"{day.isoformat()} / {project}",
                "items": block.get("items", []),
                "links": block.get("links", []),
            }
        )
    return prefixed


def build_weekly_from_daily(start: date, end: date) -> tuple[dict, list[Path]]:
    this_week_tasks = []
    issues = []
    next_week_tasks = []
    used_files = []

    for day in date_range(start, end):
        path = daily_path(day)
        if not path.exists():
            continue

        daily = read_json(path)
        used_files.append(path)
        this_week_tasks.extend(prefix_blocks(day, daily.get("todayTasks", [])))
        issues.extend(prefix_blocks(day, daily.get("issues", [])))
        next_week_tasks = prefix_blocks(day, daily.get("tomorrowTasks", []))

    if not used_files:
        raise SystemExit(f"No daily reports found from {start.isoformat()} to {end.isoformat()}.")

    report = {
        "month": start.strftime("%Y-%m"),
        "week": week_of_month(start),
        "thisWeekTasks": this_week_tasks,
        "issues": issues,
        "nextWeekTasks": next_week_tasks,
        "summary": [
            f"{start.isoformat()}~{end.isoformat()} 일일보고 {len(used_files)}건 취합",
            "세부 내용은 금주 진행 업무 및 이슈사항 참고",
        ],
    }
    return report, used_files


def default_output_path(start: date) -> Path:
    return ROOT / "reports" / f"weekly.{start.strftime('%Y-%m')}.{week_of_month(start)}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create weekly report JSON from saved daily reports.")
    parser.add_argument("--week", choices=["previous", "current"], default="previous")
    parser.add_argument("--start", help="Start date YYYY-MM-DD. Overrides --week.")
    parser.add_argument("--end", help="End date YYYY-MM-DD. Overrides --week.")
    parser.add_argument("--out", help="Output JSON path.")
    args = parser.parse_args()

    if args.start or args.end:
        if not args.start or not args.end:
            raise SystemExit("--start and --end must be used together.")
        start = parse_date(args.start)
        end = parse_date(args.end)
    else:
        start, end = week_range(today_kst(), args.week)

    report, used_files = build_weekly_from_daily(start, end)
    out_path = Path(args.out) if args.out else default_output_path(start)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Created: {out_path}")
    print("Used daily reports:")
    for path in used_files:
        print(f"- {path}")


if __name__ == "__main__":
    main()

