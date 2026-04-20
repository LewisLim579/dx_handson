# 결정 사항 (ADR 요약)

## 저장소

- **S3 단일 버킷**, 객체 키로 `config/`, `state/`, `output/` 구분. 프리픽스는 `S3_PREFIX`로 확장 가능.
- 첫 배포 시 버킷에 설정이 없으면 Lambda 패키지 내 `config/`를 그대로 복사(bootstrap).

## 비밀 관리

- 민감 값은 **Secrets Manager JSON** 한 덩어리(`APP_SECRET_ARN`)로 수신. 로컬은 환경 변수 우선.

## LLM

- **Azure OpenAI 우선**: `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`가 있으면 `openai.AzureOpenAI`로 배포(chat) 호출. JSON 모드가 거부되면 동일 클라이언트로 재시도(옵션 순차 완화).
- Azure가 없으면 **OpenAI 호환 HTTP**(`OPENAI_API_KEY`, 선택 `OPENAI_API_BASE`)로 기존 경로 유지.

## HTML 파싱

- 사이트별 전용 스크레이퍼 대신 **`parser_profile` + 공통 휴리스틱**으로 단순화. 링크·제목 추출 실패 시 `generic_list_fallback`.
- JS 렌더 전용 페이지는 HTTP만으로 빈 결과가 나올 수 있으며, 그 경우 `source_health`에 오류가 쌓인다(별도 브라우저 자동화는 범위 밖).

## X(트위터)

- **Twitter API v2** Bearer 토큰 기준(`TWITTER_BEARER_TOKEN`). 무료/제한 정책에 따라 실제 수집 빈도는 달라질 수 있다.

## YouTube

- **Data API v3**로 `@ktv_kr` 채널 ID 해석 후 `q=국무회의` 검색. 자막 API는 OAuth가 필요한 경우가 많아 **1차는 제목·설명만** LLM에 넣고, `transcript_available`은 기본 false.
- “국무회의 종료 후”는 **신규 업로드 검색 + 중복 제외**로 근사.

## 스케줄

- `template.yaml` 예시: 뉴스 `rate(4 hours)`, 공공 일 1회 `cron`, X `rate(10 minutes)`, YouTube `rate(30 minutes)`. 운영에서 EventBridge만 조정하면 된다.

## 텔레그램

- `parse_mode: HTML`, 간단 이스케이프만 적용. 메시지 길이 상한은 API 제한에 맞춰 잘라 전송.

## 읽기 전용 UI

- Lambda Function URL 또는 API Gateway GET만 연결. **인증 없음**은 템플릿 편의상이며, 운영 시에는 IAM/OAuth/WAF 등으로 보호해야 한다.
