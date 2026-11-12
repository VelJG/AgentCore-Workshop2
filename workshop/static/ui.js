const form = document.querySelector("#chat-form");
const input = document.querySelector("#message");
const send = document.querySelector("#send");
const messages = document.querySelector("#messages");
const status = document.querySelector("#service-status");
let busy = false;

function bubble(role, content, source, agent, citations) {
  const item = document.createElement("div");
  item.className = `bubble ${role}`;
  const heading = document.createElement("span");
  heading.className = "meta";
  const labels = { qa: "Q&A Agent", ticket: "Ticket Agent", research: "Research Agent" };
  heading.textContent = role === "user" ? "Bạn" : (labels[agent] || "Trợ lý");
  item.append(heading, document.createTextNode(content));
  if (source && source.length) {
    const label = document.createElement("span");
    label.className = "source";
    label.textContent = `Nguồn: ${source.join(", ")}`;
    item.append(label);
  }
  if (citations && citations.length) {
    const label = document.createElement("span");
    label.className = "source";
    label.append(document.createTextNode("Nguồn web: "));
    let linked = 0;
    citations.slice(0, 5).forEach(citation => {
      try {
        const url = new URL(citation.url);
        if (url.protocol !== "https:") return;
        if (linked++) label.append(document.createTextNode(" · "));
        const link = document.createElement("a");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = citation.title || url.hostname;
        label.append(link);
      } catch { /* Skip malformed source URLs. */ }
    });
    item.append(label);
  }
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}

function setBusy(value) {
  busy = value;
  send.disabled = value;
  input.disabled = value;
  document.querySelectorAll(".example").forEach(button => { button.disabled = value; });
}

async function post(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let result;
  try { result = await response.json(); }
  catch { throw new Error(`Máy chủ trả về phản hồi không hợp lệ (HTTP ${response.status}).`); }
  if (!response.ok) {
    throw new Error(typeof result.detail === "string" ? result.detail : `Yêu cầu thất bại (HTTP ${response.status}).`);
  }
  return result;
}

async function decide(id, approve, buttons, card) {
  buttons.forEach(button => { button.disabled = true; });
  try {
    const result = await post(`/approvals/${encodeURIComponent(id)}`, { approve });
    if (result.status === "approved") {
      bubble("assistant", `Đã phê duyệt. Phiếu ${result.ticket_id} được tạo với trạng thái Pending.`);
    } else {
      bubble("assistant", "Đã từ chối. Không có phiếu nào được tạo.");
    }
    card.remove();
  } catch (error) {
    bubble("assistant", `Không thể hoàn tất quyết định: ${error.message}`);
    buttons.forEach(button => { button.disabled = false; });
  }
}

function approvalCard(result) {
  const card = bubble("assistant", `Đề xuất tạo phiếu: ${result.draft.content}\nChưa có phiếu nào được tạo. Bạn có phê duyệt không?`, null, "ticket");
  const actions = document.createElement("div");
  actions.className = "actions";
  const approve = document.createElement("button");
  approve.type = "button";
  approve.textContent = "Phê duyệt";
  const deny = document.createElement("button");
  deny.type = "button";
  deny.className = "secondary";
  deny.textContent = "Từ chối";
  actions.append(approve, deny);
  card.append(actions);
  const buttons = [approve, deny];
  approve.addEventListener("click", () => decide(result.approval_id, true, buttons, card));
  deny.addEventListener("click", () => decide(result.approval_id, false, buttons, card));
}

async function sendMessage(message) {
  if (busy || !message.trim()) return;
  const trimmed = message.trim();
  bubble("user", trimmed);
  input.value = "";
  setBusy(true);
  try {
    const result = await post("/chat", { message: trimmed });
    if (result.kind === "approval_required") approvalCard(result);
    else if (result.kind === "answer") bubble("assistant", result.answer, result.sources, result.agent, result.citations);
    else throw new Error("Máy chủ trả về loại phản hồi không hợp lệ.");
  } catch (error) {
    bubble("assistant", `Không thể gửi tin nhắn: ${error.message}`);
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
document.querySelectorAll(".example").forEach(button => {
  button.addEventListener("click", () => sendMessage(button.dataset.message));
});
fetch("/health").then(response => {
  if (!response.ok) throw new Error("Health check failed");
  return response.json();
}).then(() => {
  status.textContent = "AI thật · local";
}).catch(() => { status.textContent = "Máy chủ chưa sẵn sàng"; });
