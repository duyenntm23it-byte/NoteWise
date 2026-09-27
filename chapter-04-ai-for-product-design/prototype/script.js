const data = window.noteWiseData;
let questionIndex = 0;
let score = 0;
let skippedCount = 0;
let isLoggedIn = localStorage.getItem("notewise.isLoggedIn") === "true";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const screenLabels = {
  "screen-auth": "Xác thực",
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

  const isAuthScreen = screenId === "screen-auth";
  $$(".screen-content").forEach((screen) => {
    const isTarget = !isAuthScreen && screen === target;
    screen.classList.toggle("hidden", !isTarget);
    screen.classList.toggle("block", isTarget);
  });
  $("#screen-auth").classList.toggle("hidden", !isAuthScreen);

  $$(".nav-item").forEach((item) => {
    item.classList.toggle(
      "active",
      !isAuthScreen && item.dataset.screen === screenId,
    );
  });

  $("#breadcrumb-title").textContent = screenLabels[screenId] || "Dashboard";
  if (screenId === "screen-quiz") renderQuestion();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.navigateTo = navigateTo;

function toggleAuthTab(mode) {
  const register = mode === "register";
  $("#auth-title").textContent = register
    ? "Tạo tài khoản mới"
    : "Chào mừng trở lại";
  $(".auth-submit").textContent = register ? "Đăng ký tài khoản" : "Đăng nhập";
  $$("[data-auth-tab]").forEach((tab) => {
    const active = tab.dataset.authTab === mode;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-pressed", String(active));
  });
  $$(".register-only").forEach((field) => {
    field.hidden = !register;
    field.style.display = register ? "grid" : "none";
  });
  $("#auth-confirm").required = register;
  $("#confirm-error").textContent = "";
}

window.toggleAuthTab = toggleAuthTab;

function updateAuthUI() {
  $("#guest-actions").classList.toggle("hidden", isLoggedIn);
  $("#guest-actions").hidden = isLoggedIn;
  $("#guest-actions").style.display = isLoggedIn ? "none" : "flex";
  $("#user-actions").classList.toggle("hidden", !isLoggedIn);
  $("#user-actions").hidden = !isLoggedIn;
  $("#user-actions").style.display = isLoggedIn ? "flex" : "none";
  $("#sidebar-logout").classList.toggle("hidden", !isLoggedIn);
  $("#sidebar-logout").hidden = !isLoggedIn;
  $("#upload-zone").hidden = !isLoggedIn;
  $$('[data-action="upload"]').forEach((button) => {
    button.hidden = !isLoggedIn;
  });
  ["analytics", "recommendations", "history"].forEach((screen) => {
    $(`#${screen}-content`).hidden = !isLoggedIn;
    $(`#${screen}-guest-gate`).hidden = isLoggedIn;
  });
}

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
  const visibleDocuments = isLoggedIn ? data.documents : data.documents.slice(0, 1);
  $("#dashboard-documents").innerHTML = data.documents
    .slice(0, 3)
    .map(documentMarkup)
    .join("");
  $("#all-documents").innerHTML = visibleDocuments.map(documentMarkup).join("");
  $("#materials-count").textContent = `${visibleDocuments.length} tài liệu`;
  $("#dashboard-topics").innerHTML = data.weakTopics
    .slice(0, 3)
    .map(topicMarkup)
    .join("");
  const supportedTopics = data.weakTopics.filter((topic) => topic.attempts >= 2);
  $("#analytics-topics").innerHTML = supportedTopics.map(topicMarkup).join("");
  $("#enough-topics-count").textContent = supportedTopics.length;
  $("#insufficient-topics-banner").hidden = supportedTopics.length === data.weakTopics.length;
  $("#priority-topics").innerHTML = data.weakTopics
    .filter((topic) => topic.score < 60 && topic.attempts >= 2)
    .map(
      (topic) =>
        `<div class="priority-card"><span class="status-badge failed">${topic.priority}</span><strong>${topic.name}</strong><p>${topic.reason}</p><button class="ghost-btn" data-screen="screen-quiz">Tạo Quiz ôn tập</button><button class="panel-link" data-screen="screen-qa">Đọc ${topic.page} →</button></div>`,
    )
    .join("");
  $("#recommendation-list").innerHTML = data.recommendations
    .map((recommendation) => {
      const documentItem = data.documents.find(
        (item) => item.id === recommendation.documentId,
      );
      return `<article class="recommendation-card">
        <span class="context-tag${documentItem ? "" : " teal-tag"}">${documentItem ? `Tài liệu liên quan: ${documentItem.title}` : "Chưa có tài liệu liên quan"}</span>
        <h2>${recommendation.title}</h2>
        <p>${documentItem ? recommendation.reason : "Bạn chưa có tài liệu về chủ đề này."}</p>
        ${documentItem ? `<small>Nguồn: ${documentItem.title} · Trang ${recommendation.pageRange} · ${documentItem.meta}</small>` : ""}
        <div>${documentItem ? '<button class="ghost-btn" data-screen="screen-materials">Mở tài liệu</button>' : '<button class="primary-btn" data-action="upload">Tải thêm</button>'}
          <button class="primary-btn" data-screen="screen-quiz">Bắt đầu học →</button>
        </div>
      </article>`;
    })
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
  $("#quiz-options").innerHTML =
    question.type === "fill-blank"
      ? '<label class="fill-answer">Câu trả lời<input id="fill-answer" type="text" autocomplete="off" placeholder="Nhập câu trả lời" /></label>'
      : question.options
          .map(
            (option, index) =>
              `<label class="option"><input type="radio" name="quiz-answer" value="${index}" /><b>${String.fromCharCode(65 + index)}</b><span>${option}</span></label>`,
          )
          .join("");
  $("#quiz-feedback").textContent = "Chọn một đáp án để tiếp tục.";
  $("#next-question").textContent =
    questionIndex === data.quizQuestions.length - 1
      ? "Nộp bài"
      : "Câu tiếp theo →";
  $("#next-question").disabled = true;
  $("#quiz-result").classList.add("hidden");
  $("#skip-question").disabled = false;
}

