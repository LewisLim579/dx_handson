# 결정 사항 요약 (ADR 스타일)

코드를 짜기 전에 정해 둔 선택입니다. “왜 이렇게 했는지”를 짧게 모아 두었습니다.

## 데이터 저장

- **S3 버킷 하나**에 넣고, 객체 **키 이름**으로 `config/`, `state/`, `output/`를 구분합니다. 필요하면 `S3_PREFIX`로 앞에 공통 접두사를 붙일 수 있습니다.  
- **첫 배포 직후** 버킷에 설정 파일이 없으면, Lambda에 포함된 `config/`를 그대로 복사합니다(부트스트랩).

## 비밀 번호·토큰

- AWS에서는 **Secrets Manager**에 JSON 한 번에 넣고, Lambda 환경 변수 `APP_SECRET_ARN`으로 가져옵니다.  
- 로컬에서는 **환경 변수**가 우선이고, 보통 `.env`와 함께 씁니다.

## LLM (Azure vs OpenAI 호환)

- **Azure OpenAI를 우선**합니다. `AZURE_OPENAI_ENDPOINT`와 `AZURE_OPENAI_API_KEY`가 있으면 `openai.AzureOpenAI` 클라이언트로 채팅 API를 호출합니다.  
- JSON 응답 형식이 거부되면, 같은 클라이언트로 옵션을 조금 바꿔 **다시 시도**합니다.  
- Azure를 쓰지 않을 때만 **OpenAI 호환 HTTP**(`OPENAI_API_KEY`, 선택 `OPENAI_API_BASE`) 경로를 씁니다.

## HTML 파싱

- 사이트마다 전용 스크레이퍼를 두지 않고, **`parser_profile` + 공통 규칙**으로 맞춥니다. 링크·제목을 못 찾으면 `generic_list_fallback`으로 넘깁니다.  
- **자바스크립트로만 그려지는 페이지**는 HTTP로 긁으면 빈 결과가 나올 수 있습니다. 그때는 `source_health`에 오류가 쌓이며, **브라우저 자동화(셀레니움 등)는 이번 범위에 넣지 않았습니다.**

## X(구 트위터)

- **Twitter API v2** Bearer 토큰(`TWITTER_BEARER_TOKEN`)을 기준으로 합니다. 무료·유료 등 **플랜에 따라** 실제로 가져올 수 있는 빈도는 달라질 수 있습니다.

## YouTube

- **Data API v3**로 `@ktv_kr` 채널 ID를 찾은 뒤, `q=국무회의`로 검색합니다.  
- 자막 API는 OAuth가 필요한 경우가 많아, **1차 버전에서는 제목·설명만** LLM에 넣고, `transcript_available`은 기본값을 false로 둡니다.  
- “국무회의가 끝난 뒤 올라온 영상”에 가깝게 하려고, **새로 올라온 것 위주로 검색하고 이미 보낸 것은 빼는 방식**으로 근사합니다.

## 스케줄

- `template.yaml` 예시: 뉴스 `rate(4 hours)`, 공공 하루 한 번 `cron`, X `rate(10 minutes)`, YouTube `rate(30 minutes)` 등.  
- 운영 중에는 **EventBridge(또는 Scheduler) 규칙만** 바꿔 주기를 조정하면 됩니다.

## 텔레그램

- `parse_mode: HTML`이며, 필요한 만큼만 이스케이프합니다. 메시지가 너무 길면 **API 한도에 맞춰 잘라서** 보냅니다.

## 웹 UI(대시보드)

- Lambda 함수 URL 또는 API Gateway에서 **GET만** 연결합니다.  
- 템플릿에 **인증 없음(`AuthType: NONE`)**이 들어 있는 것은 배포를 단순하게 하려는 것이고, **실제 운영**에서는 IAM·OAuth·WAF 등으로 **접근을 제한하는 것**을 전제로 합니다.
