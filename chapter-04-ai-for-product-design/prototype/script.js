const data = window.noteWiseData;
let questionIndex = 0;
let score = 0;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const screenLabels = {
  "screen-dashboard": "Dashboard",
  "screen-materials": "Tài liệu",
  "screen-qa": "Document Q&A",
  "screen-quiz": "Quiz AI",
  "screen-analytics": "Analytics",
  "screen-recommendations": "Gợi ý học tập",
  "screen-history": "Lịch sử",
};

function navigateTo(screenId) {
  const target = document.getElementById(screenId);
  if (!target) return;

  $$(".screen-content").forEach((screen) => {
    const isTarget = screen === target;
    screen.classList.toggle("hidden", !isTarget);
    screen.classList.toggle("block", isTarget);
  });

  $$(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.screen === screenId);
  });

  $("#breadcrumb-title").textContent = screenLabels[screenId] || "Dashboard";
  if (screenId === "screen-quiz") renderQuestion();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.navigateTo = navigateTo;

function documentMarkup(documentItem) {
  const fileType = documentItem.meta.startsWith("PDF")
    ? "PDF"
    : documentItem.meta.startsWith("PPT")
      ? "PPT"
      : "DOC";
  const statusClass =
    documentItem.status === "Sẵn sàng"
      ? "ready"
      : documentItem.status === "Thất bại"
        ? "failed"
        : "processing";
  return `<div class="document">
    <div class="doc-icon ${documentItem.color}">${fileType}</div>
    <div class="doc-info"><strong>${documentItem.title}</strong><small>${documentItem.meta} · ${documentItem.subject} · ${documentItem.date}</small></div>
    <span class="status-badge ${statusClass}">${documentItem.status}</span>
    <div class="doc-progress"><small>${documentItem.progress}%</small><div class="progress-line"><span style="width:${documentItem.progress}%"></span></div></div>
    <div class="quick-actions">
      <button class="quick-action" data-action="summary">Xem tóm tắt</button>
      <button class="quick-action" data-action="qa">Hỏi đáp AI</button>
      <button class="quick-action" data-action="quiz-setup">Tạo Quiz</button>
    </div>
    <button class="doc-open" aria-label="Mở ${documentItem.title}" data-action="qa">↗</button>
    ${documentItem.status === "Thất bại" ? '<button class="retry-btn" data-action="retry">Thử lại</button>' : ""}
    <button class="doc-menu" data-action="delete">•••</button>
  </div>`;
}

function topicMarkup(topic) {
  return `<div class="weak-item"><span class="weak-name">${topic.name}</span><span class="weak-score">${topic.delta}</span><div class="progress-line"><span style="width:${topic.score}%;background:var(--${topic.tone})"></span></div><span class="weak-page">${topic.page} · ${topic.score}% · ${topic.priority}</span></div>`;
}

function renderLists() {
  $("#dashboard-documents").innerHTML = data.documents
    .slice(0, 3)
    .map(documentMarkup)
    .join("");
  $("#all-documents").innerHTML = data.documents.map(documentMarkup).join("");
  $("#dashboard-topics").innerHTML = data.weakTopics
    .slice(0, 3)
    .map(topicMarkup)
    .join("");
  $("#analytics-topics").innerHTML = data.weakTopics.map(topicMarkup).join("");
  $("#priority-topics").innerHTML = data.weakTopics
    .filter((topic) => topic.score < 60)
    .map(
      (topic) =>
        `<div class="priority-card"><span class="status-badge failed">${topic.priority}</span><strong>${topic.name}</strong><p>${topic.reason}</p><button class="ghost-btn" data-screen="screen-quiz">Tạo Quiz ôn tập</button><button class="panel-link" data-screen="screen-qa">Đọc ${topic.page} →</button></div>`,
    )
    .join("");
  $("#history-table").innerHTML =
    `<div class="history-row history-head"><span>Thời gian</span><span>Hoạt động</span><span>Tài liệu</span><span>Điểm</span><span>Thời lượng</span><span>Chủ đề</span></div>${data.history.map((item) => `<button class="history-row" data-action="history-detail"><span>${item.date}</span><span class="activity-tag">${item.activity}</span><span>${item.document}</span><strong>${item.score}</strong><span>${item.duration}</span><span>${item.topic}</span></button>`).join("")}`;
}

function renderQuestion() {
  const question = data.quizQuestions[questionIndex];
  $("#quiz-topic").textContent = question.topic;
  $("#quiz-question").textContent = question.question;
  $("#quiz-progress").textContent =
    `Câu ${questionIndex + 1} / ${data.quizQuestions.length}`;
  $("#quiz-progress-bar").style.width =
    `${((questionIndex + 1) / data.quizQuestions.length) * 100}%`;
  $("#quiz-options").innerHTML = question.options
    .map(
      (option, index) =>
        `<button class="option" data-index="${index}"><b>${String.fromCharCode(65 + index)}</b> ${option}</button>`,
    )
    .join("");
  $("#quiz-feedback").textContent = "Chọn một đáp án để tiếp tục.";
  $("#next-question").textContent =
    questionIndex === data.quizQuestions.length - 1
      ? "Nộp bài"
      : "Câu tiếp theo →";
  $("#next-question").disabled = true;
  $("#quiz-result").classList.add("hidden");
}

