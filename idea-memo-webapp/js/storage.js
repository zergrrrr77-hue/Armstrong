// 메모를 실제로 "어디에 저장할지" 담당하는 파일입니다.
// 지금은 localStorage(브라우저 안에 있는 저장 공간, 인터넷 없이도 유지됨)를 쓰지만,
// 나중에 클라우드 동기화로 바꿀 때는 이 파일 안의 함수들만 서버 통신으로 바꾸면 되도록
// "저장 방식"과 "화면 로직(app.js)"을 분리해뒀어요.

(() => {
  const STORAGE_KEY = "idea-memo-webapp:memos";

  // 태그(3단계)나 고정(4단계) 같은 새 기능이 생기기 전에 저장된 메모에는
  // 그 필드가 없을 수 있어서, 불러올 때 기본값을 채워줍니다.
  const loadAll = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const memos = raw ? JSON.parse(raw) : [];
      return memos.map((memo) => ({ tags: [], pinned: false, ...memo }));
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
        pinned: false,
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

    togglePin(id) {
      const memos = loadAll();
      const target = memos.find((memo) => memo.id === id);
      if (!target) return null;
      target.pinned = !target.pinned;
      saveAll(memos);
      return target;
    },

    // 지금까지 쓰인 태그를 전부 모아 중복 없이, 가나다순으로 돌려줍니다.
    // (화면 위쪽 태그 필터 목록을 그릴 때 씁니다.)
    getAllTags() {
      const tagSet = new Set();
      loadAll().forEach((memo) => memo.tags.forEach((tag) => tagSet.add(tag)));
      return [...tagSet].sort((a, b) => a.localeCompare(b, "ko"));
    },

    // 지금 저장된 모든 메모를 예쁘게 들여쓴 JSON 글자로 바꿔줍니다. (내보내기용)
    exportAsJson() {
      return JSON.stringify(loadAll(), null, 2);
    },

    // 내보내기로 받은 JSON 파일(또는 그 안의 배열)을 가져와서 기존 메모 뒤에 추가합니다.
    // 잘못된 형식의 항목은 건너뛰고, 몇 개를 추가/건너뛰었는지 알려줍니다.
    importFromJson(jsonText) {
      let parsed;
      try {
        parsed = JSON.parse(jsonText);
      } catch (error) {
        throw new Error("올바른 JSON 파일이 아니에요.");
      }

      const incoming = Array.isArray(parsed) ? parsed : [];
      const memos = loadAll();
      let added = 0;
      let skipped = 0;

      incoming.forEach((item) => {
        if (!item || typeof item.title !== "string" || !item.title.trim()) {
          skipped += 1;
          return;
        }
        const now = new Date().toISOString();
        memos.push({
          id: makeId(),
          title: item.title.trim(),
          content: typeof item.content === "string" ? item.content.trim() : "",
          tags: Array.isArray(item.tags) ? item.tags.filter((t) => typeof t === "string") : [],
          pinned: false,
          createdAt: typeof item.createdAt === "string" ? item.createdAt : now,
          updatedAt: typeof item.updatedAt === "string" ? item.updatedAt : now,
        });
        added += 1;
      });

      saveAll(memos);
      return { added, skipped };
    },
  };
})();
