// 이 파일은 "서비스 워커"예요. 웹페이지와 별도로 브라우저 뒤편에서 실행되면서,
// 파일들을 미리 저장(캐싱)해뒀다가 인터넷이 없을 때도 앱을 열 수 있게 해줘요.

// 캐시 이름 뒤 숫자를 올리면(v1 -> v2), 브라우저가 예전 캐시를 지우고 새로 받아요.
// 나중에 파일을 수정할 때마다 이 숫자를 올려주면 됩니다.
const CACHE_NAME = "idea-memo-v3";

// 앱이 오프라인에서도 뜨는 데 필요한 최소 파일 목록 ("앱 껍데기"라는 뜻으로 App Shell이라 불러요)
const APP_SHELL = [
  "./",
  "./index.html",
  "./css/style.css",
  "./js/storage.js",
  "./js/app.js",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

// 서비스 워커가 처음 설치될 때: 위 파일들을 캐시에 저장해둡니다.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// 새 버전이 활성화될 때: 예전 버전 캐시는 지워서 저장 공간을 아낍니다.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// 페이지가 파일을 요청할 때: 캐시에 있으면 그걸 먼저 주고(빠름 + 오프라인 지원),
// 캐시에 없으면 그때 인터넷에서 받아옵니다.
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
