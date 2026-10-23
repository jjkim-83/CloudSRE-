"""
=============================================================================
Project       : Cloud SRE-NEXUS (Autonomous Cloud Operations & Architecture Copilot)
File Path     : cloud_sre_nexus/app.py
File Name     : app.py
Description   : Streamlit 기반 SRE 에이전트 통합 UI 및 다중 프로바이더 오케스트레이션
Last Modified : 2026-10-23 15:30:00 KST (Asia/Seoul)
Version       : v1.5.0 (RAG 1단계 동적 PDF/TXT 문서 인덱싱 및 가이드 탑재)
Author/Owner  : Cloud SRE Team
=============================================================================
A unified Streamlit platform integrating:
- Operations MCP: Loose-coupling via local mock ARM topology (Web Upload/Edit) or live Azure MCP
- Learning MCP: Live Microsoft Learn search + AWS/GCP Multi-Cloud MCP Expansion
- Third-Party & Internal RAG: Built-in 4 solutions + Dynamic PDF/TXT/MD document uploader & parser
- Event Trigger & Real-time Dispatcher: Slack & Telegram alerts
All settings and credentials loaded via centralized config (.env & st.secrets).
"""

import io
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import streamlit as st
from config import settings

# PDF 파싱 라이브러리 (pypdf) 안전 임포트
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# ==============================================================================
# 1. 플러그인 구조: 모듈형 프로바이더 아키텍처
# ==============================================================================

# [프로바이더 1] 운영 인프라 프로바이더 (운영 MCP / Mock ARM JSON 겸용)
class InfraProvider:
    def __init__(self, mode: str = None, json_path: str = None, live_endpoint: str = None, in_memory_data: dict = None):
        self.mode = mode or settings.INFRA_SOURCE_TYPE
        self.json_path = json_path or settings.INFRA_JSON_PATH
        self.live_endpoint = live_endpoint or settings.AZURE_MCP_ENDPOINT
        self.infra_data = in_memory_data or {}
        if not self.infra_data:
            self.load()

    def load(self):
        if self.mode == "mock":
            if os.path.exists(self.json_path):
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        self.infra_data = json.load(f)
                except Exception as e:
                    self.infra_data = {"error": f"JSON 로드 실패: {e}"}
            else:
                self.infra_data = {"warning": f"Mock 파일({self.json_path})을 찾을 수 없습니다."}
        else:
            self.infra_data = {
                "status": "Live Azure MCP 연결 대기 중",
                "endpoint": self.live_endpoint,
                "protocol": "Model Context Protocol (SSE/STDIO)",
                "capabilities": ["resource_discovery", "metrics_query", "arm_deployment"]
            }

    def get_summary(self) -> str:
        if self.mode == "mock":
            return json.dumps(self.infra_data, ensure_ascii=False, indent=2)
        return f"[실시간 Azure MCP 연동]\n• 엔드포인트: {self.live_endpoint}\n• 감지 모드: Live Azure Tenant Infrastructure"


# [프로바이더 2] 공식 지식 프로바이더 (학습 MCP: MS Learn + 멀티클라우드 MCP)
class LearnMCPProvider:
    def __init__(self, enable_multicloud: bool = False, aws_endpoint: str = "", gcp_endpoint: str = "", search_limit: int = None, timeout: int = None):
        self.enable_multicloud = enable_multicloud
        self.aws_endpoint = aws_endpoint
        self.gcp_endpoint = gcp_endpoint
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
            ms_text += f"\n\n🌐 **[멀티클라우드 MCP 통합 연동]**"
            if self.aws_endpoint:
                ms_text += f"\n• AWS MCP Server: `{self.aws_endpoint}` (연결 활성화)"
            if self.gcp_endpoint:
                ms_text += f"\n• GCP MCP Server: `{self.gcp_endpoint}` (연결 활성화)"
        return ms_text


