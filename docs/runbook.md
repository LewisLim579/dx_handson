# 운영 런북

## 사전 준비

1. S3 버킷(SAM으로 생성)과 Lambda 실행 역할에 `s3:GetObject`/`PutObject` 권한.
2. Secrets Manager 시크릿에 최소 다음 키 포함:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `OPENAI_API_KEY`
   - `TWITTER_BEARER_TOKEN`
   - `YOUTUBE_API_KEY`
3. Lambda 환경 변수: `S3_BUCKET`, `APP_SECRET_ARN` (배포 템플릿 참고).

## 대시보드 URL

`template.yaml`에는 함수 URL 리소스를 생략했을 수 있다. 필요 시:

- 콘솔에서 해당 Lambda → 구성 → 함수 URL 생성(또는 API Gateway HTTP API로 GET `/` 프록시).

엔드포인트:

- `GET /` — HTML 대시보드
- `GET /api/dashboard` — `state/dashboard_snapshot.json` 동일 내용
- `GET /api/items?decision=sent|skipped|failed&category=news|gov|x|youtube`

## 스케줄 조정

EventBridge 규칙(또는 Scheduler)의 `Input` JSON이 `{"jobType":"news"}` 형태인지 확인. 빈도는 요구사항(뉴스 일 3~6회, 공공 일 1회, X 10분 목표 등)에 맞게 조정.

## 장애 대응

| 증상 | 확인 |
|------|------|
| 텔레그램 미발송 | 시크릿·`TELEGRAM_CHAT_ID`·봇 차단 여부 |
| X 항상 스킵/오류 | `TWITTER_BEARER_TOKEN`, API 한도, 사용자명 변경 여부 |
| 유튜브 요약 실패 | `YOUTUBE_API_KEY` 쿼ota, 채널 핸들 변경 |
| HTML 소스 0건 | 사이트 구조 변경 → 파서 휴리스틱 조정 필요 |
| 대시보드 빈 화면 | S3에 `state/dashboard_snapshot.json` 존재 여부, 첫 job 실행 여부 |

## 로그

CloudWatch Logs에서 Lambda 로그 그룹 확인. 구조화 로그는 `output/runs/...` JSON으로도 남는다.

## 로컬 재현

프로젝트 루트 `.env` 에 키를 두면 자동 로드된다. 없으면 PowerShell에서 `$env:...` 로 설정.

```powershell
python cli.py run --job gov
```

`local_data/` 구조는 S3와 동일해야 한다.
