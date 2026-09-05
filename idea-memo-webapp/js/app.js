// 브라우저가 "서비스 워커(Service Worker, 웹페이지 뒤에서 계속 실행되며
// 오프라인 캐싱·백그라운드 동작을 담당하는 스크립트)"를 지원하면 등록합니다.
// 이게 있어야 인터넷이 없어도 앱이 열리고, "홈 화면에 추가"도 가능해져요.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("service-worker.js")
      .then(() => {
        console.log("서비스 워커 등록 완료 (오프라인 지원 준비됨)");
      })
      .catch((error) => {
        console.warn("서비스 워커 등록 실패:", error);
      });
  });
}

console.log("아이디어 메모장 - 1단계(기본 틀) 로드 완료");
