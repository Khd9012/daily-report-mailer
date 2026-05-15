# daily-report-mailer

CODEIDEA 일일보고/주간보고 메일을 생성하고 다우오피스 SMTP로 발송하는 간단한 Python 도구입니다.

## 기능

- 일일보고 메일 본문 생성
- 주간보고 메일 본문 생성
- 저장된 일일보고를 모아 주간보고 초안 생성
- 다우오피스 SMTP 발송
- 발송 전 미리보기
- `To`, `Cc`, `Bcc` 지원

## 준비

Python 3.11 이상을 권장합니다. 별도 패키지 설치는 필요 없습니다.

먼저 `.env.example`을 복사해서 `.env`를 만듭니다.

```powershell
copy .env.example .env
```

`.env`에 본인 다우오피스 계정과 수신자를 입력합니다.

```env
SMTP_HOST=send.daouoffice.com
SMTP_PORT=465
SMTP_SECURE=true
SMTP_USER=your.name@codeidea.dev
SMTP_PASSWORD=your-password

SENDER_NAME=홍길동
SENDER_TEAM=개발팀
SENDER_TITLE=과장
DEFAULT_FROM_NAME=

REPORT_TO=recipient1@codeidea.dev,recipient2@codeidea.dev
REPORT_CC=manager@codeidea.dev
REPORT_BCC=
```

`DEFAULT_FROM_NAME`이 비어 있으면 `SENDER_NAME`이 보낸 사람 표시 이름으로 사용됩니다.

`.env`에는 비밀번호가 들어가므로 공유하거나 GitHub에 올리지 마세요. `.gitignore`에 이미 제외되어 있습니다.

## 일일보고 작성

대화형 입력으로 오늘 일일보고 JSON 파일을 만듭니다.

```powershell
python make_report.py --type daily
```

생성 예시:

```text
reports/daily.2026-05-15.json
```

발송 전 미리보기:

```powershell
python send_report.py --type daily --report reports/daily.2026-05-15.json --dry-run
```

미리보기 예시:

```text
From: 홍길동 <your.name@codeidea.dev>
To: recipient1@codeidea.dev, recipient2@codeidea.dev
Cc: manager@codeidea.dev
Subject: [일일보고] 2026-05-15 (금) 일일보고 - 홍길동

안녕하세요, 개발팀 홍길동입니다.
2026-05-15 (금) 일일보고를 작성하여 송부드립니다.

하기 내용 확인 부탁드립니다.

[금일 진행 업무]

1. 프로젝트명
- 업무 내용
- 업무 내용
* 관련 링크/파일
  - Figma 링크 또는 관련 파일 링크

[이슈사항]

없음

[명일 예정 업무]

1. 프로젝트명
- 업무 내용
```

실제 발송:

```powershell
python send_report.py --type daily --report reports/daily.2026-05-15.json
```

## 주간보고 작성

주간보고는 두 가지 방식으로 만들 수 있습니다.

직접 입력:

```powershell
python make_report.py --type weekly
```

저장된 일일보고를 모아 자동 생성:

```powershell
python weekly_from_daily.py --week previous
```

`--week previous`는 지난 월요일부터 금요일까지의 `reports/daily.YYYY-MM-DD.json` 파일을 모읍니다.

현재 주를 모으려면:

```powershell
python weekly_from_daily.py --week current
```

특정 기간을 직접 지정하려면:

```powershell
python weekly_from_daily.py --start 2026-05-11 --end 2026-05-15
```

생성된 주간보고 미리보기:

```powershell
python send_report.py --type weekly --report reports/weekly.2026-05.둘째주.json --dry-run
```

미리보기 예시:

```text
From: 홍길동 <your.name@codeidea.dev>
To: recipient1@codeidea.dev, recipient2@codeidea.dev
Cc: manager@codeidea.dev
Subject: [주간보고] 2026-05 둘째주 주간보고 - 홍길동

안녕하세요, 개발팀 홍길동입니다.
2026-05 둘째주 주간보고를 작성하여 송부드립니다.

하기 내용 확인 부탁드립니다.

[금주 진행 업무]

1. 2026-05-11 / 프로젝트명
- 업무 내용
- 업무 내용

[이슈사항]

없음

[차주 예정 업무]

1. 2026-05-15 / 프로젝트명
- 업무 내용

[종합 의견]

- 2026-05-11~2026-05-15 일일보고 5건 취합
- 세부 내용은 금주 진행 업무 및 이슈사항 참고
```

실제 발송:

```powershell
python send_report.py --type weekly --report reports/weekly.2026-05.둘째주.json
```

## 파일 구성

```text
.
├── .env.example
├── .gitignore
├── make_report.py
├── send_report.py
├── weekly_from_daily.py
└── reports
    ├── daily.example.json
    └── weekly.example.json
```

## 보고 JSON 구조

일일보고:

```json
{
  "date": "2026-05-15",
  "day": "금",
  "todayTasks": [
    {
      "project": "프로젝트명",
      "items": ["업무 내용"],
      "links": []
    }
  ],
  "issues": [],
  "tomorrowTasks": []
}
```

주간보고:

```json
{
  "month": "2026-05",
  "week": "셋째주",
  "thisWeekTasks": [],
  "issues": [],
  "nextWeekTasks": [],
  "summary": []
}
```

보통은 JSON을 직접 만들 필요 없이 `make_report.py`를 사용하면 됩니다.

## 주의사항

- SMTP는 예약 발송 기능이 없습니다. 스크립트 실행 시점에 바로 발송됩니다.
- 수신자, 참조, 숨은참조는 `.env`의 `REPORT_TO`, `REPORT_CC`, `REPORT_BCC`에서 설정합니다.
- 여러 이메일은 콤마로 구분합니다.
- 실제 발송 전에는 항상 `--dry-run`으로 제목, 본문, 수신자를 확인하세요.
