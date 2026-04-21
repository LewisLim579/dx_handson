# 운영 런북

운영·장애 대응 때 빠르게 보려고 정리한 문서입니다.

## 배포 전에 확인할 것

1. S3 버킷(SAM이 만들어 줌)과 Lambda 실행 역할에 `s3:GetObject`, `s3:PutObject` 권한이 있습니다.  
2. Secrets Manager 시크릿에 **최소** 다음 키가 들어 있습니다(실제로 쓰는 LLM에 맞게).  
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`  
   - 유튜브에 Gemini: `GEMINI_API_KEY`, (선택) `GEMINI_MODEL`, `LLM_PROVIDER`  
   - X·백업용: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` 또는 `OPENAI_API_KEY`  
   - `TWITTER_BEARER_TOKEN`  
   - `YOUTUBE_API_KEY`  
3. Lambda 환경 변수: `S3_BUCKET`, `APP_SECRET_ARN`(배포 템플릿과 동일하게).

## 대시보드 URL

`template.yaml`에 **함수 URL(`FunctionUrlConfig`)**이 들어 있으므로, `sam deploy` 후 **Lambda 콘솔 → 구성 → 함수 URL**에서 HTTPS 주소를 확인하면 됩니다. (CloudFormation **Outputs**에는 URL 문자열이 없고 `BucketName`·`FunctionName`만 있습니다.)

수동으로 붙이거나 바꿀 때는:

- Lambda 콘솔 → **구성 → 함수 URL**에서 생성·수정하거나, API Gateway HTTP API로 GET `/`만 프록시해도 됩니다.

엔드포인트 의미:

- `GET /` — HTML 대시보드  
- `GET /api/dashboard` — `state/dashboard_snapshot.json`과 같은 내용(JSON)  
- `GET /api/items?decision=sent|skipped|failed&category=news|gov|x|youtube` — 항목 필터

## 스케줄 바꾸기

EventBridge 규칙(또는 Scheduler)의 **입력 JSON**이 `{"jobType":"news"}` 형태인지 먼저 확인합니다. 그다음 빈도를 요구사항에 맞게 조정합니다(예: 뉴스 하루 3~6회, 공공 하루 1회, X는 10분 단위 목표 등).

## 문제가 생겼을 때

| 증상 | 먼저 볼 것 |
|------|------------|
| 텔레그램에 안 옴 | 시크릿 값, `TELEGRAM_CHAT_ID`, 봇이 차단됐는지 |
| X만 계속 스킵·오류 | `TWITTER_BEARER_TOKEN`, API 한도, 사용자명(@)이 바뀌지 않았는지 |
| 유튜브 요약만 실패 | `YOUTUBE_API_KEY` 할당량, 채널 핸들 변경 여부 |
| HTML 소스에서 0건만 나옴 | 사이트 레이아웃이 바뀌었을 수 있음 → 파서 규칙 조정 필요 |
| 대시보드가 비어 있음 | S3에 `state/dashboard_snapshot.json`이 있는지, job이 한 번이라도 돌았는지 |

## 로그

- **CloudWatch Logs**: Lambda 로그 그룹.  
- **S3**: `output/runs/...` 아래 JSON에도 실행 요약이 남습니다.

## 로컬에서 같은 상황 재현하기

프로젝트 루트에 `.env`를 두면 앱이 자동으로 읽습니다. 없으면 PowerShell에서 `$env:변수명 = "값"`으로 넣을 수 있습니다.

```powershell
python cli.py run --job gov
```

`local_data/` 안의 폴더 구조는 **S3와 같게** 두는 것이 디버깅에 편합니다.
