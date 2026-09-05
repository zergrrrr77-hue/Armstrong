// 화면에 메모를 그리고, 버튼 클릭에 반응하는 로직을 담당하는 파일이에요.
// 실제 저장/삭제는 storage.js의 MemoStorage가 처리하고, 여기서는 "화면"만 신경 씁니다.

const memoListEl = document.getElementById("memo-list");
const emptyStateEl = document.getElementById("empty-state");
const memoCountEl = document.getElementById("memo-count");
const sortSelectEl = document.getElementById("sort-select");

const dialogEl = document.getElementById("memo-dialog");
const dialogHeadingEl = document.getElementById("dialog-heading");
const memoFormEl = document.getElementById("memo-form");
const titleInputEl = document.getElementById("memo-title-input");
const contentInputEl = document.getElementById("memo-content-input");
const cancelBtnEl = document.getElementById("dialog-cancel-btn");
const fabBtnEl = document.getElementById("fab-btn");

// 지금 다이얼로그가 "새로 쓰는 중"인지 "수정 중"인지 구분하기 위한 값.
// null이면 새 메모, 문자열(id)이 들어있으면 그 메모를 수정 중이라는 뜻.
let editingMemoId = null;

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

function render() {
  const memos = sortMemos(MemoStorage.getAll(), sortSelectEl.value);

  memoCountEl.textContent = memos.length > 0 ? `총 ${memos.length}개` : "";
  emptyStateEl.hidden = memos.length > 0;

  memoListEl.innerHTML = "";
  memos.forEach((memo) => memoListEl.appendChild(createMemoCard(memo)));
}

function openDialog(mode, memo) {
  memoFormEl.reset();

  if (mode === "edit" && memo) {
    editingMemoId = memo.id;
    dialogHeadingEl.textContent = "메모 수정";
    titleInputEl.value = memo.title;
    contentInputEl.value = memo.content;
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

  if (!title) {
    titleInputEl.focus();
    return;
  }

  if (editingMemoId) {
    MemoStorage.update(editingMemoId, title, content);
  } else {
    MemoStorage.create(title, content);
  }

  dialogEl.close();
  render();
});

sortSelectEl.addEventListener("change", render);

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

console.log("아이디어 메모장 - 2단계(작성/목록) 로드 완료");