# [프로바이더 3] 서드파티 & 사내 가이드 RAG 프로바이더 (동적 문서 결합)
class ThirdPartyRAGProvider:
    def __init__(self, enabled: bool = None, custom_docs: list = None):
        self.enabled = settings.ENABLE_THIRD_PARTY_RAG if enabled is None else enabled
        
        # 기본 내장 서드파티 및 사내 보안 규정 지식베이스 (4종)
        self.base_kb = [
            {
                "solution": "Palo Alto VM-Series NVA",
                "category": "보안 & 네트워크 라우팅",
                "title": "Palo Alto 차세대 방화벽 Azure VNet 배포 및 UDR 라우팅 지침",
                "content": "Palo Alto NVA는 Trust(10.0.1.0/24), Untrust(10.0.0.0/24) 2개 이상의 서브넷에 각각 전용 NIC를 두어야 함. Azure NIC 레벨에서 IP Forwarding(IP 전달)을 반드시 활성화하고, 사내 UDR에서 0.0.0.0/0의 다음 홉(Next Hop)을 NVA Trust 사설 IP로 강제해야 함."
            },
            {
                "solution": "Datadog Azure Integration",
                "category": "옵저버빌리티 & 모니터링",
                "title": "Datadog을 이용한 Azure 리소스 및 로그 모니터링 아키텍처",
                "content": "Azure Platform Logs는 직접 전송하지 않고 Azure Event Hubs를 거쳐 Datadog 전달기로 스트리밍해야 대규모 트래픽 병목이 없음. VM 내부 상세 메트릭 수집을 위해선 Datadog Agent를 VM 확장을 통해 자동 배포해야 함."
            },
            {
                "solution": "Confluent Cloud on Azure",
                "category": "메시징 & 데이터 스트리밍",
                "title": "Confluent Cloud Kafka와 Azure VNet Private Link 보안 연동",
                "content": "인터넷 공용 엔드포인트 노출을 금지하는 금융/엔터프라이즈 환경에서는 Azure Private Link를 이용해 사설 IP로 카프카 클러스터에 접근해야 하며, privatelink.azure.confluent.cloud 전용 프라이빗 DNS 영역 등록이 필수적임."
            },
            {
                "solution": "사내 클라우드 보안 거버넌스 규정 (Internal Policy)",
                "category": "보안 컴플라이언스",
                "title": "사내 표준 클라우드 인프라 보안 컴플라이언스 v3.2",
                "content": "모든 가상 머신(VM)은 관리자 포트(22, 3389)를 공용 인터넷에 절대 직접 노출할 수 없으며 Azure Bastion을 통해서만 접속해야 함. 스토리지 계정은 최소 TLS 1.2 이상(향후 TLS 1.3 전환 준비) 및 프라이빗 엔드포인트 연동이 강제됨."
            }
        ]
        
        # 사용자가 업로드한 커스텀 문서 병합
        self.kb = list(self.base_kb)
        if custom_docs:
            self.kb.extend(custom_docs)

    def search(self, query: str) -> str:
        if not self.enabled:
            return "서드파티 RAG가 비활성화되어 있습니다."
        
        q = query.lower()
        matched = []
        for item in self.kb:
            searchable = (item["solution"] + " " + item["category"] + " " + item["title"] + " " + item["content"]).lower()
            keywords = [item["solution"].lower(), item["category"].lower(), "palo alto", "방화벽", "datadog", "모니터링", "confluent", "kafka", "카프카", "사내", "규정", "보안", "nva", "서드파티", "tls", "인프라", "감사", "런북"]
            if any(k in q for k in keywords) or any(term in searchable for term in q.split() if len(term) > 1):
                matched.append(f"📌 [서드파티/사내 RAG] **{item['title']}**\n- 솔루션/분류: {item['solution']} ({item['category']})\n- 내용: {item['content']}")

        if not matched and self.kb:
            for item in self.kb[:2]:
                matched.append(f"📌 [서드파티/사내 RAG (참조)] **{item['title']}**\n- 솔루션/분류: {item['solution']} ({item['category']})\n- 내용: {item['content']}")

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
# 3. LLM 오케스트레이션 헬퍼 (503 혼잡 자동 재시도 및 다중 모델 폴백)
# ==============================================================================
def call_gemini(api_key: str, system_prompt: str, user_prompt: str, preferred_model: str = None) -> str:
    active_key = str(api_key or settings.GEMINI_API_KEY).strip()
    if not active_key:
        return "⚠️ Secrets 또는 사이드바에 유효한 Gemini API Key를 입력해주세요."
    
    primary = (preferred_model or settings.GEMINI_MODEL or "gemini-3.8-flash").strip()
    candidate_models = [
        primary,
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite"
    ]
    models_to_try = []
    for m in candidate_models:
        if m and m not in models_to_try:
            models_to_try.append(m)

    payload = {
        "contents": [{"parts": [{"text": f"[시스템 프롬프트]\n{system_prompt}\n\n[사용자 입력]\n{user_prompt}"}]}],
        "generationConfig": {"temperature": settings.GEMINI_TEMPERATURE}
    }
    json_bytes = json.dumps(payload).encode("utf-8")
    last_error_details = []

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={active_key}"
        
        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    data=json_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": active_key
                    }
                )
                with urllib.request.urlopen(req, timeout=settings.GEMINI_TIMEOUT_SECONDS) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                try:
                    err_text = e.read().decode("utf-8")
                    err_json = json.loads(err_text)
                    detail_msg = err_json.get("error", {}).get("message", err_text[:200])
                except Exception:
                    detail_msg = str(e)
                
                if e.code == 503 and attempt == 0:
                    time.sleep(1.5)
                    continue
                
                last_error_details.append(f"• {model} (HTTP {e.code}): {detail_msg}")
                
                if e.code in (404, 503):
                    break
                elif e.code in (400, 403):
                    return f"❌ **API Key 인증 실패 (HTTP {e.code})**:\n{detail_msg}\n\n👉 Google AI Studio (https://aistudio.google.com/)에서 발급받은 API Key인지 확인해 주세요."
            except Exception as e:
                last_error_details.append(f"• {model}: {e}")
                break

    return f"❌ **LLM 호출 실패 (후보 모델 전체 시도 완료)**:\n" + "\n".join(last_error_details)


