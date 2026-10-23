<!--
=============================================================================
Project       : Cloud SRE-NEXUS (Autonomous Cloud Operations & Architecture Copilot)
File Path     : cloud_sre_nexus/README.md
File Name     : README.md
Description   : 프로젝트 통합 마스터 가이드 (기획 배경, 듀얼 MCP/RAG 아키텍처, 실시간 RSS, 배포 및 트러블슈팅)
Last Modified : 2026-10-23 15:55:00 KST (Asia/Seoul)
Version       : v1.6.0 (실시간 Azure RSS 피드 연동, PDF RAG 1단계, 엔터프라이즈 마스터 문서화)
Author/Owner  : Cloud SRE Team
=============================================================================
-->

# ☁️ Cloud SRE-NEXUS
> **Autonomous Cloud Operations & Architecture Copilot**  
> 듀얼 MCP(운영 인프라 + 학습 지식) 및 서드파티 RAG 기반 자율형 멀티/하이브리드 클라우드 SRE AI 에이전트 시스템

---

## 📖 1. 프로젝트 기획 및 탄생 배경

### 1) 시작점: 단순 스크립트의 한계
클라우드 운영 현장에서는 매주 쏟아지는 클라우드 릴리스(Azure Updates RSS), 보안 권고문, 서비스 헬스 장애 경보를 실시간으로 모니터링해야 합니다. 초기에는 Google Apps Script(GAS) 등을 이용해 문서를 동기화하고 크롤링하려 했으나, 다음과 같은 근본적인 한계에 부딪혔습니다:
* 마이크로소프트의 방대한 182건 이상의 기술 문서 카테고리를 단순 정적 문서로 다루면 최신 변경사항을 제때 반영할 수 없습니다.
* 단순 챗봇이나 일반 RAG는 **"지금 당장 내 Azure 테넌트에 어떤 VNet과 VM, 스토리지가 떠 있는지(운영 상태)"**를 알지 못해 원론적인 교과서 답변만 내놓습니다.

### 2) MCP vs RAG 논쟁: 무엇이 정답인가?
* **"공식 문서는 MCP로 충분한가?"**: 마이크로소프트가 공식 제공하는 Model Context Protocol(MCP)을 사용하면 Azure 리소스와 공식 문서를 표준 프로토콜로 읽어올 수 있습니다.
* **"그렇다면 RAG는 왜 필요한가?"**: MS 공식 문서는 **우리 회사가 도입한 Palo Alto 방화벽(NVA), Datadog 모니터링 파이프라인, Confluent Kafka**, 그리고 **"관리자 포트 인터넷 개방 금지", "TLS 1.2+ 강제" 같은 사내 보안 규정**을 전혀 모릅니다.
* **결론 (하이브리드 아키텍처 도출)**:
  1. **운영 MCP**: 내 인프라의 현재 자원 토폴로지를 실시간 스캔
  2. **학습 MCP**: Microsoft Learn 공식 기술 문서를 무과금 실시간 검색
  3. **서드파티 RAG**: 사내 보안 내규 및 외부 연동 솔루션 매뉴얼 교차 검증
  4. **실시간 RSS 피드 & 알림**: 공식 업데이트 수신 즉시 인프라 영향도(Blast Radius) 진단 및 Slack/Telegram 런북 전파

---

## 🏛️ 2. 전체 시스템 아키텍처 및 데이터 파이프라인

Cloud SRE-NEXUS는 다음 5대 영역이 유기적으로 결합된 자율형 SRE 에이전트입니다:

[클라우드 이벤트 / 사용자 질의]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│             Cloud SRE-NEXUS Core Engine                │
│                                                        │
│  [1. 운영 인프라 MCP]    [2. 공식 학습 MCP]  [3. 서드파티 RAG]  │
│  • Mock 웹 편집/업로드   • MS Learn 실시간   • 사내 보안 규정   │
│  • Live Azure MCP(:8000) • AWS/GCP 멀티확장  • Palo Alto/DD    │
│  (내 인프라 자원 토폴로지) (공식 표준 스펙)   (사내 내규/매뉴얼) │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (삼각 교차 추론 & Blast Radius 평가)
┌────────────────────────────────────────────────────────┐
│             Google Gemini AI Engine (v1.6.0)           │
│   • 1순위: gemini-3.8-flash (2026년 최신 표준 모델)      │
│   • 503 서버 혼잡 시: 지능형 백오프 재시도 및 하위 폴백   │
│   • 런북(Runbook): 단계별 명령어 및 장애 조치 절차 생성    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (실시간 원클릭 전파)
┌────────────────────────────────────────────────────────┐
│               Enterprise Notification Hub              │
│   • Slack Incoming Webhook (대시보드 링크 첨부)        │
│   • Telegram Bot API (Markdown 포맷 보고서 전송)       │
└────────────────────────────────────────────────────────┘

