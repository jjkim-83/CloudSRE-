"""
Cloud SRE-NEXUS: Autonomous Cloud Operations & Architecture Copilot
===================================================================
A unified Streamlit platform integrating:
- Operations MCP: Loose-coupling via local mock ARM topology or live Azure MCP
- Learning MCP: Live Microsoft Learn documentation search
- Third-Party & Internal RAG: Palo Alto NVA, Datadog, Confluent, and compliance policies
- Event Trigger & Real-time Dispatcher: Slack & Telegram alerts
All settings and credentials loaded via centralized config (.env).
"""

import json
import os
import urllib.request
import urllib.parse
import streamlit as st
from config import settings

# ==============================================================================
# 1. 플러그인 구조: 모듈형 프로바이더 아키텍처
# ==============================================================================

# [프로바이더 1] 운영 인프라 프로바이더 (운영 MCP / Mock ARM JSON 겸용)
class InfraProvider:
    def __init__(self, mode: str = None, json_path: str = None, live_endpoint: str = None):
        self.mode = mode or settings.INFRA_SOURCE_TYPE
        self.json_path = json_path or settings.INFRA_JSON_PATH
        self.live_endpoint = live_endpoint or settings.AZURE_MCP_ENDPOINT
        self.infra_data = {}
        self.load()

    def load(self):
        if self.mode == "mock" and os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.infra_data = json.load(f)
            except Exception as e:
                self.infra_data = {"error": f"JSON 로드 실패: {e}"}
        else:
            # 향후 실제 Azure MCP Server 또는 ARM REST API 호출로 확장
            self.infra_data = {
                "status": "Live Azure MCP 연결 대기 중",
                "endpoint": self.live_endpoint,
                "protocol": "Model Context Protocol (SSE/STDIO)"
            }

    def get_summary(self) -> str:
        if self.mode == "mock":
            return json.dumps(self.infra_data, ensure_ascii=False, indent=2)
        return f"[실시간 Azure MCP 연동] 엔드포인트: {self.live_endpoint}"


# [프로바이더 2] 공식 지식 프로바이더 (학습 MCP: MS Learn + 멀티클라우드 확장)
class LearnMCPProvider:
    def __init__(self, enable_multicloud: bool = None, search_limit: int = None, timeout: int = None):
        self.enable_multicloud = settings.ENABLE_MULTICLOUD if enable_multicloud is None else enable_multicloud
        self.search_limit = search_limit or settings.MS_LEARN_SEARCH_LIMIT
        self.timeout = timeout or settings.MS_LEARN_TIMEOUT_SECONDS

    def search(self, query: str) -> str:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://learn.microsoft.com/api/search?search={encoded_query}&locale=ko-kr&$top={self.search_limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                results = []
                for item in res.get("results", []):
                    title = item.get("title", "")
                    url_link = item.get("url", "")
                    desc = item.get("description", "")
                    results.append(f"- [{title}]({url_link}): {desc}")
                ms_text = "\n".join(results) if results else "공식 문서를 찾지 못했습니다."
        except Exception:
            ms_text = f"MS Learn 검색 참조: https://learn.microsoft.com/ko-kr/search/?terms={urllib.parse.quote(query)}"
        
        if self.enable_multicloud:
            ms_text += "\n\n*(멀티클라우드 모드 활성화됨: AWS/GCP MCP 도구 연동 대기)*"
        return ms_text