# ==============================================================================
# 4. Streamlit UI 렌더링
# ==============================================================================
st.set_page_config(
    page_title=f"{settings.PROJECT_NAME} - Cloud SRE Agent",
    page_icon="☁️",
    layout="wide"
)

# 세션 상태 초기화: 커스텀 인프라 JSON
if "mock_infra_data" not in st.session_state:
    try:
        with open(settings.INFRA_JSON_PATH, "r", encoding="utf-8") as f:
            st.session_state["mock_infra_data"] = json.load(f)
    except Exception:
        st.session_state["mock_infra_data"] = {
            "virtual_networks": [{"name": "vnet-prod-kr", "address_space": "10.0.0.0/16"}]
        }

# 세션 상태 초기화: 사용자 업로드 RAG 문서 목록
if "custom_rag_docs" not in st.session_state:
    st.session_state["custom_rag_docs"] = []

st.sidebar.title(f"⚙️ {settings.PROJECT_NAME}")
st.sidebar.caption("중앙 환경 변수 & Secrets 연동 상태")

# --- 0. API 설정 ---
api_key = st.sidebar.text_input(
    "Gemini API Key (무료)",
    value=settings.GEMINI_API_KEY,
    type="password",
    help=".env 또는 Streamlit Secrets의 GEMINI_API_KEY 값이 기본 로드됩니다."
)

model_options = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite"
]
default_model_idx = 0
if settings.GEMINI_MODEL in model_options:
    default_model_idx = model_options.index(settings.GEMINI_MODEL)