---

## 🧩 3. 컴포넌트별 상세 동작 명세

### 1) 운영 인프라 프로바이더 (InfraProvider - 운영 MCP)
* **Mock 모드 (느슨한 결합)**: 테넌트 인증 권한이 없는 PoC 단계에서도 `my_infra.json`을 통해 VNet(`vnet-prod-kr`), 서브넷(`snet-web`, `snet-db`), NSG, VM 3대, 스토리지 TLS 설정을 시뮬레이션합니다.
* **웹 실시간 편집기 탑재**: 사이드바에서 본인의 인프라 JSON 파일을 직접 업로드하거나, 화면 텍스트 에디터에서 서브넷/VM 스펙을 직접 수정하고 `💾 편집 내용 인프라에 즉시 반영`을 누르면 즉시 메모리에 반영됩니다.
* **Live Azure MCP 전환**: 실제 Azure 환경 전환 시 마이크로소프트 공식 Azure MCP Server 표준 엔드포인트(`http://localhost:8000/sse`)와 SSE/STDIO로 원클릭 실시간 연동됩니다.

### 2) 공식 지식 프로바이더 (LearnMCPProvider - 학습 MCP)
* 마이크로소프트 공식 검색 엔드포인트(`learn.microsoft.com/api/search`)를 무과금 실시간 호출하여 최신 공식 문서를 가져옵니다.
* 향후 확장을 위해 **AWS MCP(:8001)** 및 **GCP MCP(:8002)** 엔드포인트 입력 슬롯이 기본 내장되어 있습니다.

### 3) 서드파티 & 사내 규정 RAG (ThirdPartyRAGProvider - 1단계 완성)
* **내장 4대 지식베이스**:
  * Palo Alto VM-Series NVA: VNet Trust/Untrust 서브넷 NIC 분리 및 UDR 0.0.0.0/0 강제 라우팅 지침
  * Datadog Azure Integration: Platform Logs의 Event Hubs 스트리밍 및 Agent 확장 배포 규칙
  * Confluent Cloud on Azure: Private Link 보안 연동 및 전용 프라이빗 DNS 구성
  * 사내 표준 클라우드 보안 규정 v3.2: 관리자 포트(22, 3389) 인터넷 개방 절대 금지(Bastion 강제), 스토리지 TLS 1.2+ 강제
* **동적 파일 인덱싱 (PDF, TXT, MD)**:
  * 사이드바 파일 업로더에 사내 규정 PDF나 솔루션 매뉴얼을 드래그 앤 드롭하면 `pypdf`가 텍스트를 즉시 추출하여 RAG 지식베이스에 동적으로 병합합니다.

### 4) 실시간 이벤트 감지 & SRE 런북 생성 (Tab 2)
* **실시간 Azure Updates RSS 연동**:
  * Azure 공식 RSS 피드(`https://azurecomcdn.azureedge.net/en-us/updates/feed/`)를 30분 단위 캐싱(`@st.cache_data`)으로 가져와 최신 공지 목록을 화면에 동적으로 뿌려줍니다.
* **영향도 분석 보고서 필수 항목**:
  1. **이벤트 요약**: 어떤 기술 변경/장애/업데이트가 발표되었는가?
  2. **영향받는 리소스 및 위험 등급**: 우리 인프라의 어떤 서브넷/VM/스토리지가 영향받는가?
  3. **위험 요인 및 장애 여파(Blast Radius)**: 사내 규정 위배 여부 및 서비스 중단 가능성
  4. **단계별 대응 런북(Runbook)**: 실제 터미널/포털에서 실행할 구체적인 CLI 명령어 및 조치 플랜

---

## 📂 4. 최종 프로젝트 파일 구조

cloud_sre_nexus/
├── .streamlit/
│   └── config.toml          # Streamlit 서버 최적화 (inotify watch limit 오류 영구 방지)
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub push 시 Google Cloud Run Always Free 자동 배포 CI/CD
├── .env.example             # 전체 환경 변수 설정 명세 및 상세 주석 템플릿
├── .env                     # 실제 활성화 환경 변수 파일 (로컬 실행용)
├── .gitignore               # .env 및 비밀 키의 GitHub 유출 방지
├── config.py                # .env, st.secrets, os.environ을 통합 로드하는 중앙 설정 싱글톤
├── app.py                   # 모든 MCP, RAG, Chat, 런북 분석, 실시간 RSS가 통합된 메인 앱
├── my_infra.json            # 운영 MCP용 엔터프라이즈 가상 인프라 토폴로지 명세
├── gas_webhook_trigger.js   # Google Apps Script(스프레드시트/RSS) 웹훅 트리거 스크립트
├── Dockerfile               # Cloud Run 및 컨테이너 0원 배포용 빌드 명세
├── requirements.txt         # 필수 라이브러리 (streamlit, python-dotenv, pypdf)
└── README.md                # 시스템 운영 매뉴얼 및 아키텍처 문서