function openQuizSetup() {
  $("#quiz-dialog").showModal();
}

function finishQuiz() {
  $("#result-score").textContent =
    `${Math.round((score / data.quizQuestions.length) * 100)}%`;
  $("#result-correct").textContent = `${score}/${data.quizQuestions.length}`;
  $("#quiz-result").classList.remove("hidden");
  $("#quiz-result").classList.add("block");
  $("#quiz-question").textContent = "Bạn đã hoàn thành bài quiz.";
  $("#quiz-options").innerHTML =
    `<div class="recommendation"><b>Kết quả đã lưu</b>AI đã lưu giải thích và citation cho từng câu trả lời.</div>`;
  $("#next-question").disabled = true;
}

document.addEventListener("click", (event) => {
  const screenTrigger = event.target.closest("[data-screen]");
  if (screenTrigger) {
    const dialog = screenTrigger.closest("dialog");
    if (dialog) dialog.close();
    navigateTo(screenTrigger.dataset.screen);
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "upload") {
    $("#upload-zone").classList.add("uploading");
    setTimeout(() => $("#upload-zone").classList.remove("uploading"), 900);
  }
  if (action === "summary") {
    navigateTo("screen-qa");
    $$('[data-reader-tab="summary"]').forEach((tab) => tab.click());
  }
  if (action === "qa" || action === "open") navigateTo("screen-qa");
  if (action === "quiz-setup") openQuizSetup();
  if (action === "retry") {
    const row = event.target.closest(".document");
    row.querySelector(".status-badge").textContent = "Đang xử lý";
    row.querySelector(".status-badge").className = "status-badge processing";
  }
  if (action === "delete") $("#delete-dialog").showModal();
  if (action === "retry-quiz") {
    questionIndex = 0;
    score = 0;
    navigateTo("screen-quiz");
  }
  if (action === "history-detail")
    window.alert("Chi tiết phiên học đã được mở.");
  if (event.target.closest("[data-close-dialog]") && !screenTrigger) {
    event.target.closest("dialog").close();
  }

  if (event.target.closest("[data-highlight]")) {
    $("#citation-highlight").classList.add("highlighted");
    setTimeout(
      () => $("#citation-highlight").classList.remove("highlighted"),
      1800,
    );
  }

  const option = event.target.closest(".option");
  if (option) {
    $$(".option").forEach((item) => item.classList.remove("selected"));
    option.classList.add("selected");
    $("#next-question").disabled = false;
    $("#quiz-feedback").textContent =
      Number(option.dataset.index) === data.quizQuestions[questionIndex].answer
        ? "Chính xác. Bạn có thể đi tiếp."
        : "Chưa đúng. Xem giải thích sau khi hoàn thành.";
  }

  if (
    event.target.closest("#next-question") &&
    !event.target.closest("#next-question").disabled
  ) {
    if (
      Number($(".option.selected").dataset.index) ===
      data.quizQuestions[questionIndex].answer
    )
      score += 1;
    if (questionIndex < data.quizQuestions.length - 1) {
      questionIndex += 1;
      renderQuestion();
    } else finishQuiz();
  }
});

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-reader-tab]");
  if (tab) {
    $$("[data-reader-tab]").forEach((item) =>
      item.classList.toggle("active", item === tab),
    );
    $("#source-content").hidden = tab.dataset.readerTab !== "source";
    $("#summary-content").hidden = tab.dataset.readerTab !== "summary";
  }
  const authTab = event.target.closest("[data-auth-mode]");
  if (authTab) {
    const register = authTab.dataset.authMode === "register";
    $$(".auth-tab").forEach((item) =>
      item.classList.toggle("active", item === authTab),
    );
    $$(".register-only").forEach((item) => (item.hidden = !register));
    $("#auth-title").textContent = register
      ? "Tạo tài khoản mới"
      : "Chào mừng trở lại";
    $(".auth-submit").textContent = register ? "Tạo tài khoản" : "Đăng nhập";
  }
});

$("#auth-form").addEventListener("submit", (event) => {
  event.preventDefault();
  $("#email-error").textContent = $("#auth-email").value.includes("@")
    ? ""
    : "Email chưa hợp lệ.";
  $("#password-error").textContent =
    $("#auth-password").value.length >= 6
      ? ""
      : "Mật khẩu cần ít nhất 6 ký tự.";
  if (!$("#email-error").textContent && !$("#password-error").textContent)
    navigateTo("screen-dashboard");
});

$$("[data-toggle-password]").forEach((button) =>
  button.addEventListener("click", () => {
    const input = $("#auth-password");
    input.type = input.type === "password" ? "text" : "password";
    button.textContent = input.type === "password" ? "Hiện" : "Ẩn";
  }),
);

$("#material-search").addEventListener("input", (event) =>
  $$("#all-documents .document").forEach((row) => {
    row.hidden = !row.textContent
      .toLowerCase()
      .includes(event.target.value.toLowerCase());
  }),
);

renderLists();
renderQuestion();
navigateTo("screen-dashboard");