selected_model = st.sidebar.selectbox(
    "Gemini 모델 선택",
    options=model_options,
    index=default_model_idx,
    help="Google 공식 권장: gemini-3.8-flash (혼잡 시 하위 모델 자동 폴백)"
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 프로바이더 연결 설정")

# --- 1. 운영 인프라 프로바이더 설정 ---
infra_options = ["Mock 모드 (가상 JSON 토폴로지)", "Live Azure MCP Server (실시간 연동)"]
default_idx = 0 if settings.INFRA_SOURCE_TYPE == "mock" else 1
infra_mode = st.sidebar.radio("1. 운영 인프라 MCP 모드", infra_options, index=default_idx)

live_endpoint = settings.AZURE_MCP_ENDPOINT
if "Live" in infra_mode:
    live_endpoint = st.sidebar.text_input(
        "Azure MCP 엔드포인트 URL",
        value=settings.AZURE_MCP_ENDPOINT or "http://localhost:8000/sse",
        help="기본 포트: 8000 (Model Context Protocol SSE/STDIO 서버)"
    )
    infra_provider = InfraProvider(mode="live", live_endpoint=live_endpoint)
else:
    with st.sidebar.expander("🛠️ 인프라 JSON 업로드 / 화면 직접 편집", expanded=False):
        uploaded_infra_file = st.file_uploader("인프라 JSON 파일 업로드", type=["json"], key="infra_uploader")
        if uploaded_infra_file is not None:
            try:
                st.session_state["mock_infra_data"] = json.load(uploaded_infra_file)
                st.success("새로운 인프라 JSON이 반영되었습니다!")
            except Exception as e:
                st.error(f"JSON 파싱 실패: {e}")
        
        current_json_str = json.dumps(st.session_state["mock_infra_data"], ensure_ascii=False, indent=2)
        edited_json = st.text_area("인프라 스펙 직접 편집", value=current_json_str, height=220)
        if st.button("💾 편집 내용 인프라에 즉시 반영"):
            try:
                st.session_state["mock_infra_data"] = json.loads(edited_json)
                st.success("인프라 변경사항이 즉시 반영되었습니다!")
            except Exception as e:
                st.error(f"JSON 형식 오류: {e}")

    infra_provider = InfraProvider(mode="mock", in_memory_data=st.session_state["mock_infra_data"])

# --- 2. 학습 MCP & 멀티클라우드 확장 ---
st.markdown("---")
enable_multi = st.sidebar.checkbox(
    "2. 멀티클라우드 MCP 확장 (AWS / GCP)",
    value=settings.ENABLE_MULTICLOUD,
    help="AWS 및 GCP 공식 MCP 서버 엔드포인트를 추가로 연동합니다."
)

aws_endpoint = ""
gcp_endpoint = ""
if enable_multi:
    with st.sidebar.expander("🌐 멀티클라우드 MCP 서버 주소 설정", expanded=True):
        aws_endpoint = st.text_input("AWS MCP 엔드포인트 URL", value=settings.AWS_MCP_ENDPOINT or "http://localhost:8001/sse")
        gcp_endpoint = st.text_input("GCP MCP 엔드포인트 URL", value=settings.GCP_MCP_ENDPOINT or "http://localhost:8002/sse")

learn_mcp = LearnMCPProvider(
    enable_multicloud=enable_multi,
    aws_endpoint=aws_endpoint,
    gcp_endpoint=gcp_endpoint
)

# --- 3. 서드파티 RAG 프로바이더 설정 & 동적 문서 업로드 ---
st.markdown("---")
enable_rag = st.sidebar.checkbox(
    "3. 서드파티 & 사내 가이드 RAG 활성화",
    value=settings.ENABLE_THIRD_PARTY_RAG,
    help="Palo Alto, Datadog, Confluent 및 사내 보안 규정 지식베이스 교차 검증"
)

if enable_rag:
    with st.sidebar.expander("📄 RAG 문서 추가 (PDF / TXT / MD 업로드)", expanded=False):
        uploaded_rag_file = st.file_uploader(
            "사내 규정/서드파티 매뉴얼 업로드",
            type=["pdf", "txt", "md"],
            key="rag_doc_uploader",
            help="PDF 문서는 텍스트가 자동 추출되어 지식베이스에 즉시 추가됩니다."
        )
        if uploaded_rag_file is not None:
            doc_exists = any(d["title"] == uploaded_rag_file.name for d in st.session_state["custom_rag_docs"])
            if not doc_exists:
                content_text = ""
                file_ext = uploaded_rag_file.name.split(".")[-1].lower()
                
                # PDF 파일 파싱 (pypdf 활용)
                if file_ext == "pdf":
                    if PYPDF_AVAILABLE:
                        try:
                            pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_rag_file.read()))
                            extracted = [page.extract_text() or "" for page in pdf_reader.pages]
                            content_text = "\n".join(extracted)
                        except Exception as e:
                            st.error(f"PDF 파싱 실패: {e}")
                    else:
                        st.warning("pypdf 라이브러리가 없어 텍스트를 추출할 수 없습니다.")
                else:
                    content_text = uploaded_rag_file.read().decode("utf-8", errors="ignore")

                if content_text.strip():
                    new_doc = {
                        "solution": uploaded_rag_file.name.rsplit(".", 1)[0],
                        "category": "사용자 업로드 규정/매뉴얼",
                        "title": uploaded_rag_file.name,
                        "content": content_text[:3500]
                    }
                    st.session_state["custom_rag_docs"].append(new_doc)
                    st.success(f"'{uploaded_rag_file.name}' 문서가 RAG에 추가되었습니다!")

        if st.session_state["custom_rag_docs"]:
            st.caption(f"✨ 사용자 업로드 문서 {len(st.session_state['custom_rag_docs'])}건 활성화됨")
            if st.button("🗑️ 업로드 문서 초기화", key="reset_rag_docs"):
                st.session_state["custom_rag_docs"] = []
                st.rerun()

    rag_provider = ThirdPartyRAGProvider(enabled=enable_rag, custom_docs=st.session_state["custom_rag_docs"])
    with st.sidebar.expander(f"📚 참조 대상 서드파티 지식 ({len(rag_provider.kb)}건)", expanded=False):
        for item in rag_provider.kb:
            st.markdown(f"**• {item['solution']}** ({item['category']})")
            st.caption(f"_{item['title']}_")