# [프로바이더 3] 서드파티 & 사내 가이드 RAG 프로바이더
class ThirdPartyRAGProvider:
    def __init__(self, enabled: bool = None):
        self.enabled = settings.ENABLE_THIRD_PARTY_RAG if enabled is None else enabled
        # 내장 서드파티 및 사내 보안 규정 지식베이스 (향후 Chroma/Qdrant 벡터DB로 교체 가능)
        self.kb = [
            {
                "solution": "Palo Alto VM-Series NVA",
                "category": "04. 보안, 거버넌스 및 ID",
                "title": "Palo Alto 차세대 방화벽 Azure VNet 배포 및 UDR 라우팅 지침",
                "content": "Palo Alto NVA는 Trust(10.0.1.0/24), Untrust(10.0.0.0/24) 2개 이상의 서브넷에 각각 전용 NIC를 두어야 함. Azure NIC 레벨에서 IP Forwarding(IP 전달)을 반드시 활성화하고, 사내 UDR에서 0.0.0.0/0의 다음 홉(Next Hop)을 NVA Trust 사설 IP로 강제해야 함."
            },
            {
                "solution": "Datadog Azure Integration",
                "category": "02. 모니터링, 옵저버빌리티 및 로깅",
                "title": "Datadog을 이용한 Azure 리소스 및 로그 모니터링 아키텍처",
                "content": "Azure Platform Logs는 직접 전송하지 않고 Azure Event Hubs를 거쳐 Datadog 전달기로 스트리밍해야 대규모 트래픽 병목이 없음. VM 내부 상세 메트릭 수집을 위해선 Datadog Agent를 VM 확장을 통해 자동 배포해야 함."
            },
            {
                "solution": "Confluent Cloud on Azure",
                "category": "08. 통합 & 메시징",
                "title": "Confluent Cloud Kafka와 Azure VNet Private Link 보안 연동",
                "content": "인터넷 공용 엔드포인트 노출을 금지하는 금융/엔터프라이즈 환경에서는 Azure Private Link를 이용해 사설 IP로 카프카 클러스터에 접근해야 하며, privatelink.azure.confluent.cloud 전용 프라이빗 DNS 영역 등록이 필수적임."
            },
            {
                "solution": "사내 클라우드 보안 거버넌스 규정 (Internal Policy)",
                "category": "04. 보안, 거버넌스 및 ID",
                "title": "사내 표준 클라우드 인프라 보안 컴플라이언스 v3.2",
                "content": "모든 가상 머신(VM)은 관리자 포트(22, 3389)를 공용 인터넷에 절대 직접 노출할 수 없으며 Azure Bastion을 통해서만 접속해야 함. 스토리지 계정은 최소 TLS 1.2 이상(향후 TLS 1.3 전환 준비) 및 프라이빗 엔드포인트 연동이 강제됨."
            }
        ]

    def search(self, query: str) -> str:
        if not self.enabled:
            return "서드파티 RAG가 비활성화되어 있습니다."
        
        q = query.lower()
        matched = []
        for item in self.kb:
            if any(term in q for term in [item["solution"].lower(), item["category"].lower(), "palo alto", "방화벽", "datadog", "모니터링", "confluent", "kafka", "카프카", "사내", "규정", "보안", "nva", "서드파티", "tls"]):
                matched.append(f"📌 [서드파티/사내 RAG] **{item['title']}**\n- 솔루션: {item['solution']}\n- 내용: {item['content']}")

        return "\n\n".join(matched) if matched else "일치하는 서드파티 RAG 문서가 없습니다."


