# ☁️ Cloud SRE-NEXUS
> **Autonomous Cloud Operations & Architecture Copilot**  
> 듀얼 MCP(운영 인프라 + 학습 지식) 및 서드파티 RAG 기반 자율형 멀티/하이브리드 클라우드 SRE AI 에이전트 시스템

---

## 📌 핵심 아키텍처 및 특징

1. **중앙 집중식 환경 변수 관리 (`.env` & `config.py`)**:
   - 모든 API Key, 엔드포인트, 채널 토큰, 인프라 파일 경로를 단일 `.env` 파일로 선언 및 격리.
   - 코드 내 하드코딩을 원천 배제하여 보안성 및 배포 환경(로컬, Docker, Cloud Run) 간 이식성 극대화.
2. **운영 인프라 프로바이더 (`InfraProvider` - 운영 MCP)**:
   - 복잡한 테넌트 인증 없이 `my_infra.json`을 통해 VNet, 서브넷, NSG, VM, 스토리지 스펙을 인식하는 **느슨한 결합(Loose Coupling)** 구조.
   - 실제 Azure MCP Server 또는 ARM REST API로 원클릭 전환 지원.
3. **공식 기술 문서 프로바이더 (`LearnMCPProvider` - 학습 MCP)**:
   - Microsoft Learn 공식 기술 문서 API를 실시간 검색하여 최신 공식 아키텍처 및 스펙 참조.
   - 향후 AWS/GCP MCP 도구 연동을 위한 멀티클라우드 슬롯 제공.
4. **서드파티 & 사내 규정 RAG (`ThirdPartyRAGProvider`)**:
   - MS 공식 문서에 없는 Palo Alto 차세대 방화벽(NVA), Datadog 모니터링 파이프라인, Confluent Kafka 연동 지침 및 사내 보안 컴플라이언스(Internal Policy) 교차 검증.
5. **실시간 알림 및 이벤트 전파**:
   - Slack Incoming Webhook 및 Telegram Bot API 실시간 알림 전파.
   - Google Apps Script (GAS) 기반 Azure Updates RSS / Service Health 알림 웹훅 트리거 지원.

---

## 📂 프로젝트 파일 구성

```text
cloud_sre_nexus/
├── .env.example             # 환경 변수 설정 템플릿 (상세 주석 포함)
├── .env                     # 실제 활성화 환경 변수 파일 (사용자 설정 입력)
├── config.py                # .env 및 OS 환경 변수를 로드하고 형변환/기본값을 제공하는 중앙 설정 모듈
├── app.py                   # Streamlit 풀스택 대시보드 (자연어 질의, SRE 보고서 생성, 알림 발송)
├── my_infra.json            # 느슨한 결합을 위한 엔터프라이즈 Mock 인프라 토폴로지 명세
├── gas_webhook_trigger.js   # Google Apps Script 웹훅 발송 소스 코드
├── Dockerfile               # Google Cloud Run 및 컨테이너 무과금 배포용 명세
├── requirements.txt         # 의존성 패키지 (streamlit, python-dotenv)
└── README.md                # 시스템 안내 및 실행 매뉴얼
```

---

## ⚙️ 환경 변수 (`.env`) 설정 가이드

`.env.example`을 참고하여 프로젝트 루트의 `.env` 파일을 작성합니다:

```env
# 프로젝트 기본 정보
PROJECT_NAME="Cloud SRE-NEXUS"

# Google AI Studio Gemini 무료 API 키 (https://aistudio.google.com/)
GEMINI_API_KEY="AIzaSy..."

# 운영 인프라 프로바이더 설정 ("mock" 또는 "live")
INFRA_SOURCE_TYPE="mock"
INFRA_JSON_PATH="my_infra.json"
AZURE_MCP_ENDPOINT="http://localhost:8000/sse"

# 학습 MCP 및 서드파티 RAG 설정
ENABLE_MULTICLOUD=false
ENABLE_THIRD_PARTY_RAG=true

# 알림 채널 연동 (필요 시 입력)
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
TELEGRAM_CHAT_ID="123456789"
```

---

## 🚀 빠른 시작 가이드 (Local)

```bash
# 1. 의존성 패키지 설치
pip install -r requirements.txt

# 2. .env 파일 설정 확인 (API 키 및 기본값)
# 3. Streamlit 앱 실행
streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 접속하면 `.env`에 등록된 설정값이 사이드바에 자동으로 채워진 상태로 즉시 실행됩니다.

---

## ☁️ 100% 무료 배포 (Google Cloud Run Always Free)

Google Cloud의 Always Free 티어(월 200만 건 요청 무료, 인스턴스 0개 자동 축소)를 이용해 0원으로 배포할 수 있습니다.

```bash
# Cloud Run 배포 (사전에 gcloud CLI 로그인 필요)
gcloud run deploy cloud-sre-nexus \
    --source . \
    --platform managed \
    --region asia-northeast3 \
    --allow-unauthenticated \
    --set-env-vars-file .env
```