else:
    rag_provider = ThirdPartyRAGProvider(enabled=False)

# --- 4. 알림 채널 설정 ---
st.sidebar.markdown("---")
st.sidebar.subheader("📢 알림 채널 연동 (.env / Secrets)")
slack_url = st.sidebar.text_input("Slack Webhook URL", value=settings.SLACK_WEBHOOK_URL, placeholder="https://hooks.slack.com/...")
tg_token = st.sidebar.text_input("Telegram Bot Token", value=settings.TELEGRAM_BOT_TOKEN, placeholder="123456789:...", type="password")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID", value=settings.TELEGRAM_CHAT_ID, placeholder="123456789")

if st.sidebar.button("🔔 알림 테스트"):
    test_text = f"☁️ [{settings.PROJECT_NAME}] 통합 알림 테스트 성공!"
    s_ok = send_slack(slack_url, test_text)
    t_ok = send_telegram(tg_token, tg_chat_id, test_text)
    if s_ok: st.sidebar.success("Slack 전송 성공")
    if t_ok: st.sidebar.success("Telegram 전송 성공")
    if not s_ok and not t_ok:
        st.sidebar.warning("알림 설정을 확인하세요 (.env, Secrets 또는 사이드바 입력창).")

# ==============================================================================
# 메인 화면 레이아웃
# ==============================================================================
st.title(f"☁️ {settings.PROJECT_NAME}")
st.caption("운영 MCP (내 인프라) + 학습 MCP (MS Learn + 멀티클라우드) + 서드파티 RAG (사내 규정/매뉴얼 동적 연동) + 실시간 런북 전파")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 인프라 & 서드파티 AI 질의응답 (User Chat)",
    "⚡ 이벤트 분석 & 알림 전파 (SRE Report)",
    "🧩 데이터 소스 모니터 (MCP & RAG 상태)",
    "📖 시스템 아키텍처 & RAG 가이드",
    "🔗 Google Apps Script 웹훅 연동"
])

