// 메모를 실제로 "어디에 저장할지" 담당하는 파일입니다.
// 지금은 localStorage(브라우저 안에 있는 저장 공간, 인터넷 없이도 유지됨)를 쓰지만,
// 나중에 클라우드 동기화로 바꿀 때는 이 파일 안의 함수들만 서버 통신으로 바꾸면 되도록
// "저장 방식"과 "화면 로직(app.js)"을 분리해뒀어요.

(() => {
  const STORAGE_KEY = "idea-memo-webapp:memos";

  // 태그 기능을 추가하기 전(2단계)에 저장된 메모에는 tags가 없을 수 있어서,
  // 불러올 때 tags가 없으면 빈 배열([])로 채워줍니다.
  const loadAll = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const memos = raw ? JSON.parse(raw) : [];
      return memos.map((memo) => ({ tags: [], ...memo }));
    } catch (error) {
      console.warn("메모를 불러오는 중 문제가 생겼어요:", error);
      return [];
    }
  };

  const saveAll = (memos) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(memos));
  };

  const makeId = () => {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return `memo-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  // 다른 파일(app.js)에서 window.MemoStorage.xxx() 형태로 사용합니다.
  window.MemoStorage = {
    getAll: loadAll,

    create(title, content, tags = []) {
      const memos = loadAll();
      const now = new Date().toISOString();
      const memo = {
        id: makeId(),
        title: title.trim(),
        content: content.trim(),
        tags,
        createdAt: now,
        updatedAt: now,
      };
      memos.push(memo);
      saveAll(memos);
      return memo;
    },

    update(id, title, content, tags = []) {
      const memos = loadAll();
      const target = memos.find((memo) => memo.id === id);
      if (!target) return null;
      target.title = title.trim();
      target.content = content.trim();
      target.tags = tags;
      target.updatedAt = new Date().toISOString();
      saveAll(memos);
      return target;
    },

    remove(id) {
      saveAll(loadAll().filter((memo) => memo.id !== id));
    },

    // 지금까지 쓰인 태그를 전부 모아 중복 없이, 가나다순으로 돌려줍니다.
    // (화면 위쪽 태그 필터 목록을 그릴 때 씁니다.)
    getAllTags() {
      const tagSet = new Set();
      loadAll().forEach((memo) => memo.tags.forEach((tag) => tagSet.add(tag)));
      return [...tagSet].sort((a, b) => a.localeCompare(b, "ko"));
    },
  };
})();
