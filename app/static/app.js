"use strict";

let current = null;      // объект шага из /api/step
let timerHandle = null;
let elapsedBase = 0;     // секунды, накопленные до текущего отрезка
let runningSince = null; // момент старта отрезка в браузере
let history = [];        // история чата — только в памяти вкладки

const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const opts = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function esc(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

/* ------------------------------------------------------------- дерево */

async function loadTree() {
  const data = await api("/api/tree");
  const box = $("tree-body");
  box.innerHTML = "";
  for (const mod of data.modules) {
    const el = document.createElement("div");
    el.className = "mod";
    const head = document.createElement("div");
    head.className = "mod-head";
    head.innerHTML = `<span>${esc(mod.module)}</span><span class="mod-count">${mod.done}/${mod.total}</span>`;
    el.appendChild(head);
    const list = document.createElement("div");
    list.hidden = true;
    for (const st of mod.steps) {
      const a = document.createElement("div");
      a.className = "step-link" + (st.declaration ? " decl" : "") +
        (st.status === "done" ? " done" : "") + (st.status === "running" ? " running" : "");
      a.dataset.id = st.step_id;
      const marks = (st.has_checks ? '<span class="badge" title="есть скрипт проверки">▣</span>' : "") +
        (st.deferred ? '<span class="badge" title="отложенный ручной прогон">△</span>' : "");
      a.innerHTML = esc(st.title) + marks;
      a.onclick = () => openStep(st.module, st.number);
      list.appendChild(a);
    }
    head.onclick = () => { list.hidden = !list.hidden; };
    if (current && current.module === mod.module) list.hidden = false;
    el.appendChild(list);
    box.appendChild(el);
  }
  if (!data.assistant) {
    $("chat-log").innerHTML =
      '<div class="msg ai">Ключ не найден: заполните <code>app/.env</code> по образцу <code>app/.env.example</code>.</div>';
  }
}

/* --------------------------------------------------------------- шаг */

async function openStep(module, number) {
  current = await api(`/api/step/${module}/${number}`);
  history = [];
  $("chat-log").innerHTML = "";
  $("step-empty").hidden = true;
  $("step-body").hidden = false;
  $("step-title").textContent = current.title;

  const h = current.header;
  $("step-meta").innerHTML = ["Умение", "Модуль", "Требуется до этого", "Время"]
    .filter((k) => h[k])
    .map((k) => `<b>${k}:</b> ${esc(h[k])}`).join(" &nbsp;·&nbsp; ") +
    ` &nbsp;·&nbsp; <code>${esc(current.rel_path)}</code>`;

  $("deferred").innerHTML = current.deferred.map((d) => `
    <div class="deferred-row">
      <div class="head">Отложенный ручной прогон — ${esc(d.section)}${d.scope === "step" ? " (этот шаг)" : ""}</div>
      <div>${esc(d.what)}</div>
      <div class="warn">Вердикт ИИ по критерию реального прогона на Desktop / Tableau / Looker не заменяет.</div>
    </div>`).join("");

  renderChecks();
  $("verdict-panel").hidden = !current.has_criterion;
  $("verdict-out").innerHTML = "";
  $("v-answer").value = "";
  $("step-html").innerHTML = current.html;

  applyState(current.state);
  document.querySelectorAll(".step-link").forEach((n) =>
    n.classList.toggle("active", n.dataset.id === current.step_id));
  $("step").scrollTop = 0;
}

/* ---------------------------------------------------------- проверки */

function renderChecks() {
  const box = $("checks");
  if (!current.checks.length) {
    box.innerHTML = '<h3>Проверка</h3><p class="hint">В этом шаге нет команды <code>check_*.py</code> — критерий проверяется иначе (см. раздел 1.5).</p>';
    return;
  }
  box.innerHTML = "<h3>Проверка</h3>" + current.checks.map((c, i) => `
    <div class="check">
      <div class="cmd">${esc(c.raw)}${c.cwd ? ` <span class="hint">(из ${esc(c.cwd)})</span>` : ""}</div>
      <button data-check="${i}">Проверить</button>
      <div id="check-out-${i}"></div>
    </div>`).join("");
  box.querySelectorAll("button[data-check]").forEach((b) => {
    b.onclick = () => runCheck(Number(b.dataset.check), b);
  });
}

async function runCheck(index, btn) {
  const out = $(`check-out-${index}`);
  btn.disabled = true;
  out.innerHTML = '<p class="hint">выполняется…</p>';
  try {
    const r = await api("/api/check/run", { step_id: current.step_id, index });
    const body = [r.stdout, r.stderr].filter(Boolean).join("\n");
    const painted = esc(body)
      .replace(/\[OK\]/g, '<span class="ok">[OK]</span>')
      .replace(/\[FAIL\]/g, '<span class="fail">[FAIL]</span>');
    out.innerHTML =
      `<div><span class="tag script">РЕЗУЛЬТАТ СКРИПТА</span> код возврата ${r.returncode}` +
      (r.error ? ` — ${esc(r.error)}` : "") + `</div>` +
      `<div class="cmd">${esc(r.command)} &nbsp;(cwd: ${esc(r.cwd)})</div>` +
      `<pre class="out">${painted || "(пустой вывод)"}</pre>`;
  } catch (e) {
    out.innerHTML = `<p class="fail">${esc(e.message)}</p>`;
  } finally {
    btn.disabled = false;
  }
}

/* ----------------------------------------------------------- таймер */

function fmt(sec) {
  const s = Math.max(0, Math.floor(sec));
  const p = (n) => String(n).padStart(2, "0");
  return `${p(Math.floor(s / 3600))}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)}`;
}

function currentSeconds() {
  return elapsedBase + (runningSince ? (Date.now() - runningSince) / 1000 : 0);
}

function tick() { $("timer").textContent = fmt(currentSeconds()); }

function applyState(st) {
  elapsedBase = st.elapsed_sec || 0;
  runningSince = st.status === "running" ? Date.now() : null;
  if (timerHandle) clearInterval(timerHandle);
  timerHandle = setInterval(tick, 1000);
  tick();

  const running = st.status === "running";
  const done = st.status === "done";
  $("btn-start").hidden = running || done;
  $("btn-start").textContent = st.status === "paused" ? "Продолжил" : "Начал";
  $("btn-pause").hidden = !running;
  $("btn-finish").hidden = done || st.status === "not_started";
  $("btn-reopen").hidden = !done;
  $("finish-form").hidden = true;
  $("session-status").textContent = {
    not_started: "не начат", running: "идёт", paused: "пауза", done: "закончен",
  }[st.status] || "";
}

$("btn-start").onclick = async () => applyState(await api("/api/session/start", { step_id: current.step_id }));
$("btn-pause").onclick = async () => applyState(await api("/api/session/pause", { step_id: current.step_id }));
$("btn-reopen").onclick = async () => applyState(await api("/api/session/reopen", { step_id: current.step_id }));
$("btn-cancel").onclick = () => { $("finish-form").hidden = true; };

$("btn-finish").onclick = () => {
  const fact = Math.floor(currentSeconds() / 900) * 0.25;
  $("f-theme").value = `${current.module}.${String(current.number).padStart(2, "0")} ${current.title}`;
  $("f-plan").value = current.plan_hours;
  $("f-fact").value = String(fact);
  $("f-notes").innerHTML = (current.state.notes || []).length
    ? '<p class="hint">В «Где застрял» будут дописаны пометки правила 6:<br>' +
      current.state.notes.map(esc).join("<br>") + "</p>"
    : "";
  $("finish-form").hidden = false;
};

$("btn-write").onclick = async () => {
  const r = await api("/api/session/finish", {
    step_id: current.step_id,
    theme: $("f-theme").value,
    plan: $("f-plan").value,
    stuck: $("f-stuck").value,
    useless: $("f-useless").value,
  });
  $("journal-tail").hidden = false;
  $("journal-tail").textContent = "research/self.md, последние строки:\n" + r.tail.join("\n");
  $("f-stuck").value = "";
  $("f-useless").value = "";
  current.state = r.state;
  applyState(r.state);
  await loadTree();
};

/* ---------------------------------------------------------- вердикт */

$("btn-verdict").onclick = async () => {
  const out = $("verdict-out");
  out.innerHTML = '<p class="hint">ассистент сверяет ответ с 1.5 и 1.6…</p>';
  try {
    const v = await api("/api/assistant/verdict", {
      step_id: current.step_id,
      task: $("v-task").value,
      answer: $("v-answer").value,
    });
    const list = (title, items) => items && items.length
      ? `<h4>${title}</h4><ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "";
    out.innerHTML = `
      <div class="verdict">
        <div><span class="tag ai">ВЕРДИКТ ИИ ПО КРИТЕРИЮ 1.5 — НЕ РЕЗУЛЬТАТ СКРИПТА</span></div>
        <h4>Вердикт: ${esc(v.verdict)}</h4>
        <p>${esc(v.explanation)}</p>
        ${list("Закрыто по 1.5", v.matched)}
        ${list("Не закрыто по 1.5", v.missing)}
        ${list("Попадание в 1.6 «Типичные ошибки»", v.errors_hit)}
        <p class="hint">${esc(v.source)}. Ручной прогон инструмента не заменяет.</p>
        <p class="hint">В журнал: ${esc(v.note)}</p>
      </div>`;
    current.state = await api(`/api/step/${current.module}/${current.number}`).then((s) => s.state);
  } catch (e) {
    out.innerHTML = `<p class="fail">${esc(e.message)}</p>`;
  }
};

/* -------------------------------------------------------------- чат */

$("btn-ask").onclick = async () => {
  const q = $("chat-input").value.trim();
  if (!q || !current) return;
  $("chat-input").value = "";
  const log = $("chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="msg you">${esc(q)}</div>`);
  const pending = document.createElement("div");
  pending.className = "msg ai";
  pending.textContent = "…";
  log.appendChild(pending);
  try {
    const r = await api("/api/assistant/ask", { step_id: current.step_id, question: q, history });
    history.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
    pending.innerHTML = esc(r.answer) +
      `<span class="note">в журнал: ${esc(r.note)}</span>`;
    const s = await api(`/api/step/${current.module}/${current.number}`);
    current.state = s.state;
  } catch (e) {
    pending.textContent = e.message;
  }
  log.scrollTop = log.scrollHeight;
};

loadTree();