---

## ⚙️ 5. 환경 변수 및 Secrets 설정 가이드

### 1) Streamlit Community Cloud 배포 시 (Secrets 설정)
배포된 화면 우측 하단 Manage app > Settings > Secrets에 아래 내용을 저장합니다:

    GEMINI_API_KEY = "AIzaSy..."
    GEMINI_MODEL = "gemini-3.8-flash"

    PROJECT_NAME = "Cloud SRE-NEXUS"
    INFRA_SOURCE_TYPE = "mock"
    ENABLE_THIRD_PARTY_RAG = true

    SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."
    TELEGRAM_BOT_TOKEN = "123456789:ABCdef..."
    TELEGRAM_CHAT_ID = "123456789"

### 2) 로컬 개발 환경 (.env 파일 설정)
템플릿 복사 후 키를 입력합니다:
    cp .env.example .env

---

## 🚀 6. 실행 및 배포 옵션 (100% 무료)

### 옵션 1. Streamlit Community Cloud (가장 추천 / 신용카드 불필요)
1. GitHub 저장소(`CloudSRE-`)에 최신 소스를 푸시합니다.
2. share.streamlit.io에서 해당 저장소와 `app.py`를 지정하면 1분 만에 배포됩니다.
3. `.streamlit/config.toml`이 내장되어 있어 `inotify watch limit` 에러 없이 안정적으로 0원 운영됩니다.

### 옵션 2. Google Cloud Run (Always Free 200만 건 무료)
저장소의 `.github/workflows/deploy.yml`을 통해 푸시 시 자동 배포됩니다. GitHub 저장소의 Settings > Secrets에 아래 3가지를 등록합니다:
* `GCP_PROJECT_ID`: 내 GCP 프로젝트 ID
* `GCP_SA_KEY`: 서비스 계정 키 JSON 전체
* `GEMINI_API_KEY`: Google AI Studio 키

---

## 🛠️ 7. 실전 트러블슈팅 및 운영 FAQ (Battle-Tested 로그)

#### Q1. LLM 호출 실패: HTTP Error 404: Not Found
* **원인**: 구글이 이전 세대 모델(`gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash`)을 신규 사용자 대상 지원 중단(Deprecated) 처리함.
* **해결**: 2026년 최신 표준 모델인 **`gemini-3.8-flash`**로 마이그레이션 완료.

#### Q2. HTTP 503: This model is currently experiencing high demand
* **원인**: 구글 무료 티어의 3.8-flash 서버에 전 세계 트래픽이 일시적으로 폭주할 때 발생하는 일시 과부하(Spike) 현상.
* **해결**: `app.py` 내부에 **1.5초 대기 후 1회 즉시 재시도(Exponential Backoff)** 및 혼잡 시 `gemini-3.7-flash` ➔ `gemini-3.5-flash-lite` 순차 우회 로직을 적용하여 무중단 답변 보장.

#### Q3. OSError: [Errno 28] inotify watch limit reached
* **원인**: Streamlit Cloud의 공유 리눅스 호스트에서 커널 파일 감시 핸들러 개수가 꽉 차서 발생.
* **해결**: `.streamlit/config.toml`에 `fileWatcherType = "none"`을 선언하여 불필요한 감시자를 끄고 성능 최적화 달성.

#### Q4. PERMISSION_DENIED: Cloud Run Admin API has not been used
* **원인**: 신규 GCP 프로젝트에서 Cloud Run 및 Cloud Build API가 비활성화된 상태.
* **해결**: Cloud Shell에서 `gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com` 실행.

#### Q5. Google Apps Script(GAS)에서 Streamlit으로 웹훅 전송 시 404/405 발생
* **원인**: Streamlit은 웹소켓 기반 대시보드이므로 외부의 임의 `POST` REST API 웹훅을 직접 수신하는 엔드포인트가 없음.
* **해결**: GAS에서는 RSS 감지 시 Slack으로 알림을 보내고 내 스트림릿 앱 링크(https://ebfsrxrsmffy9g8ynyrfvj.streamlit.app)를 클릭하게 유도하거나, Streamlit 인앱에서 `fetch_azure_rss_updates()`를 통해 직접 RSS를 긁어오도록 아키텍처 정립.