# ------------------------------------------------------------------------------
# TAB 1: User Chat
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("인프라 토폴로지 + 공식 문서 + 서드파티/사내 규정 교차 질의")
    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input(
            "질문을 입력하세요:",
            placeholder="예: Palo Alto 방화벽을 우리 VNet에 연동할 때 주의점과 사내 보안 규정 위배 사항을 알려줘."
        )
    with col2:
        st.write("")
        st.write("")
        ask_btn = st.button("질문하기 🚀", use_container_width=True)

    if ask_btn and user_query:
        with st.spinner(f"운영 인프라 스펙 대조, MS Learn 및 서드파티 RAG 검색 중 ({selected_model})..."):
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
            answer = call_gemini(api_key, sys_prompt, user_query, preferred_model=selected_model)
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
        with st.spinner(f"인프라 토폴로지, 공식 스펙, 서드파티 가이드 종합 분석 중 ({selected_model})..."):
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
            report = call_gemini(api_key, sys_prompt, "종합 보고서를 작성해줘.", preferred_model=selected_model)
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
        st.caption("현재 적용 중인 인프라 토폴로지 (사이드바에서 업로드 및 실시간 편집 가능)")
        st.json(infra_provider.infra_data)
    with col_b:
        st.write(f"**2. 서드파티 & 사내 가이드 RAG 지식베이스 (총 {len(rag_provider.kb)}건)**")
        st.caption("사내 보안 규정, 서드파티 NVA/모니터링 규칙 및 사용자 업로드 PDF/TXT")
        st.json(rag_provider.kb)

# ------------------------------------------------------------------------------
# TAB 4: Architecture & RAG Guide
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("💡 Cloud SRE-NEXUS 전체 아키텍처 및 RAG 가이드")
    st.markdown("""
### 1. 왜 Microsoft 공식 문서 외에 '서드파티 RAG'가 필수적인가요?
* **MS Learn 공식 문서(학습 MCP)**는 Azure 자체의 표준 기능과 일반적인 설정법만 알려줍니다.
* 하지만 실제 기업 클라우드 환경에서는 **Palo Alto 차세대 방화벽(NVA), Datadog 모니터링, Confluent Kafka**, 그리고 **"관리자 포트 인터넷 직접 오픈 금지", "TLS 1.2 강제" 같은 사내 보안 규정**이 얽혀 있습니다.
* 마이크로소프트 공식 문서는 사내 보안 규정이나 서드파티 솔루션과의 라우팅 충돌을 알지 못하므로, **서드파티 RAG를 통해 사내 정책과 연동 매뉴얼을 함께 주입해야만 '사내 인프라 맞춤형' 진단**이 가능합니다.

---

### 2. RAG(검색 증강 생성) 동작 3단계 원리
1. **문서 수집 (Ingestion)**: 사이드바의 파일 업로더를 통해 사내 보안 규정 PDF나 매뉴얼을 등록합니다 (`pypdf` 자동 텍스트 추출).
2. **지식 결합 (Fusion)**: 사용자가 질문하거나 인프라 이벤트가 발생하면 다음 3가지 소스를 융합합니다:
   - ① **운영 MCP**: 현재 내 인프라 자원 목록 (서브넷, VM 스펙, NSG)
   - ② **학습 MCP**: Microsoft Learn 공식 기술 문서
   - ③ **서드파티 RAG**: 사내 보안 규정 + 서드파티 연동 지침
3. **교차 검증 (Reasoning)**: Gemini AI가 3가지 지식을 대조하여 **"사내 규정을 위배하지 않으면서 서드파티 솔루션을 올바르게 연결하는 런북"**을 생성합니다.
""")

# ------------------------------------------------------------------------------
# TAB 5: Google Apps Script Webhook
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("Google Apps Script ➔ 본 통합 시스템 연동 안내")
    st.markdown(f"설정된 웹훅 URL: `{settings.GAS_WEBHOOK_URL}`")
    st.info("💡 Streamlit은 웹 화면용 서버이므로, Google Apps Script에서는 슬랙/메신저로 알림을 쏘며 아래 주소를 클릭하도록 링크를 전달하는 방식을 권장합니다.")
    st.code("https://ebfsrxrsmffy9g8ynyrfvj.streamlit.app", language="text")
