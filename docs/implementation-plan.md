# 구현 계획

## 목표

등록 소스를 주기적으로 수집하고, 키워드·AI 판별로 선별한 뒤 카테고리별 텔레그램 형식으로 발송하며, 운영자는 읽기 전용 UI 한 페이지로 최근 실행·발송·실패를 확인한다.

## 아키텍처

| 구성 요소 | 역할 |
|-----------|------|
| EventBridge Scheduler | `jobType`별 입력(`news`/`gov`/`x`/`youtube`)으로 동일 Lambda 트리거 |
| Lambda 1개 | 스케줄 실행 + HTTP GET(대시보드·JSON API) |
| S3 | `config/`, `state/`, `output/` 전부 파일 저장 |
| Secrets Manager | 텔레그램·OpenAI·X·YouTube 키 |
| CloudWatch Logs | Lambda 표준 로그 |

## 코드 구조

- `handler.py`: HTTP 이벤트는 `clipper.http_dashboard`, 스케줄은 `clipper.runner.run_job`
- `clipper/storage.py`: `LocalFileStorage` / `S3Storage` — 동일 키 레이아웃
- `clipper/runner.py`: job별 오케스트레이션, `output/runs|items|failed/` 아티팩트 기록
- `clipper/parsers/profiles.py`: `parser_profile`별 HTML 파싱(휴리스틱 + 폴백)
- `clipper/keywords.py`: global + source_specific 병합, alias/normalize
- `clipper/dedupe.py`: external_id / 정규화 URL / 제목+시각 해시
- `clipper/telegram_client.py`: 카테고리별 메시지 포맷
- `clipper/llm.py`: OpenAI 호환 Chat Completions + JSON 파싱(X·YouTube)
- `clipper/x_fetch.py`, `clipper/youtube_fetch.py`: Twitter API v2, YouTube Data API v3

## 데이터 흐름(한 job)

1. `config/*.json` 로드, `state/*.json` 로드, `sent_items` 30일 prune
2. 소스별 HTTP fetch → 파싱 → 체크포인트 `seen_ids`와 `sent_items`로 중복 제외
3. 뉴스/공공: 키워드 필터 → 텔레그램(제목+링크)
4. X: 타임라인 → LLM 관련도 → `relevant`만 발송
5. YouTube: 채널 `국무회의` 검색 → 메타+LLM 요약 → 발송
6. `state/dashboard_snapshot.json` 갱신, `output/`에 runs·items·failed 저장

## 비기능

- React/Next.js 미사용, 단일 정적 HTML 문자열
- 뉴스 본문 전문 미전송(목록·제목 중심)
- Lambda 1개 제약 준수

## 완료 기준

README의 Definition of Done과 동일하며, 본 저장소의 `config/sources.json` 44개 소스·`config/keywords.json` 키워드가 그대로 반영되어 있다.
