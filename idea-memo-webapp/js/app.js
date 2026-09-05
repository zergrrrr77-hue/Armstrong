// 화면에 메모를 그리고, 버튼 클릭에 반응하는 로직을 담당하는 파일이에요.
// 실제 저장/삭제는 storage.js의 MemoStorage가 처리하고, 여기서는 "화면"만 신경 씁니다.

const memoListEl = document.getElementById("memo-list");
const emptyStateEl = document.getElementById("empty-state");
const memoCountEl = document.getElementById("memo-count");
const sortSelectEl = document.getElementById("sort-select");
const searchInputEl = document.getElementById("search-input");
const tagFilterEl = document.getElementById("tag-filter");

const dialogEl = document.getElementById("memo-dialog");
const dialogHeadingEl = document.getElementById("dialog-heading");
const memoFormEl = document.getElementById("memo-form");
const titleInputEl = document.getElementById("memo-title-input");
const contentInputEl = document.getElementById("memo-content-input");
const tagsInputEl = document.getElementById("memo-tags-input");
const cancelBtnEl = document.getElementById("dialog-cancel-btn");
const fabBtnEl = document.getElementById("fab-btn");
const exportBtnEl = document.getElementById("export-btn");
const importBtnEl = document.getElementById("import-btn");
const importFileInputEl = document.getElementById("import-file-input");

// 지금 다이얼로그가 "새로 쓰는 중"인지 "수정 중"인지 구분하기 위한 값.
// null이면 새 메모, 문자열(id)이 들어있으면 그 메모를 수정 중이라는 뜻.
let editingMemoId = null;

// 지금 선택된 태그 필터. null이면 "전체"(필터 없음)라는 뜻.
let activeTag = null;

// 지금 펼쳐져 있는 카드들의 id 모음. render()가 목록을 통째로 다시 그려도
// (검색 중 타이핑할 때마다처럼) 펼쳐둔 카드가 도로 접히지 않도록 여기에 기억해둡니다.
const expandedIds = new Set();

