# CODEIDEA report mail sender

Daily/weekly report mail generator and SMTP sender.

## Files

- `send_report.py`: Generates and sends report email.
- `.env.example`: SMTP credential template.
- `reports/daily.example.json`: Daily report input sample.
- `reports/weekly.example.json`: Weekly report input sample.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in SMTP account values.
3. Fill in sender and recipient values.
4. Edit report JSON files.

## SMTP

DaouOffice SMTP example:

```env
SMTP_HOST=send.daouoffice.com
SMTP_PORT=465
SMTP_SECURE=true
SMTP_USER=your.name@codeidea.dev
SMTP_PASSWORD=your-password
SENDER_NAME=홍길동
SENDER_TEAM=OO팀
SENDER_TITLE=직급
DEFAULT_FROM_NAME=
REPORT_TO=person1@codeidea.dev,person2@codeidea.dev
REPORT_CC=manager@codeidea.dev
REPORT_BCC=
```

If `DEFAULT_FROM_NAME` is empty, `SENDER_NAME` is used as the email display name.

## Dry run

Preview the email without sending:

```powershell
python send_report.py --type daily --report reports/daily.example.json --dry-run
```

```powershell
python send_report.py --type weekly --report reports/weekly.example.json --dry-run
```

## Create Report JSON

You do not have to write `date`, `day`, or task JSON by hand.

Create a daily report interactively:

```powershell
python make_report.py --type daily
```

Create a weekly report interactively:

```powershell
python make_report.py --type weekly
```

This creates files like:

```text
reports/daily.2026-05-15.json
reports/weekly.2026-05.셋째주.json
```

Then preview/send with that file:

```powershell
python send_report.py --type daily --report reports/daily.2026-05-15.json --dry-run
```

## Create Weekly From Daily Reports

Daily reports are saved as:

```text
reports/daily.YYYY-MM-DD.json
```

Create a weekly report draft from the previous Monday-Friday daily reports:

```powershell
python weekly_from_daily.py --week previous
```

Create from the current week:

```powershell
python weekly_from_daily.py --week current
```

Create from a custom range:

```powershell
python weekly_from_daily.py --start 2026-05-11 --end 2026-05-15
```

Then preview/send:

```powershell
python send_report.py --type weekly --report reports/weekly.2026-05.둘째주.json --dry-run
```

## Send

```powershell
python send_report.py --type daily --report reports/daily.example.json
```

```powershell
python send_report.py --type weekly --report reports/weekly.example.json
```

## Recipients

SMTP supports all common recipient headers:

- `to`: main recipients
- `cc`: copied recipients
- `bcc`: hidden copied recipients

`send_report.py` sends to every address included in `to`, `cc`, and `bcc`.

Recommended sharing rule:

- Put SMTP ID/password only in `.env`.
- Put sender name/team and real recipients in `.env`.
- Do not share `.env`.
