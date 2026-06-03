const state = {
  busy: false,
  messages: [],
  calls: [],
};

const els = {
  simulate: document.querySelector("#simulate-user"),
  form: document.querySelector("#debug-user-form"),
  input: document.querySelector("#debug-user-input"),
  send: document.querySelector("#debug-user-send"),
  transcript: document.querySelector("#debug-transcript"),
  conversationCount: document.querySelector("#conversation-count"),
  historyMeta: document.querySelector("#history-meta"),
  runningNotes: document.querySelector("#running-notes"),
  assessmentList: document.querySelector("#assessment-list"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

function formatDate(value) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function setBusy(value) {
  state.busy = value;
  els.simulate.disabled = value;
  els.input.disabled = value;
  els.send.disabled = value;
  els.simulate.textContent = value ? "Running..." : "Simulate user response";
}

function renderHistory(history) {
  els.historyMeta.innerHTML = "";
  const rows = [
    ["Title", history.title],
    ["History ID", history.id],
    ["Created", formatDate(history.created_at)],
    ["Updated", formatDate(history.updated_at)],
  ];

  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    els.historyMeta.append(term, description);
  }
}

function renderTranscript(messages) {
  state.messages = messages;
  els.transcript.innerHTML = "";
  els.conversationCount.textContent = `${messages.length} ${messages.length === 1 ? "message" : "messages"}`;

  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "debug-empty";
    empty.textContent = "No debug conversation yet. Use the simulate button to generate an opening user message.";
    els.transcript.append(empty);
    return;
  }

  for (let index = 0; index < messages.length; index += 1) {
    const message = messages[index];
    const article = document.createElement("article");
    article.className = `debug-turn ${message.role}`;

    const label = document.createElement("div");
    label.className = "debug-turn-label";
    label.textContent = message.role === "assistant" ? "Therapist" : "User";

    const content = document.createElement("p");
    content.textContent = message.content;

    const time = document.createElement("time");
    time.textContent = formatDate(message.created_at);

    article.append(label, content, time);
    if (message.role === "assistant") {
      const previousUser = findPreviousUserMessage(messages, index);
      const responseCall = previousUser
        ? callsForMessage(previousUser.id).find((call) => call.kind === "therapist_response")
        : null;
      if (responseCall) {
        article.classList.add("clickable");
        article.addEventListener("click", () => openCallModal("Therapist response", responseCall));
      }
    }
    els.transcript.append(article);

    if (message.role === "user") {
      renderCallStrip(message.id);
    }
  }
}

function findPreviousUserMessage(messages, index) {
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    if (messages[cursor].role === "user") return messages[cursor];
  }
  return null;
}

function callsForMessage(messageId) {
  return state.calls.filter((call) => call.message_id === messageId);
}

function formatCallKind(kind) {
  return kind.replace("assessment:", "").replaceAll("_", " ");
}

function renderCallStrip(messageId) {
  const assessmentCalls = callsForMessage(messageId).filter((call) => call.kind.startsWith("assessment:"));
  if (!assessmentCalls.length) return;

  const strip = document.createElement("div");
  strip.className = "debug-call-strip";
  for (const call of assessmentCalls) {
    const button = document.createElement("button");
    button.className = "debug-call-chip";
    button.type = "button";
    button.textContent = formatCallKind(call.kind);
    button.addEventListener("click", () => openCallModal(formatCallKind(call.kind), call));
    strip.append(button);
  }
  els.transcript.append(strip);
}

function openCallModal(title, call) {
  const existing = document.querySelector(".debug-call-modal");
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.className = "debug-call-modal";

  const dialog = document.createElement("section");
  dialog.className = "debug-call-dialog";

  const header = document.createElement("header");
  const heading = document.createElement("h2");
  const close = document.createElement("button");
  heading.textContent = title;
  close.type = "button";
  close.textContent = "Close";
  close.addEventListener("click", () => overlay.remove());
  header.append(heading, close);

  const requestPanel = document.createElement("article");
  const requestTitle = document.createElement("h3");
  const requestBody = document.createElement("pre");
  requestTitle.textContent = "LLM call";
  requestBody.textContent = call.request_json;
  requestPanel.append(requestTitle, requestBody);

  const responsePanel = document.createElement("article");
  const responseTitle = document.createElement("h3");
  const responseBody = document.createElement("pre");
  responseTitle.textContent = "LLM response";
  responseBody.textContent = call.response;
  responsePanel.append(responseTitle, responseBody);

  const body = document.createElement("div");
  body.className = "debug-call-modal-body";
  body.append(requestPanel, responsePanel);

  dialog.append(header, body);
  overlay.append(dialog);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) overlay.remove();
  });
  document.body.append(overlay);
}

function renderAssessments(assessments) {
  els.assessmentList.innerHTML = "";
  if (!assessments.length) {
    const empty = document.createElement("div");
    empty.className = "debug-empty";
    empty.textContent = "No assessments have been generated yet.";
    els.assessmentList.append(empty);
    return;
  }

  for (const assessment of assessments.slice().reverse()) {
    const item = document.createElement("article");
    item.className = "assessment-item";

    const title = document.createElement("h3");
    title.textContent = assessment.kind.replaceAll("_", " ");

    const content = document.createElement("p");
    content.textContent = assessment.content;

    const time = document.createElement("time");
    time.textContent = formatDate(assessment.created_at);

    item.append(title, content, time);
    els.assessmentList.append(item);
  }
}

async function loadDebugHistory() {
  const data = await api("/api/debug/history");
  state.calls = data.llm_calls || [];
  renderHistory(data.history);
  renderTranscript(data.messages);
  els.runningNotes.textContent = data.history.notes || "(none)";
  renderAssessments(data.assessments);
}

async function simulateUserResponse() {
  if (state.busy) return;
  try {
    setBusy(true);
    const baseMessages = state.messages;
    renderTranscript([
      ...baseMessages,
      { role: "user", content: "Simulating user response...", created_at: new Date().toISOString() },
    ]);

    const simulated = await api("/api/debug/history/simulate-user", {
      method: "POST",
      body: "{}",
    });
    renderTranscript([
      ...baseMessages,
      { role: "user", content: simulated.content, created_at: new Date().toISOString() },
      { role: "assistant", content: "...", created_at: new Date().toISOString() },
    ]);

    await sendDebugUserMessage(simulated.content, false);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function sendDebugUserMessage(content, renderPending = true) {
  if (renderPending) {
    renderTranscript([
      ...state.messages,
      { role: "user", content, created_at: new Date().toISOString() },
      { role: "assistant", content: "...", created_at: new Date().toISOString() },
    ]);
  }

  await api("/api/debug/history/messages", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  await loadDebugHistory();
}

async function submitDebugUserMessage(event) {
  event.preventDefault();
  if (state.busy) return;

  const content = els.input.value.trim();
  if (!content) return;

  try {
    setBusy(true);
    els.input.value = "";
    await sendDebugUserMessage(content);
  } catch (error) {
    alert(error.message);
  } finally {
    setBusy(false);
  }
}

async function boot() {
  els.simulate.addEventListener("click", simulateUserResponse);
  els.form.addEventListener("submit", submitDebugUserMessage);
  els.input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    els.form.requestSubmit();
  });
  try {
    await loadDebugHistory();
  } catch (error) {
    alert(error.message);
  }
}

boot();