function openQuizSetup() {
  const availableDocuments = data.documents.filter(
    (item) => item.status === "Sẵn sàng",
  );
  if (!availableDocuments.length) {
    showStateAlert(
      "Nội dung không đủ để tạo Quiz/Q&A",
      "Chọn tài liệu đã xử lý thành công để tạo bài luyện tập.",
    );
    return;
  }
  $("#quiz-dialog").showModal();
}

function finishQuiz() {
  $("#result-score").textContent =
    `${Math.round((score / data.quizQuestions.length) * 100)}%`;
  $("#result-correct").textContent = `${score}/${data.quizQuestions.length}`;
  $("#quiz-result").classList.remove("hidden");
  $("#quiz-result").classList.add("block");
  $("#quiz-question").textContent = "Bạn đã hoàn thành bài quiz.";
  $("#quiz-options").innerHTML = "";
  $("#next-question").disabled = true;
  $("#skip-question").disabled = true;
  $("#result-skipped").hidden = skippedCount === 0;
  $("#result-skipped").textContent = `Bỏ qua: ${skippedCount} câu`;
  if (isLoggedIn) {
    $("#result-save-status").hidden = false;
    $("#result-save-status").className = "status-badge processing";
    $("#result-save-status").textContent = "Đang lưu...";
    $("#result-save-message").textContent = "Kết quả đang được lưu tự động.";
    setTimeout(() => {
      $("#result-save-status").className = "status-badge ready";
      $("#result-save-status").textContent = "Đã lưu";
      $("#result-save-message").textContent =
        "AI đã lưu giải thích và citation cho từng câu trả lời.";
    }, 700);
  } else {
    $("#result-save-status").hidden = true;
    $("#result-save-message").textContent =
      "⚠️ Kết quả không được lưu vì bạn chưa đăng nhập";
  }
}

function showStateAlert(title, message) {
  $("#state-dialog-title").textContent = title;
  $("#state-dialog-message").textContent = message;
  $("#state-dialog").showModal();
}

function isAnswerCorrect(question) {
  if (question.type === "fill-blank") {
    return $("#fill-answer").value.trim().toLocaleLowerCase("vi") ===
      question.answer.toLocaleLowerCase("vi");
  }
  return Number($("input[name='quiz-answer']:checked")?.value) === question.answer;
}

function advanceQuiz() {
  if (questionIndex < data.quizQuestions.length - 1) {
    questionIndex += 1;
    renderQuestion();
  } else {
    finishQuiz();
  }
}