// "아이디어, 할일 " 같은 입력을 ["아이디어", "할일"]로 바꿔줍니다.
// (빈 칸이나 중복은 제거)
function parseTagsInput(rawValue) {
  const tags = rawValue
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
  return [...new Set(tags)];
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sortMemos(memos, sortBy) {
  const sorted = [...memos];
  if (sortBy === "oldest") {
    sorted.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  } else if (sortBy === "title") {
    sorted.sort((a, b) => a.title.localeCompare(b.title, "ko"));
  } else {
    // 기본값: 최신순
    sorted.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }

  // 정렬 기준과 상관없이, 고정(📌)해둔 메모는 항상 맨 위로.
  // Array.sort는 "안정 정렬"이라 같은 그룹(고정/비고정) 안에서는 방금 정한 순서가 그대로 유지돼요.
  sorted.sort((a, b) => Number(b.pinned) - Number(a.pinned));
  return sorted;
}

// 메모 하나를 카드 DOM으로 만듭니다.
// innerHTML 대신 createElement + textContent를 써서, 메모 내용에 <script> 같은
// 이상한 태그가 들어있어도 그대로 "글자"로만 표시되게(안전하게) 만들었어요.
//
// 예전에는 <details>/<summary>(브라우저 기본 펼치기 태그)를 썼는데, 그 태그는
// 펼칠 때 부드럽게 애니메이션되지 않아요(순식간에 나타남/사라짐). 그래서 직접
// 버튼 + div로 만들고, 펼침 상태를 우리가 기억했다가 CSS 트랜지션으로 부드럽게 열립니다.
function createMemoCard(memo) {
  const card = document.createElement("div");
  card.className = "memo-card" + (memo.pinned ? " pinned" : "");
  card.dataset.id = memo.id;

  const isExpanded = expandedIds.has(memo.id);

  // 진짜 <button>으로 만들면 그 안에 있는 수정/삭제/고정 버튼들이 "버튼 속 버튼"이
  // 되어버려서(HTML 규칙 위반, 스크린리더 혼란) div + role="button"으로 만들고
  // 키보드(Enter/Space)로도 펼칠 수 있게 tabindex를 줍니다.
  const header = document.createElement("div");
  header.className = "memo-summary";
  header.setAttribute("role", "button");
  header.setAttribute("tabindex", "0");
  header.setAttribute("aria-expanded", String(isExpanded));

  const main = document.createElement("div");
  main.className = "memo-summary-main";

  const title = document.createElement("h2");
  title.className = "memo-title";
  title.textContent = memo.title;

  const date = document.createElement("time");
  date.className = "memo-date";
  const updated = memo.updatedAt !== memo.createdAt;
  date.textContent = formatDate(memo.createdAt) + (updated ? " (수정됨)" : "");

  main.append(title, date);

  if (memo.tags.length > 0) {
    const tagsRow = document.createElement("div");
    tagsRow.className = "memo-tags";
    memo.tags.forEach((tag) => {
      const tagEl = document.createElement("span");
      tagEl.className = "memo-tag";
      tagEl.textContent = tag;
      // 카드 안의 태그를 눌러도 그 태그로 바로 필터링되도록.
      tagEl.addEventListener("click", (event) => {
        event.stopPropagation();
        activeTag = tag;
        render();
      });
      tagsRow.appendChild(tagEl);
    });
    main.appendChild(tagsRow);
  }

  const actions = document.createElement("div");
  actions.className = "memo-actions";

  const pinBtn = document.createElement("button");
  pinBtn.type = "button";
  pinBtn.className = "icon-btn pin-btn" + (memo.pinned ? " active" : "");
  pinBtn.setAttribute("aria-label", memo.pinned ? "고정 해제" : "메모 고정");
  pinBtn.textContent = "📌";
  pinBtn.addEventListener("click", (event) => {
    // 버튼이 header(펼치기 버튼) 안에 있어서, 누르면 펼치기까지 같이 실행되는 걸 막습니다.
    event.stopPropagation();
    MemoStorage.togglePin(memo.id);
    render();
  });

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "icon-btn";
  editBtn.setAttribute("aria-label", "메모 수정");
  editBtn.textContent = "✏️";
  editBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openDialog("edit", memo);
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "icon-btn";
  deleteBtn.setAttribute("aria-label", "메모 삭제");
  deleteBtn.textContent = "🗑️";
  deleteBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    if (confirm(`"${memo.title}" 메모를 삭제할까요?`)) {
      expandedIds.delete(memo.id);
      MemoStorage.remove(memo.id);
      render();
    }
  });

  actions.append(pinBtn, editBtn, deleteBtn);
  header.append(main, actions);

  // 펼침/접힘을 CSS 트랜지션으로 부드럽게 처리하기 위한 래퍼.
  // (grid-template-rows를 0fr <-> 1fr로 움직이면, 내용 높이를 몰라도 자연스럽게 늘었다 줄었다 해요)
  const contentWrapper = document.createElement("div");
  contentWrapper.className = "memo-content-wrapper" + (isExpanded ? " open" : "");

  const content = document.createElement("div");
  content.className = "memo-content";
  content.textContent = memo.content || "(내용 없음)";
  contentWrapper.appendChild(content);

  const toggleExpanded = () => {
    const nowExpanded = !expandedIds.has(memo.id);
    if (nowExpanded) {
      expandedIds.add(memo.id);
    } else {
      expandedIds.delete(memo.id);
    }
    header.setAttribute("aria-expanded", String(nowExpanded));
    contentWrapper.classList.toggle("open", nowExpanded);
  };

  header.addEventListener("click", toggleExpanded);
  // role="button"인 div는 버튼과 달리 Enter/Space를 눌러도 저절로 반응하지 않아서 직접 처리합니다.
  header.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleExpanded();
    }
  });

  card.append(header, contentWrapper);
  return card;
}

// 검색어/태그 필터를 함께 적용합니다. 검색은 제목과 내용 둘 다에서 찾아요.
function filterMemos(memos) {
  let result = memos;

  if (activeTag) {
    result = result.filter((memo) => memo.tags.includes(activeTag));
  }

  const query = searchInputEl.value.trim().toLowerCase();
  if (query) {
    result = result.filter(
      (memo) =>
        memo.title.toLowerCase().includes(query) ||
        memo.content.toLowerCase().includes(query)
    );
  }

  return result;
}

// 화면 위쪽의 태그 칩(전체 + 지금까지 쓰인 태그들)을 다시 그립니다.
function renderTagFilter() {
  const allTags = MemoStorage.getAllTags();
  tagFilterEl.hidden = allTags.length === 0;
  tagFilterEl.innerHTML = "";

  const makeChip = (label, tagValue) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "tag-chip" + (activeTag === tagValue ? " active" : "");
    chip.textContent = label;
    chip.addEventListener("click", () => {
      activeTag = tagValue;
      render();
    });
    return chip;
  };

  tagFilterEl.appendChild(makeChip("전체", null));
  allTags.forEach((tag) => tagFilterEl.appendChild(makeChip(tag, tag)));
}

