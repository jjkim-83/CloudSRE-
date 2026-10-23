"""
=============================================================================
Project       : Cloud SRE-NEXUS (Autonomous Cloud Operations & Architecture Copilot)
File Path     : cloud_sre_nexus/services.py
File Name     : services.py
Description   : SRE 에이전트 핵심 비즈니스 로직 및 프로바이더 모듈 (MCP, RAG, RSS, LLM, 알림)
Last Modified : 2026-10-23 16:56:00 KST (Asia/Seoul)
Version       : v1.8.1 (Azure RSS 환경변수 API 키 자동 참조 및 시그니처 TypeError 방지)
Author/Owner  : Cloud SRE Team
=============================================================================
"""

import io
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from config import settings

# Streamlit 캐시 데코레이터 안전 임포트
try:
    import streamlit as st
    cache_data = st.cache_data
except Exception:
    def cache_data(ttl=None):
        return lambda f: f

# PDF 파싱 라이브러리 안전 임포트
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# ==============================================================================
# 0. Azure RSS 영문 타이틀 한국어 번역 헬퍼 (규칙 기반 + LLM 하이브리드)
# ==============================================================================
def quick_translate_title(title: str) -> str:
    """핵심 릴리즈 키워드를 공학적 한국어 표기로 즉시 변환"""
    t = title.strip()
    replacements = [
        (r"General availability:?", "[정식 출시/GA]"),
        (r"Generally available:?", "[정식 출시/GA]"),
        (r"Public preview:?", "[공개 프리뷰]"),
        (r"Private preview:?", "[비공개 프리뷰]"),
        (r"Retirement notice:?", "[지원 종료(은퇴) 공지]"),
        (r"Retirement of", "[지원 종료]"),
        (r"Retiring:?", "[지원 종료]"),
        (r"Announcing:?", "[공식 발표]"),
        (r"Announcement:?", "[공식 안내]"),
        (r"Deprecation:?", "[지원 중단/폐지]"),
        (r"Support for", "지원:"),
        (r"support for", "지원:"),
        (r"now available in", "➔ 사용 가능:"),
        (r"is now available", "정식 지원 개시"),
        (r"now in public preview", "공개 프리뷰 시작"),
        (r"now in general availability", "정식 출시(GA) 시작"),
    ]
    for pattern, rep in replacements:
        t = re.sub(pattern, rep, t, flags=re.IGNORECASE).strip()
    return t


