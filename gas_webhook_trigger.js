/**
 * Cloud SRE-NEXUS - Google Apps Script (GAS) Trigger Script
 * ==========================================================
 * 이 스크립트를 Google 스프레드시트의 [확장 프로그램] > [Apps Script]에 붙여넣습니다.
 * - 트리거 기능: Azure Updates RSS 또는 Service Health 이벤트를 감지하여
 *   Cloud SRE-NEXUS 웹훅 엔드포인트로 JSON 페이로드를 자동 발송합니다.
 */

// Cloud SRE-NEXUS 엔드포인트 URL (로컬 ngrok URL 또는 Google Cloud Run 배포 URL)
const SRE_NEXUS_WEBHOOK_URL = "https://your-cloud-run-url/webhook";

function sendToCloudSreNexus(eventTitle, eventDetails, category) {
  var payload = {
    "project": "Cloud SRE-NEXUS",
    "timestamp": new Date().toISOString(),
    "event_type": category || "Azure Service Update",
    "title": eventTitle,
    "details": eventDetails,
    "source": "GAS Automated RSS Monitor"
  };

  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };

  try {
    var response = UrlFetchApp.fetch(SRE_NEXUS_WEBHOOK_URL, options);
    Logger.log("[Cloud SRE-NEXUS] Webhook sent successfully: " + response.getResponseCode());
  } catch (err) {
    Logger.log("[Cloud SRE-NEXUS] Webhook error: " + err.toString());
  }
}

// 1시간 주기 실행용 테스트 함수
function triggerCheckUpdates() {
  var sampleTitle = "Azure Storage TLS 1.2 Deprecation Notice";
  var sampleDetails = "Starting November 2026, Azure Storage will enforce TLS 1.3 as default and deprecate older versions.";
  sendToCloudSreNexus(sampleTitle, sampleDetails, "Security Compliance");
}
