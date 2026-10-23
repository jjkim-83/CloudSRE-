<!--
=============================================================================
Project       : Cloud SRE-NEXUS (Autonomous Cloud Operations & Architecture Copilot)
File Path     : cloud_sre_nexus/README.md
File Name     : README.md
Description   : 프로젝트 통합 가이드 및 운영 매뉴얼 (아키텍처, MCP/RAG 구조, 배포법)
Last Modified : 2026-10-23 15:47:10 KST (Asia/Seoul)
Version       : v1.5.0 (RAG 1단계 PDF 파싱, 503 재시도, Streamlit 최적화 반영)
Author/Owner  : Cloud SRE Team
=============================================================================
-->

# ☁️ Cloud SRE-NEXUS
> **Autonomous Cloud Operations & Architecture Copilot**  
> 듀얼 MCP(운영 인프라 + 학습 지식) 및 서드파티 RAG 기반 자율형 멀티/하이브리드 클라우드 SRE AI 에이전트 시스템

---

## 📌 핵심 기능 및 아키텍처 (`v1.5.0` 기준)

Cloud SRE-NEXUS는 단순한 질의응답 챗봇이 아닌, **내 인프라의 현재 스펙(운영 MCP)**과 **마이크로소프트 공식 기술 문서(학습 MCP)**, 그리고 **사내 보안 규정 및 서드파티 솔루션(RAG)**을 삼각 교차 검증하여 장애 영향도를 진단하고 실행 런북을 자동 생성하는 SRE 운영 허브입니다.

```text
[클라우드 이벤트 / 사용자 질의]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│               Cloud SRE-NEXUS Core Engine              │
│                                                        │
│  [1. 운영 MCP]         [2. 학습 MCP]      [3. 서드파티 RAG]   │
│  • Mock JSON 편집기    • MS Learn 실시간   • 사내 규정 v3.2     │
│  • Live Azure MCP      • AWS/GCP 확장     • Palo Alto / DD     │
│  (내 인프라 현황)      (공식 표준 스펙)   (사내 내규/매뉴얼)    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (삼각 교차 추론 & 런북 생성)
┌────────────────────────────────────────────────────────┐
│                   SRE Action & Alert                   │
│   • 인프라 영향도(Blast Radius) 및 위험 등급 평가       │
│   • 사내 규정 준수 단계별 런북(Runbook) 도출           │
│   • Slack Webhook 및 Telegram 실시간 원클릭 전파       │
└────────────────────────────────────────────────────────┘
