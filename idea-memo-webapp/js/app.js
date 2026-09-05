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

// 지금 다이얼로그가 "새로 쓰는 중"인지 "수정 중"인지 구분하기 위한 값.
// null이면 새 메모, 문자열(id)이 들어있으면 그 메모를 수정 중이라는 뜻.
let editingMemoId = null;

// 지금 선택된 태그 필터. null이면 "전체"(필터 없음)라는 뜻.
let activeTag = null;

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
  return sorted;
}

// 메모 하나를 <details> 카드 DOM으로 만듭니다.
// innerHTML 대신 createElement + textContent를 써서, 메모 내용에 <script> 같은
// 이상한 태그가 들어있어도 그대로 "글자"로만 표시되게(안전하게) 만들었어요.
function createMemoCard(memo) {
  const details = document.createElement("details");
  details.className = "memo-card";
  details.dataset.id = memo.id;

  const summary = document.createElement("summary");
  summary.className = "memo-summary";

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
        event.preventDefault();
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

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "icon-btn";
  editBtn.setAttribute("aria-label", "메모 수정");
  editBtn.textContent = "✏️";
  editBtn.addEventListener("click", (event) => {
    // <summary> 안에서 버튼을 눌러도 카드가 펼쳐지지 않도록 막습니다.
    event.preventDefault();
    event.stopPropagation();
    openDialog("edit", memo);
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "icon-btn";
  deleteBtn.setAttribute("aria-label", "메모 삭제");
  deleteBtn.textContent = "🗑️";
  deleteBtn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (confirm(`"${memo.title}" 메모를 삭제할까요?`)) {
      MemoStorage.remove(memo.id);
      render();
    }
  });

  actions.append(editBtn, deleteBtn);
  summary.append(main, actions);

  const content = document.createElement("div");
  content.className = "memo-content";
  content.textContent = memo.content || "(내용 없음)";

  details.append(summary, content);
  return details;
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
  titleInputEl.focus();
}

fabBtnEl.addEventListener("click", () => openDialog("create"));

cancelBtnEl.addEventListener("click", () => dialogEl.close());

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

  dialogEl.close();
  render();
});

sortSelectEl.addEventListener("change", render);
searchInputEl.addEventListener("input", render);

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

console.log("아이디어 메모장 - 3단계(검색/태그) 로드 완료");