function render() {
  renderTagFilter();

  const allMemos = MemoStorage.getAll();
  const visibleMemos = sortMemos(filterMemos(allMemos), sortSelectEl.value);

  memoCountEl.textContent = visibleMemos.length > 0 ? `총 ${visibleMemos.length}개` : "";

  if (allMemos.length === 0) {
    emptyStateEl.hidden = false;
    emptyStateEl.innerHTML = "아직 메모가 없어요.<br />오른쪽 아래 + 버튼을 눌러 첫 메모를 남겨보세요!";
  } else if (visibleMemos.length === 0) {
    emptyStateEl.hidden = false;
    emptyStateEl.innerHTML = "검색어나 태그 조건에 맞는 메모가 없어요.";
  } else {
    emptyStateEl.hidden = true;
  }

  memoListEl.innerHTML = "";
  visibleMemos.forEach((memo) => memoListEl.appendChild(createMemoCard(memo)));
}

function openDialog(mode, memo) {
  memoFormEl.reset();

  if (mode === "edit" && memo) {
    editingMemoId = memo.id;
    dialogHeadingEl.textContent = "메모 수정";
    titleInputEl.value = memo.title;
    contentInputEl.value = memo.content;
    tagsInputEl.value = memo.tags.join(", ");
  } else {
    editingMemoId = null;
    dialogHeadingEl.textContent = "새 메모";
  }

  dialogEl.showModal();
  // showModal() 직후 바로 클래스를 붙이면 트랜지션이 씹힐 때가 있어서,
  // 브라우저가 다음 화면을 그리기 직전(requestAnimationFrame)에 붙여서 확실히 애니메이션되게 합니다.
  requestAnimationFrame(() => dialogEl.classList.add("is-visible"));
  titleInputEl.focus();
}

// 팝업을 부드럽게 닫습니다: 클래스를 떼서 "닫히는 중" 트랜지션을 보여준 뒤,
// 트랜지션이 끝나면 실제로 dialog.close()를 호출해요.
function closeDialogAnimated() {
  dialogEl.classList.remove("is-visible");
  window.setTimeout(() => dialogEl.close(), 180);
}

fabBtnEl.addEventListener("click", () => openDialog("create"));

cancelBtnEl.addEventListener("click", () => closeDialogAnimated());

memoFormEl.addEventListener("submit", (event) => {
  event.preventDefault();

  const title = titleInputEl.value.trim();
  const content = contentInputEl.value.trim();
  const tags = parseTagsInput(tagsInputEl.value);

  if (!title) {
    titleInputEl.focus();
    return;
  }

  if (editingMemoId) {
    MemoStorage.update(editingMemoId, title, content, tags);
  } else {
    MemoStorage.create(title, content, tags);
  }

  closeDialogAnimated();
  render();
});

sortSelectEl.addEventListener("change", render);
searchInputEl.addEventListener("input", render);

// 내보내기: 지금 메모를 전부 JSON 파일로 다운로드합니다. (백업 / 다른 기기로 옮기기용)
exportBtnEl.addEventListener("click", () => {
  const json = MemoStorage.exportAsJson();
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const today = new Date().toISOString().slice(0, 10);
  const link = document.createElement("a");
  link.href = url;
  link.download = `idea-memo-backup-${today}.json`;
  link.click();

  URL.revokeObjectURL(url);
});

// 가져오기: "가져오기" 버튼을 누르면, 화면엔 안 보이는 파일 선택창을 대신 열어줍니다.
importBtnEl.addEventListener("click", () => importFileInputEl.click());

importFileInputEl.addEventListener("change", () => {
  const file = importFileInputEl.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const { added, skipped } = MemoStorage.importFromJson(reader.result);
      alert(
        `${added}개의 메모를 가져왔어요.` +
          (skipped > 0 ? ` (형식이 이상해서 ${skipped}개는 건너뛰었어요)` : "")
      );
      render();
    } catch (error) {
      alert(`가져오기에 실패했어요: ${error.message}`);
    }
  };
  reader.readAsText(file);

  // 같은 파일을 다시 선택해도 change 이벤트가 또 일어나도록 값을 비워둡니다.
  importFileInputEl.value = "";
});

render();

// 브라우저가 서비스 워커를 지원하면 등록합니다. (오프라인 지원 + 홈 화면 추가 준비)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("service-worker.js")
      .then(() => console.log("서비스 워커 등록 완료 (오프라인 지원 준비됨)"))
      .catch((error) => console.warn("서비스 워커 등록 실패:", error));
  });
}

console.log("아이디어 메모장 - 4단계(디자인/추가기능) 로드 완료");
