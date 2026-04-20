# 구현 계획

## 우리가 만들려는 것

등록해 둔 소스를 **주기적으로 모으고**, 키워드와 AI로 **걸러낸 뒤**, 종류별로 정해진 형식으로 **텔레그램에 보냅니다**. 운영자는 **읽기 전용 화면 한 장**으로 최근 실행·발송·실패를 볼 수 있습니다.

## 전체 구성

| 구성 요소 | 하는 일 |
|-----------|---------|
| EventBridge Scheduler | `jobType`(`news` / `gov` / `x` / `youtube`)마다 **같은 Lambda**를 호출합니다. |
| Lambda 1개 | 스케줄 작업 + HTTP GET(대시보드·JSON API) |
| S3 | `config/`, `state/`, `output/`를 **파일(JSON)**로 저장합니다. |
| Secrets Manager | 텔레그램·OpenAI·X·YouTube 키 |
| CloudWatch Logs | Lambda 기본 로그 |

## 코드가 나뉘는 방식

- `handler.py` — HTTP 요청은 `clipper.http_dashboard`, 스케줄은 `clipper.runner.run_job`으로 넘깁니다.  
- `clipper/storage.py` — 로컬(`LocalFileStorage`)과 S3(`S3Storage`)가 **같은 키(폴더) 구조**를 씁니다.  
- `clipper/runner.py` — job마다 순서를 맞춰 실행하고, `output/runs`, `items`, `failed` 등에 기록합니다.  
- `clipper/parsers/profiles.py` — `parser_profile`별로 HTML을 파싱합니다(규칙 + 폴백).  
- `clipper/keywords.py` — 전역·소스별 키워드를 합치고, 별칭·정규화를 합니다.  
- `clipper/dedupe.py` — `external_id`, 정규화한 URL, 제목+시간 해시 등으로 중복을 줄입니다.  
- `clipper/telegram_client.py` — 카테고리별로 메시지 모양을 맞춥니다.  
- `clipper/llm.py` — OpenAI 호환 Chat Completions와 JSON 파싱(X·YouTube).  
- `clipper/x_fetch.py`, `clipper/youtube_fetch.py` — Twitter API v2, YouTube Data API v3.

## 한 번의 job이 돌아갈 때(흐름)

1. `config/*.json`과 `state/*.json`을 읽고, `sent_items`는 30일 지난 항목을 정리합니다.  
2. 소스마다 HTTP로 가져와 파싱한 다음, 체크포인트의 `seen_ids`와 `sent_items`로 **이미 보낸 것은 빼고** 처리합니다.  
3. 뉴스·공공: 키워드로 거른 뒤 텔레그램에 **제목+링크**를 보냅니다.  
4. X: 타임라인을 가져온 뒤 LLM으로 관련도를 보고, **관련 있다고 나온 것만** 보냅니다.  
5. YouTube: 채널에서 `국무회의` 검색 → 메타 정보 + LLM 요약 → 발송.  
6. `state/dashboard_snapshot.json`을 갱신하고, `output/`에 실행·항목·실패 로그를 남깁니다.

## 기술 선택(범위 밖으로 둔 것)

- React·Next.js는 쓰지 않고, **문자열로 만든 HTML 한 페이지**입니다.  
- 뉴스 **본문 전체**는 텔레그램으로 보내지 않고, **목록·제목 중심**입니다.  
- Lambda는 **함수 하나**로 맞춥니다.

## “다 됐다”고 보는 기준

README에 적어 둔 완료 기준과 같습니다. 이 저장소의 `config/sources.json` **44개 소스**와 `config/keywords.json` 키워드가 **줄이지 않고** 반영되어 있어야 합니다.