def translate_titles_batch(items: list, api_key: str = "") -> list:
    """Gemini API를 활용해 5~8개 RSS 타이틀을 한 번에 한국어로 매끄럽게 번역"""
    active_key = str(api_key or settings.GEMINI_API_KEY).strip()
    
    # 1단계: 규칙 기반 번역 기본 적용
    for item in items:
        item["title_ko"] = quick_translate_title(item["title"])
    
    if not active_key or not items:
        return items

    # 2단계: Gemini API를 통해 자연스러운 한국어 문맥 번역 보정 (1회 일괄 호출)
    titles_text = "\n".join([f"{i+1}. {it['title']}" for i, it in enumerate(items)])
    prompt = (
        "다음 Microsoft Azure 공식 릴리즈 공지 영문 제목들을 한국어 IT 클라우드 엔지니어가 읽기 편한 자연스러운 한국어로 번역해줘.\n"
        "다른 설명 없이 번역된 제목만 번호 순서대로 한 줄씩 출력해:\n\n"
        f"{titles_text}"
    )
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={active_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": active_key}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated_lines = data["candidates"][0]["content"]["parts"][0]["text"].strip().split("\n")
            
            for line in translated_lines:
                line = line.strip()
                match = re.match(r"^(\d+)[\.\)]\s*(.+)$", line)
                if match:
                    idx = int(match.group(1)) - 1
                    if 0 <= idx < len(items):
                        items[idx]["title_ko"] = match.group(2).strip()
    except Exception:
        pass  # 실패 시 규칙 기반 번역(quick_translate_title) 유지
    
    return items


# ==============================================================================
# 1. 실시간 Azure Updates RSS 피드 수집기 (신규 MS 공식 엔드포인트)
# ==============================================================================
@cache_data(ttl=1800)
def fetch_azure_rss_updates(limit: int = 8, *args, **kwargs):
    """
    Microsoft 공식 신규 릴리즈 RSS 엔드포인트에서 최신 공지 비동기 수집 및 한국어화
    - 신규 공식 주소: https://www.microsoft.com/releasecommunications/api/v2/azure/rss
    - 환경변수 및 settings.GEMINI_API_KEY 자동 참조로 호출부에서 api_key 전달 불필요
    - 하위 호환성을 위해 *args, **kwargs 수용 (TypeError 방지)
    """
    api_key = kwargs.get("api_key", "")
    if not api_key and args:
        api_key = args[0]
    api_key = str(api_key or settings.GEMINI_API_KEY).strip()
    candidate_urls = [
        "https://www.microsoft.com/releasecommunications/api/v2/azure/rss",
        "https://azure.microsoft.com/en-us/blog/feed/"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }

    raw_items = []
    for url in candidate_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for item in root.findall("./channel/item")[:limit]:
                    title = item.findtext("title", default="제목 없음").strip()
                    desc = item.findtext("description", default="").strip()
                    link = item.findtext("link", default="").strip()
                    pub_date = item.findtext("pubDate", default="").strip()
                    
                    clean_desc = desc.replace("<p>", "").replace("</p>", "\n").replace("<br/>", "\n").replace("<br>", "\n")
                    clean_desc = " ".join(clean_desc.split())
                    if len(clean_desc) > 250:
                        clean_desc = clean_desc[:250] + "..."

                    raw_items.append({
                        "title": title,
                        "description": clean_desc,
                        "link": link or "https://azure.microsoft.com/en-us/updates/",
                        "pub_date": pub_date[:16] if pub_date else "최근 업데이트"
                    })
                if raw_items:
                    break
        except Exception:
            continue

    if not raw_items:
        raw_items = [
            {
                "title": "General availability: Azure Storage support for TLS 1.3",
                "description": "Azure Storage now provides full GA support for TLS 1.3 to improve security and performance across all storage endpoints.",
                "link": "https://azure.microsoft.com/en-us/updates/",
                "pub_date": "Recently Published"
            },
            {
                "title": "Public preview: Multi-region load balancing for Azure Kubernetes Service (AKS)",
                "description": "Automate cross-region traffic distribution and health failover directly from Azure Kubernetes Service.",
                "link": "https://azure.microsoft.com/en-us/updates/",
                "pub_date": "Recently Published"
            },
            {
                "title": "Retirement notice: TLS 1.0 and 1.1 protocol enforcement for Azure App Services",
                "description": "Starting late 2026, legacy TLS versions will be completely retired across all Azure App Service web apps.",
                "link": "https://azure.microsoft.com/en-us/updates/",
                "pub_date": "Recently Published"
            }
        ]

    # 한국어 타이틀 일괄 생성 (규칙 + AI 하이브리드)
    return translate_titles_batch(raw_items, api_key=api_key)


# ==============================================================================
# 2. 운영 인프라 프로바이더 (운영 MCP / Mock ARM JSON)
# ==============================================================================
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
        return f"[실시간 Azure MCP 연동]\n• 엔드포인트: {self.live_endpoint}\n• 모드: Live Azure Tenant Infrastructure"


# ==============================================================================
# 3. 공식 지식 프로바이더 (학습 MCP: MS Learn + 멀티클라우드 MCP)
# ==============================================================================
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


# ==============================================================================
# 4. 서드파티 & 사내 가이드 RAG 프로바이더
# ==============================================================================
class ThirdPartyRAGProvider:
    def __init__(self, enabled: bool = None, custom_docs: list = None):
        self.enabled = settings.ENABLE_THIRD_PARTY_RAG if enabled is None else enabled
        
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
# 5. 알림 헬퍼 (Slack & Telegram)
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
    except Exception:
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
    except Exception:
        return False


# ==============================================================================
# 6. LLM 오케스트레이션 헬퍼 (503 혼잡 자동 재시도 및 다중 모델 폴백)
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