document.addEventListener("click", (event) => {
  const authOpen = event.target.closest("[data-auth-open]");
  if (authOpen) toggleAuthTab(authOpen.dataset.authOpen);

  const screenTrigger = event.target.closest("[data-screen]");
  if (screenTrigger) {
    const dialog = screenTrigger.closest("dialog");
    if (dialog) dialog.close();
    navigateTo(screenTrigger.dataset.screen);
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "logout") {
    isLoggedIn = false;
    localStorage.setItem("notewise.isLoggedIn", "false");
    renderLists();
    updateAuthUI();
    navigateTo("screen-dashboard");
  }
  if (action === "session-expired") {
    isLoggedIn = false;
    localStorage.setItem("notewise.isLoggedIn", "false");
    renderLists();
    updateAuthUI();
    navigateTo("screen-dashboard");
    showStateAlert(
      "Phiên làm việc hết hạn",
      "Bạn đã được chuyển về chế độ Khách. Đăng nhập để tiếp tục lưu tiến độ.",
    );
  }
  if (action === "upload") {
    if (!isLoggedIn) {
      toggleAuthTab("login");
      navigateTo("screen-auth");
      return;
    }
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
    skippedCount = 0;
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

  if (
    event.target.closest("#next-question") &&
    !event.target.closest("#next-question").disabled
  ) {
    if (isAnswerCorrect(data.quizQuestions[questionIndex])) score += 1;
    advanceQuiz();
  }

  if (event.target.closest("#skip-question")) {
    skippedCount += 1;
    advanceQuiz();
  }

  if (event.target.closest("#start-quiz")) {
    const selectedDocument = data.documents.find(
      (item) => item.id === $("#quiz-source").value,
    );
    $("#quiz-dialog").close();
    if (!selectedDocument || selectedDocument.status !== "Sẵn sàng") {
      showStateAlert(
        "Nội dung không đủ để tạo Quiz/Q&A",
        "Tài liệu này chưa sẵn sàng hoặc không có đủ nội dung để tạo Quiz.",
      );
      return;
    }
    questionIndex = 0;
    score = 0;
    skippedCount = 0;
    navigateTo("screen-quiz");
  }
});

document.addEventListener("change", (event) => {
  if (event.target.matches('input[name="quiz-answer"]')) {
    $$(".option").forEach((item) => item.classList.remove("selected"));
    event.target.closest(".option").classList.add("selected");
    $("#next-question").disabled = false;
    $("#quiz-feedback").textContent = isAnswerCorrect(
      data.quizQuestions[questionIndex],
    )
      ? "Chính xác. Bạn có thể đi tiếp."
      : "Chưa đúng. Xem giải thích sau khi hoàn thành.";
  }
  if (event.target.id === "material-status-filter") filterDocuments();
});

document.addEventListener("input", (event) => {
  if (event.target.id === "fill-answer") {
    $("#next-question").disabled = !event.target.value.trim();
  }
});

$("#qa-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("#qa-question").value.trim();
  showStateAlert(
    question
      ? "Đầu ra AI không hợp lệ"
      : "Nội dung không đủ để tạo Quiz/Q&A",
    question
      ? "AI trả về nội dung không đúng định dạng. Hãy thử lại sau."
      : "Nhập câu hỏi hoặc chọn tài liệu có đủ nội dung để tiếp tục.",
  );
});

function filterDocuments() {
  const selectedStatus = $("#material-status-filter").value;
  $$("#all-documents .document").forEach((row) => {
    row.hidden =
      (selectedStatus !== "Tất cả trạng thái" &&
        row.querySelector(".status-badge").textContent !== selectedStatus) ||
      !row.textContent.toLowerCase().includes($("#material-search").value.toLowerCase());
  });
}

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-reader-tab]");
  if (tab) {
    $$("[data-reader-tab]").forEach((item) =>
      item.classList.toggle("active", item === tab),
    );
    $("#source-content").hidden = tab.dataset.readerTab !== "source";
    $("#summary-content").hidden = tab.dataset.readerTab !== "summary";
  }
  const authTab = event.target.closest("[data-auth-tab]");
  if (authTab) {
    toggleAuthTab(authTab.dataset.authTab);
  }
});

$("#auth-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const register = !$("#auth-confirm").closest(".register-only").hidden;
  $("#email-error").textContent = $("#auth-email").value.includes("@")
    ? ""
    : "Email chưa hợp lệ.";
  $("#password-error").textContent =
    $("#auth-password").value.length >= 6
      ? ""
      : "Mật khẩu cần ít nhất 6 ký tự.";
  $("#confirm-error").textContent =
    register && $("#auth-confirm").value !== $("#auth-password").value
      ? "Mật khẩu xác nhận không khớp."
      : "";
  if (
    !$("#email-error").textContent &&
    !$("#password-error").textContent &&
    !$("#confirm-error").textContent
  ) {
    isLoggedIn = true;
    localStorage.setItem("notewise.isLoggedIn", "true");
    renderLists();
    updateAuthUI();
    navigateTo("screen-dashboard");
  }
});

$$("[data-toggle-password]").forEach((button) =>
  button.addEventListener("click", () => {
    const input = $("#auth-password");
    input.type = input.type === "password" ? "text" : "password";
    button.textContent = input.type === "password" ? "Hiện" : "Ẩn";
  }),
);

$("#material-search").addEventListener("input", (event) =>
  filterDocuments(),
);

renderLists();
renderQuestion();
updateAuthUI();
toggleAuthTab("login");
navigateTo("screen-dashboard");