# ==============================================================================
# 2. 통합 알림 전송 헬퍼 (Slack & Telegram)
# ==============================================================================
def send_slack(webhook_url: str, text: str) -> bool:
    target_url = webhook_url or settings.SLACK_WEBHOOK_URL
    if not target_url:
        return False
    try:
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(target_url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        st.error(f"Slack 에러: {e}")
        return False

def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    cid = chat_id or settings.TELEGRAM_CHAT_ID
    if not token or not cid:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": cid, "text": text[:4000], "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        st.error(f"Telegram 에러: {e}")
        return False


# ==============================================================================
# 3. LLM 오케스트레이션 헬퍼 (Google AI Studio Free Tier)
# ==============================================================================
def call_gemini(api_key: str, system_prompt: str, user_prompt: str) -> str:
    active_key = api_key or settings.GEMINI_API_KEY
    if not active_key:
        return "⚠️ .env 파일에 GEMINI_API_KEY를 설정하거나 사이드바에 API Key를 입력해주세요."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={active_key}"
    payload = {
        "contents": [{"parts": [{"text": f"[시스템 프롬프트]\n{system_prompt}\n\n[사용자 입력]\n{user_prompt}"}]}],
        "generationConfig": {"temperature": settings.GEMINI_TEMPERATURE}
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=settings.GEMINI_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"LLM 호출 실패: {e}"


# ==============================================================================
# 4. Streamlit UI 렌더링
# ==============================================================================
st.set_page_config(
    page_title=f"{settings.PROJECT_NAME} - Cloud SRE Agent",
    page_icon="☁️",
    layout="wide"
)

# 사이드바: 환경변수(.env) 기반 기본값 로드 및 실시간 오버라이드
st.sidebar.title(f"⚙️ {settings.PROJECT_NAME}")
st.sidebar.caption("중앙 환경 변수(.env) 연동 상태")

# 0. API 키 설정 (기본값: settings.GEMINI_API_KEY)
api_key = st.sidebar.text_input(
    "Gemini API Key (무료)",
    value=settings.GEMINI_API_KEY,
    type="password",
    help=".env 파일의 GEMINI_API_KEY 값이 기본 로드됩니다."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 프로바이더 연결 설정")

# 1. 운영 인프라 프로바이더 모드 선택
infra_options = ["Mock 모드 (my_infra.json)", "Live Azure MCP Server (실시간)"]
default_idx = 0 if settings.INFRA_SOURCE_TYPE == "mock" else 1
infra_mode = st.sidebar.radio("1. 운영 인프라 MCP 모드", infra_options, index=default_idx)

live_endpoint = settings.AZURE_MCP_ENDPOINT
if "Live" in infra_mode:
    live_endpoint = st.sidebar.text_input(
        "Azure MCP 엔드포인트 URL",
        value=settings.AZURE_MCP_ENDPOINT,
        help=".env의 AZURE_MCP_ENDPOINT 값"
    )

infra_provider = InfraProvider(
    mode="mock" if "Mock" in infra_mode else "live",
    json_path=settings.INFRA_JSON_PATH,
    live_endpoint=live_endpoint
)

# 2. 학습 MCP 프로바이더 설정
enable_multi = st.sidebar.checkbox(
    "2. 멀티클라우드 MCP 확장 (AWS/GCP)",
    value=settings.ENABLE_MULTICLOUD
)
learn_mcp = LearnMCPProvider(enable_multicloud=enable_multi)

# 3. 서드파티 RAG 프로바이더 설정
enable_rag = st.sidebar.checkbox(
    "3. 서드파티 & 사내 가이드 RAG 활성화",
    value=settings.ENABLE_THIRD_PARTY_RAG,
    help="Palo Alto, Datadog, Confluent, 사내 보안 규정 등 검색"
)
rag_provider = ThirdPartyRAGProvider(enabled=enable_rag)

st.sidebar.markdown("---")
st.sidebar.subheader("📢 알림 채널 연동 (.env 연동)")
slack_url = st.sidebar.text_input(
    "Slack Webhook URL",
    value=settings.SLACK_WEBHOOK_URL,
    placeholder="https://hooks.slack.com/..."
)
tg_token = st.sidebar.text_input(
    "Telegram Bot Token",
    value=settings.TELEGRAM_BOT_TOKEN,
    placeholder="123456789:...",
    type="password"
)
tg_chat_id = st.sidebar.text_input(
    "Telegram Chat ID",
    value=settings.TELEGRAM_CHAT_ID,
    placeholder="123456789"
)

if st.sidebar.button("🔔 알림 테스트"):
    test_text = f"☁️ [{settings.PROJECT_NAME}] 통합 알림 테스트 성공!"
    s_ok = send_slack(slack_url, test_text)
    t_ok = send_telegram(tg_token, tg_chat_id, test_text)
    if s_ok: st.sidebar.success("Slack 전송 성공")
    if t_ok: st.sidebar.success("Telegram 전송 성공")
    if not s_ok and not t_ok:
        st.sidebar.warning("알림 설정을 확인하세요 (.env 또는 입력창).")

# 메인 헤더
st.title(f"☁️ {settings.PROJECT_NAME}")
st.caption("운영 MCP (내 인프라) + 학습 MCP (MS Learn) + 서드파티 RAG (Palo Alto, Datadog 등) + 이벤트 트리거 & 알림 전파")

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 인프라 & 서드파티 AI 질의응답 (User Chat)",
    "⚡ 이벤트 분석 & 알림 전파 (SRE Report)",
    "🧩 데이터 소스 모니터 (MCP & RAG 상태)",
    "🔗 Google Apps Script 웹훅 연동"
])

# ------------------------------------------------------------------------------
# TAB 1: User Chat
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("인프라 토폴로지 + 공식 문서 + 서드파티 솔루션 교차 질의")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input(
            "질문을 입력하세요:",
            placeholder="예: Palo Alto 방화벽을 우리 VNet에 연동할 때 주의점과 보안 위배 사항을 알려줘."
        )
    with col2:
        st.write("")
        st.write("")
        ask_btn = st.button("질문하기 🚀", use_container_width=True)

    if ask_btn and user_query:
        with st.spinner("운영 인프라 스펙 대조, MS Learn 및 서드파티 RAG 검색 중..."):
            infra_context = infra_provider.get_summary()
            learn_context = learn_mcp.search(user_query)
            rag_context = rag_provider.search(user_query)

            sys_prompt = f"""
당신은 최고 수준의 멀티클라우드 & Azure 수석 엔지니어이자 {settings.PROJECT_NAME} 자율 에이전트입니다.
아래 3가지 소스에서 제공된 지식을 융합하여 사용자의 질문에 전문적으로 답하세요:

[1. 운영 인프라 현황 (운영 MCP / JSON)]
{infra_context}

[2. Microsoft Learn 공식 지식 (학습 MCP)]
{learn_context}

[3. 서드파티 솔루션 및 사내 보안 규정 (서드파티 RAG)]
{rag_context}

답변 작성 원칙:
1. 내 인프라의 실제 리소스(서브넷, VM, NSG 등)를 직접 언급하며 맞춤형으로 설명할 것.
2. 서드파티(Palo Alto, Datadog 등) 연동 요구사항과 공식 Azure 아키텍처 간의 충돌 여부를 짚어줄 것.
3. 실행 가능한 구체적인 CLI/설정 가이드를 포함할 것.
"""
            answer = call_gemini(api_key, sys_prompt, user_query)
            st.markdown(answer)
            st.markdown("---")
            
            with st.expander("🔍 이번 답변에 참조된 통합 소스 상세 확인"):
                st.markdown(f"**[학습 MCP]**\n{learn_context}")
                st.markdown(f"**[서드파티 RAG]**\n{rag_context}")

# ------------------------------------------------------------------------------
# TAB 2: Event Analysis & Notification
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("이벤트 감지 ➔ 인프라 & 서드파티 영향도 평가 ➔ 실시간 알림 전파")
    
    event_type = st.selectbox(
        "테스트할 클라우드 이벤트 선택:",
        [
            "1. [신규 기능] Azure Storage TLS 1.3 강제 적용 및 TLS 1.2 폐지 예고 (Azure Updates RSS)",
            "2. [서드파티 연동] 사내 보안 지침에 따라 Palo Alto NVA를 snet-web 서브넷 전면에 배치 (내부 컴플라이언스)",
            "3. [유지보수] Korea Central 가상 머신 호스트 OS 긴급 보안 패치 및 리부팅 (Service Health)",
            "4. [장애 경보] Korea Central 가용 영역 1번 스토리지 및 네트워크 I/O 지연 발생 (Monitor Alert)"
        ]
    )

    if st.button("⚡ 종합 영향도 분석 실행"):
        with st.spinner("인프라 토폴로지, 공식 스펙, 서드파티 가이드 종합 분석 중..."):
            infra_context = infra_provider.get_summary()
            learn_context = learn_mcp.search(event_type)
            rag_context = rag_provider.search(event_type)

            sys_prompt = f"""
당신은 엔터프라이즈 Cloud SRE 긴급 대응 에이전트 ({settings.PROJECT_NAME})입니다.
수신된 이벤트에 대해 운영 인프라와 서드파티 연동 환경에 미치는 영향도를 분석하고 보고서를 작성하세요.

[이벤트]
{event_type}

[운영 인프라]
{infra_context}

[MS 공식 레퍼런스]
{learn_context}

[서드파티 및 사내 규정]
{rag_context}

보고서 필수 양식:
# 🚨 [{settings.PROJECT_NAME} 종합 영향도 분석 보고서]
1. **이벤트 요약**: 어떤 변경/장애가 발생했는가?
2. **영향받는 리소스 및 서드파티 솔루션**: 영향 리소스 및 위험 등급
3. **위험 요인 및 장애 여파(Blast Radius)**: 사내 규정 위배 여부 및 서비스 중단 가능성
4. **단계별 대응 런북(Runbook)**: 실제 실행할 구체적인 명령어 및 조치 플랜
"""
            report = call_gemini(api_key, sys_prompt, "종합 보고서를 작성해줘.")
            st.session_state["full_report"] = report

    if "full_report" in st.session_state:
        st.markdown(st.session_state["full_report"])
        st.markdown("---")
        st.write("📢 **생성된 종합 보고서를 메신저 채널로 전송:**")
        col_s, col_t = st.columns(2)
        with col_s:
            if st.button("📢 Slack 채널로 보고서 발송"):
                ok = send_slack(slack_url, st.session_state["full_report"])
                if ok: st.success("Slack 전송 완료!")
                else: st.error("Slack 설정을 확인하세요.")
        with col_t:
            if st.button("📢 Telegram 채널로 보고서 발송"):
                ok = send_telegram(tg_token, tg_chat_id, st.session_state["full_report"])
                if ok: st.success("Telegram 전송 완료!")
                else: st.error("Telegram 설정을 확인하세요.")

# ------------------------------------------------------------------------------
# TAB 3: Data Source Status
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("연동된 데이터 소스 및 프로바이더 현황")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**1. 운영 인프라 프로바이더 (운영 MCP / JSON)**")
        st.json(infra_provider.infra_data)
    with col_b:
        st.write("**2. 서드파티 & 사내 가이드 RAG 지식베이스**")
        st.json(rag_provider.kb)

# ------------------------------------------------------------------------------
# TAB 4: Google Apps Script Webhook
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Google Apps Script ➔ 본 통합 시스템 연동 웹훅")
    st.markdown(f"설정된 웹훅 URL: `{settings.GAS_WEBHOOK_URL}`")
    st.code("""
function sendToCloudSreNexus(eventTitle, eventDetails, category) {
  var pocUrl = "https://your-cloud-run-url/webhook";
  var payload = {
    "project": "Cloud SRE-NEXUS",
    "timestamp": new Date().toISOString(),
    "event_type": category || "Azure Service Update",
    "title": eventTitle,
    "details": eventDetails,
    "source": "GAS Automated RSS Monitor"
  };
  UrlFetchApp.fetch(pocUrl, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload)
  });
}
""", language="javascript")
