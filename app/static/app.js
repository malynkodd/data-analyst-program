"use strict";

let tree = null;         // ответ /api/tree
let current = null;      // ответ /api/step для открытого шага
let timerHandle = null;
let elapsedBase = 0;
let runningSince = null;
let chatHistory = [];    // история чата — только в памяти вкладки

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

const esc = (s) => String(s == null ? "" : s)
  .replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const STATUS_TEXT = { not_started: "не начат", running: "идёт", paused: "пауза", done: "закончен" };

/* Экраны: показан ровно один. Скрытие — только атрибутом `hidden`
   (в CSS он объявлен сильнее любого display). */
const SCREENS = ["home", "step-body", "module-body", "skills-body", "journal-body"];
const NAV_OF = { home: "home", "skills-body": "skills", "journal-body": "journal" };

function showScreen(id) {
  SCREENS.forEach((s) => { $(s).hidden = s !== id; });
  document.querySelectorAll(".topnav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.screen === NAV_OF[id]));
  $("step").scrollTop = 0;
}

/* ==================================================================
   ДЕРЕВО — порядок прохождения по шести этапам части 6.2 blueprint
   ================================================================== */

async function loadTree(keepOpen) {
  tree = await api("/api/tree");
  renderTree();
  renderHome();
  const pct = tree.total ? Math.round((tree.done / tree.total) * 100) : 0;
  $("top-bar").style.width = pct + "%";
  $("top-count").textContent = `${tree.done} из ${tree.total} шагов`;
  if (!tree.assistant) {
    $("chat-hint").innerHTML =
      'Ключ не найден — чат и вердикт ИИ выключены. Заполните <code>app/.env</code> ' +
      'по образцу <code>app/.env.example</code> и перезапустите приложение. ' +
      'Всё остальное работает и без ключа.';
    $("chat-hint").classList.add("fail");
  }
  if (keepOpen) highlightActive();
}

function renderTree() {
  const filter = $("tree-filter").value.trim().toLowerCase();
  const box = $("tree-body");
  box.innerHTML = "";
  box.classList.remove("loading");

  for (const stage of tree.stages) {
    const modules = stage.modules
      .map((mod) => ({ mod, steps: mod.steps.filter((s) => matches(s, mod, filter)) }))
      .filter((x) => x.steps.length);
    if (!modules.length) continue;

    const el = document.createElement("div");
    el.className = "stage";
    el.innerHTML =
      `<div class="stage-head"><span><span class="n">Этап ${stage.number}</span> ${esc(stage.name)}</span>` +
      `<span title="часы по blueprint 6.2">${esc(stage.hours)} ч</span></div>`;

    for (const { mod, steps } of modules) {
      const m = document.createElement("div");
      m.className = "mod";
      const complete = mod.total && mod.done === mod.total ? " complete" : "";
      m.innerHTML =
        `<div class="mod-head${complete}" title="${esc(mod.kind)} · ${esc(mod.hours)} ч">` +
        `<span class="code">${esc(mod.module)}</span>` +
        `<span class="name">${esc(mod.name)}</span>` +
        `<span class="count">${mod.done}/${mod.total}</span></div>`;
      const list = document.createElement("div");
      list.className = "mod-steps";
      list.hidden = !filter && !(current && current.module === mod.module);

      for (const st of steps) {
        const a = document.createElement("div");
        a.className = "step-link" + (st.declaration ? " decl" : "") +
          (st.status === "done" ? " done" : "") + (st.status === "running" ? " running" : "");
        a.dataset.id = st.step_id;
        a.title = st.full_title;
        const marks = (st.has_checks ? '<span class="badge" title="есть проверка скриптом">▣</span>' : "") +
          (st.deferred ? '<span class="badge" title="нужен ручной прогон на настоящем инструменте">△</span>' : "");
        const label = st.declaration ? "Декларация модуля — служебное, можно пропустить" : st.title;
        a.innerHTML = `<span class="num">${st.declaration ? "—" : String(st.number).padStart(2, "0")}</span>` +
          `<span class="t">${esc(label)}</span>${marks}`;
        a.onclick = () => openStep(st.module, st.number);
        list.appendChild(a);
      }
      m.querySelector(".mod-head").onclick = () => {
        list.hidden = false;
        openModule(mod.module);
      };
      m.appendChild(list);
      el.appendChild(m);
    }
    box.appendChild(el);
  }
  if (!box.children.length) box.innerHTML = '<p class="hint">Ничего не найдено.</p>';
  highlightActive();
}

function matches(step, mod, filter) {
  if (!filter) return true;
  return (step.full_title + " " + mod.module + " " + mod.name + " " + step.skill)
    .toLowerCase().includes(filter);
}

function highlightActive() {
  document.querySelectorAll(".step-link").forEach((n) =>
    n.classList.toggle("active", !!current && n.dataset.id === current.step_id));
}

$("tree-filter").oninput = () => renderTree();

/* ==================================================================
   СТАРТОВЫЙ ЭКРАН
   ================================================================== */

function renderHome() {
  const n = tree.next_step;
  $("home-next").innerHTML = n
    ? `<div class="label">${tree.done ? "Продолжить здесь" : "Начать здесь"}</div>
       <h3>${esc(n.module)}.${String(n.number).padStart(2, "0")} — ${esc(n.title)}</h3>
       <div class="meta">${esc(n.module_name)} · этап «${esc(n.stage)}» · ${esc(n.plan_hours)} ч
         ${n.status === "paused" ? " · сессия на паузе" : ""}</div>
       <button class="primary" id="btn-go">Открыть шаг</button>`
    : `<div class="label">Программа пройдена</div>
       <h3>Все ${tree.total} шагов закрыты</h3>
       <div class="meta">Журнал прохождения — <code>research/self.md</code>.</div>`;
  if (n) $("btn-go").onclick = () => openStep(n.module, n.number);

  const rows = tree.stages.map((s) => {
    const cur = tree.next_step && s.modules.some((m) => m.module === tree.next_step.module);
    return `<tr class="${cur ? "current" : ""}">
      <td><b>${s.number}. ${esc(s.name)}</b></td>
      <td>${s.modules.map((m) => esc(m.module)).join(", ")}</td>
      <td>${esc(s.hours)} ч</td>
      <td>${s.done}/${s.total}</td></tr>`;
  }).join("");
  $("home-stages").innerHTML =
    `<h2>Шесть этапов</h2>
     <p class="hint">Порядок и часы — из <code>design/blueprint.md</code>, часть 6.2.
       Недели: при 10 ч/нед — вся программа 43–56, при 25 ч/нед — 18–23.</p>
     <table class="stages"><tr><th>Этап</th><th>Что входит</th><th>Часы</th><th>Пройдено</th></tr>
     ${rows}</table>`;
}

/* ==================================================================
   ЭКРАН МОДУЛЯ — из его же step-00.md
   ================================================================== */

let currentModule = null;

async function openModule(code) {
  currentModule = await api(`/api/module/${code}`);
  const m = currentModule;
  showScreen("module-body");

  $("mod-crumbs").innerHTML = m.stage
    ? `Этап ${m.stage.number} · <b>${esc(m.stage.name)}</b> · ${esc(m.kind)}`
    : esc(m.kind);
  $("mod-title").textContent = `${m.module} — ${m.name}`;
  $("mod-chips").innerHTML =
    `<span class="chip strong">⏱ ${esc(m.hours)} ч на весь ${esc(m.kind)}</span>` +
    `<span class="chip">${m.total} шаг${m.total === 1 ? "" : "ов"}, закрыто ${m.done}</span>` +
    (m.skills.length ? `<span class="chip">умения: ${m.skills.map((s) => esc(s.id)).join(", ")}</span>` : "");

  $("mod-deferred").innerHTML = m.deferred.map((d) => `
    <div class="deferred-row">
      <div class="head">△ ${esc(d.section)}</div>
      <div>${esc(d.what)}</div>
      <div class="warn">Эти шаги делаются руками в настоящем приложении. Вердикт ИИ их не заменяет.</div>
    </div>`).join("");

  const nextStep = m.steps.find((st) => !st.declaration && st.status !== "done");
  $("mod-next").hidden = !nextStep;
  if (nextStep) {
    $("mod-next").innerHTML =
      `<div class="label">${m.done ? "Продолжить" : "Начать"} ${esc(m.module)}</div>
       <h3>${String(nextStep.number).padStart(2, "0")}. ${esc(nextStep.title)}</h3>
       <div class="meta">${esc(nextStep.plan_hours)} ч по плану${nextStep.skill ? " · умение " + esc(nextStep.skill.split(/[(—;]/)[0].trim()) : ""}</div>
       <button class="primary" id="mod-go">Открыть шаг</button>`;
    $("mod-go").onclick = () => openStep(m.module, nextStep.number);
  }

  $("mod-steps").innerHTML = m.steps.map((st) => `
    <div class="modstep ${st.declaration ? "decl" : ""} ${st.status === "done" ? "done" : ""}"
         data-n="${st.number}">
      <span class="n">${st.declaration ? "—" : String(st.number).padStart(2, "0")}</span>
      <span class="t">${esc(st.declaration ? "Справка модуля: датасет, схема, предусловие" : st.title)}</span>
      <span class="meta">${st.declaration ? "служебное" : esc(st.plan_hours) + " ч"}
        ${st.has_checks ? " ▣" : ""}${st.deferred ? " △" : ""}
        ${st.status === "done" ? " ✓" : ""}</span>
    </div>`).join("");
  $("mod-steps").querySelectorAll(".modstep").forEach((el) => {
    el.onclick = () => openStep(m.module, Number(el.dataset.n));
  });

  $("mod-skills").innerHTML = m.skills.length
    ? m.skills.map((sk) => skillCard(sk, [])).join("")
    : '<p class="hint">Инфраструктурный блок: своих умений части 1 blueprint у него нет.</p>';

  $("mod-decl").innerHTML = m.declaration_html;
  $("mod-decl-wrap").hidden = !m.has_declaration;
  renderTree();
}

/* ==================================================================
   КАРТА УМЕНИЙ
   ================================================================== */

function skillCard(sk, steps) {
  const links = (steps || []).map((st) =>
    `<a data-step="${esc(st.step_id)}" class="${st.done ? "done" : ""}">${esc(st.step_id)}${st.done ? " ✓" : ""}</a>`).join("");
  return `<div class="skill ${sk.done ? "done" : ""}">
    <div><span class="id">${esc(sk.id)}</span><span class="st">${esc(sk.statement)}</span></div>
    <div class="how"><b>Как проверяется:</b> ${esc(sk.check)}</div>
    ${links ? `<div class="steps">${links}</div>` : ""}
  </div>`;
}

async function openSkills() {
  const d = await api("/api/skills");
  showScreen("skills-body");
  $("skills-progress").innerHTML =
    `<div class="label">Закрыто умений</div><h3>${d.done} из ${d.total}</h3>
     <div class="meta">Умение закрыто, когда закрыты все шаги, которые его объявили.
       Отметку «закончил» ставите вы — приложение не знает, что сделано вне его.</div>`;
  $("skills-list").innerHTML = d.groups.map((g) => `
    <div class="skgroup">
      <h3>${esc(g.group)}. ${esc(g.name)}</h3>
      ${g.skills.map((sk) => skillCard(sk, sk.steps)).join("")}
    </div>`).join("");
  bindStepLinks($("skills-list"));
}

function bindStepLinks(root) {
  root.querySelectorAll("a[data-step]").forEach((a) => {
    a.onclick = () => {
      const [mod, name] = a.dataset.step.split("/");
      openStep(mod, Number(name.replace("step-", "")));
    };
  });
}

/* ==================================================================
   ЖУРНАЛ
   ================================================================== */

async function openJournal() {
  const d = await api("/api/journal");
  showScreen("journal-body");
  const real = d.records.filter((r) => r.parsed);
  $("journal-summary").innerHTML = `
    <div class="card"><h3>Записей</h3><span class="big">${real.length}</span>
      <p>строк в <code>${esc(d.path)}</code></p></div>
    <div class="card"><h3>План против факта</h3>
      <span class="big">${d.sum_fact} / ${d.sum_plan} ч</span>
      <p>по ${d.counted} записям, где заполнены оба поля. План — середина вилки шага,
         поэтому это ориентир, а не приговор оценке.</p></div>
    <div class="card"><h3>Обращений к стороне</h3><span class="big">${d.notes}</span>
      <p>пометок <code>[сторона]</code>. Больше одной на шаг — признак, что теории
         в шаге не хватает (решение 28).</p></div>`;

  $("journal-records").innerHTML = real.length
    ? `<table class="journal">
        <tr><th>Дата</th><th>Тема</th><th>План</th><th>Факт</th><th>Из них задания</th><th>Где застрял</th><th>Что оказалось лишним</th></tr>
        ${d.records.map((r) => r.parsed
          ? `<tr><td class="num">${esc(r.date)}</td><td>${esc(r.theme)}</td>
             <td class="num">${esc(r.plan)}</td><td class="num">${esc(r.fact)}</td>
             <td class="num">${esc(r.fact_tasks)}</td>
             <td>${esc(r.stuck)}</td><td>${esc(r.useless)}</td></tr>`
          : `<tr><td colspan="7"><code>${esc(r.raw)}</code></td></tr>`).join("")}
      </table>`
    : '<p class="hint">Записей пока нет. Первая появится, когда вы закроете первый шаг.</p>';
}

/* ==================================================================
   ШАГ
   ================================================================== */

async function openStep(module, number) {
  current = await api(`/api/step/${module}/${number}`);
  chatHistory = [];
  $("chat-log").innerHTML = "";
  showScreen("step-body");

  $("crumbs").innerHTML =
    `<b>${esc(current.module)}</b> ${esc(current.module_name)}` +
    (current.position ? ` · шаг ${current.position} из ${current.of}` : " · служебный файл") +
    ` · <span title="файл, который вы читаете">${esc(current.rel_path)}</span>`;
  $("step-title").textContent = current.title;

  const h = current.header;
  const chips = [];
  if (current.plan_hours !== "—") chips.push(`<span class="chip strong">⏱ ${esc(current.plan_hours)} ч по плану</span>`);
  if (h["Умение"]) chips.push(`<span class="chip">умение ${esc(h["Умение"])}</span>`);
  if (current.checks.length) chips.push(`<span class="chip">▣ проверяется скриптом</span>`);
  if (current.deferred.length) chips.push(`<span class="chip">△ нужен ручной прогон</span>`);
  if (h["Требуется до этого"]) {
    const need = h["Требуется до этого"].replace(/`/g, "");
    const short = need.length > 70 ? need.slice(0, 70).trimEnd() + "…" : need;
    chips.push(`<span class="chip" title="${esc(need)}">до этого: ${esc(short)}</span>`);
  }
  $("step-chips").innerHTML = chips.join("");

  $("deferred").innerHTML = current.deferred.map((d) => `
    <div class="deferred-row">
      <div class="head">△ Здесь оценка ИИ не заменяет реальный прогон — ${esc(d.section)}</div>
      <div>${esc(d.what)}</div>
      <div class="warn">Этот шаг делается руками в настоящем приложении (Power BI Desktop,
        Tableau Public, Looker Studio). Ассистент может проверить формулировку ответа,
        но не то, что вы действительно построили.</div>
    </div>`).join("");

  $("whats-next").hidden = true;
  $("journal-tail").hidden = true;
  renderPrereq();
  $("preamble").innerHTML = current.preamble_html ? `<div class="md">${current.preamble_html}</div>` : "";
  $("preamble").hidden = !current.preamble_html;

  renderSections();
  renderStepNav();
  renderSuggestions();
  applyState(current.state);
  renderTree();
}

function renderPrereq() {
  const p = current.prerequisites;
  const box = $("prereq");
  const items = [...p.steps.filter((x) => !x.declaration), ...p.modules];
  if (!p.raw || !items.length) {
    box.innerHTML = "";
    box.hidden = true;
    return;
  }
  box.hidden = false;
  const open = items.filter((x) => x.step_id ? !x.done : x.done < x.total);
  const link = (x) => x.step_id
    ? `<a data-step="${esc(x.step_id)}">${esc(x.step_id)} — ${esc(x.title)}</a>${x.done ? " ✓" : ""}`
    : `<a data-module="${esc(x.module)}">${esc(x.module)} ${esc(x.name)}</a> — закрыто ${x.done} из ${x.total}`;
  box.innerHTML = `<div class="prereq ${open.length ? "" : "ok"}">
      <b>${open.length
        ? "До этого шага в программе идёт то, что ещё не отмечено закрытым:"
        : "Всё, что нужно до этого шага, отмечено закрытым."}</b>
      ${items.map((x) => "· " + link(x)).join("<br>")}
      ${open.length ? '<div class="hint">Это подсказка, а не запрет: отметки ставите вы, и приложение не знает, что вы делали вне его. Шаг открывается в любом случае.</div>' : ""}
    </div>`;
  bindStepLinks(box);
  box.querySelectorAll("a[data-module]").forEach((a) => {
    a.onclick = () => openModule(a.dataset.module);
  });
}

function renderSections() {
  const toc = current.sections.filter((s) => s.num)
    .map((s) => `<a href="#sec-${s.num}" class="${s.key ? "key" : ""}">${esc(s.num)} ${esc(s.title)}</a>`).join("");
  $("toc").innerHTML = toc;
  $("toc").hidden = !toc;

  const box = $("sections");
  box.innerHTML = "";
  for (const s of current.sections) {
    const el = document.createElement("div");
    el.className = "sec" + (s.key ? " key" : "");
    el.id = "sec-" + s.num;
    el.innerHTML =
      `<div class="sec-head"><span class="num">${esc(s.num)}</span>` +
      `<span class="ttl">${esc(s.title)}</span>` +
      `<span class="hint">${esc(s.hint)}</span><span class="caret">▾</span></div>` +
      `<div class="sec-body md">${s.html}</div>`;
    el.querySelector(".sec-head").onclick = () => el.classList.toggle("collapsed");
    box.appendChild(el);

    // Проверки стоят там, где они нужны: сразу под критерием готовности.
    if (s.num === "1.5") {
      box.appendChild(buildChecksPanel());
      if (current.has_criterion) box.appendChild(buildVerdictPanel());
    }
  }
  // Шаг без раздела 1.5 (декларации) — панель проверок в конец, если есть команды.
  if (!current.sections.some((s) => s.num === "1.5") && current.checks.length) {
    box.appendChild(buildChecksPanel());
  }
}

function renderStepNav() {
  const link = (s, dir) => s
    ? `<a href="#" data-go="${s.module}/${s.number}">${dir} ${esc(s.module)}.${String(s.number).padStart(2, "0")} ${esc(s.title)}</a>`
    : "<span></span>";
  $("step-nav").innerHTML = link(current.prev, "←") + link(current.next, "→");
  $("step-nav").querySelectorAll("a[data-go]").forEach((a) => {
    a.onclick = (e) => {
      e.preventDefault();
      const [m, n] = a.dataset.go.split("/");
      openStep(m, Number(n));
    };
  });
}

/* ------------------------------------------------------- проверки */

function buildChecksPanel() {
  const el = document.createElement("div");
  el.className = "panel";
  if (!current.checks.length) {
    el.innerHTML = `<h3>Проверка</h3><p class="hint">У этого шага нет скрипта:
      критерий выше проверяется вашими руками — сверкой файла, числа или экрана.
      Письменную часть можно отдать ассистенту (блок ниже).</p>`;
    return el;
  }
  el.innerHTML = `<h3>Проверка скриптом</h3>
    <p class="hint">Запускается тот же файл, что написан в шаге, — вывод показывается
      дословно, как в терминале. Порог указан в критерии выше.</p>` +
    current.checks.map((c, i) => `
      <div class="check">
        <div class="cmd">${esc(c.raw)}${c.cwd && c.cwd !== "." ? ` (из ${esc(c.cwd)})` : ""}</div>
        <button data-check="${i}" class="primary">Проверить</button>
        <div id="check-out-${i}"></div>
      </div>`).join("");
  el.querySelectorAll("button[data-check]").forEach((b) => {
    b.onclick = () => runCheck(Number(b.dataset.check), b);
  });
  return el;
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
    const verdict = r.returncode === 0
      ? "код возврата 0 — скрипт не нашёл расхождений"
      : `код возврата ${r.returncode} — есть расхождения, смотрите строки [FAIL]`;
    out.innerHTML =
      `<div class="verdict-line" style="margin-top:10px"><span class="tag script">РЕЗУЛЬТАТ СКРИПТА</span> ${esc(verdict)}` +
      (r.error ? ` — ${esc(r.error)}` : "") + `</div>` +
      `<pre class="out">${painted || "(пустой вывод)"}</pre>` +
      `<p class="hint">То же самое в терминале: <code>${esc(r.command)}</code> из <code>${esc(r.cwd)}</code></p>`;
  } catch (e) {
    out.innerHTML = `<p class="fail">${esc(e.message)}</p>`;
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------- вердикт ИИ */

function buildVerdictPanel() {
  const el = document.createElement("div");
  el.className = "panel";
  el.innerHTML = `
    <h3>Проверка письменного ответа ассистентом</h3>
    <p class="hint">Для того, что скриптом не проверяется: письменные ответы, вопрос 1.8,
      описание сделанного в Power BI или Tableau. Ассистент сверит ваш текст с разделами
      1.5 и 1.6 этого шага. <b>Это слабее скрипта</b> — он проверяет формулировку, а не файл.</p>
    <label>Что проверяем<input id="v-task" placeholder="например: задание 13, или вопрос 1.8"></label>
    <label>Ваш ответ<textarea id="v-answer" rows="5" placeholder="напишите ответ своими словами"></textarea></label>
    <button id="btn-verdict" class="primary">Проверить по критерию</button>
    <div id="verdict-out"></div>`;
  el.querySelector("#btn-verdict").onclick = askVerdict;
  return el;
}

async function askVerdict() {
  const out = $("verdict-out");
  out.innerHTML = '<p class="hint">ассистент читает ваш ответ и разделы 1.5 и 1.6…</p>';
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
        <div class="verdict-line"><span class="tag ai">ВЕРДИКТ ИИ ПО КРИТЕРИЮ — НЕ РЕЗУЛЬТАТ СКРИПТА</span></div>
        <div class="big">${esc(v.verdict)}</div>
        <p>${esc(v.explanation)}</p>
        ${list("Что ответ закрывает", v.matched)}
        ${list("Чего в ответе нет", v.missing)}
        ${list("Попадание в «Типичные ошибки» (1.6)", v.errors_hit)}
        <p class="hint">Это оценка текста, а не проверка файла. Ручной прогон инструмента она не заменяет.</p>
        <p class="hint">В журнал уйдёт: <code>${esc(v.note)}</code></p>
      </div>`;
    await refreshState();
  } catch (e) {
    out.innerHTML = `<p class="fail">${esc(e.message)}</p>`;
  }
}

/* ==================================================================
   СЕССИЯ И ТАЙМЕР
   ================================================================== */

function fmt(sec) {
  const s = Math.max(0, Math.floor(sec));
  const p = (n) => String(n).padStart(2, "0");
  return `${Math.floor(s / 3600)}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)}`;
}

const currentSeconds = () => elapsedBase + (runningSince ? (Date.now() - runningSince) / 1000 : 0);
const tick = () => { $("timer").textContent = fmt(currentSeconds()); };

const HINTS = {
  not_started: "Нажмите «Начал» — пойдёт таймер. Без него шаг тоже читается, но час не попадёт в журнал.",
  running: "Таймер идёт. Отходите — нажмите «Пауза»: перерывы в честные часы не считаются.",
  paused: "Пауза. «Продолжил» — вернуться к работе, «Закончил» — записать сессию в журнал.",
  done: "Шаг закрыт. Записи в журнале уже нет смысла править отсюда — правьте сам файл.",
};

function applyState(st) {
  current.state = st;
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
  const pill = $("session-status");
  pill.textContent = STATUS_TEXT[st.status] || "";
  pill.className = "pill " + (st.status === "running" ? "running" : st.status === "done" ? "done" : "");
  $("session-hint").textContent = HINTS[st.status] || "";
}

async function refreshState() {
  const s = await api(`/api/step/${current.module}/${current.number}`);
  current.state = s.state;
  return s.state;
}

$("btn-start").onclick = async () => applyState(await api("/api/session/start", { step_id: current.step_id }));
$("btn-pause").onclick = async () => applyState(await api("/api/session/pause", { step_id: current.step_id }));
$("btn-reopen").onclick = async () => { applyState(await api("/api/session/reopen", { step_id: current.step_id })); loadTree(true); };
$("btn-cancel").onclick = () => { $("finish-form").hidden = true; };

$("btn-finish").onclick = () => {
  const fact = Math.floor(currentSeconds() / 900) * 0.25;
  $("f-theme").value = `${current.code} ${current.title}`;
  $("f-plan").value = current.plan_hours;
  $("f-fact").value = String(fact);
  const notes = current.state.notes || [];
  $("f-notes").innerHTML = notes.length
    ? `<p class="hint">В «Где застрял» приложение допишет ${notes.length} пометк${notes.length === 1 ? "у" : "и"}
       об обращениях к ассистенту:<br>${notes.map((n) => `<code>${esc(n)}</code>`).join("<br>")}</p>`
    : `<p class="hint">Обращений к ассистенту за сессию не было — в журнале это тоже факт.</p>`;
  $("finish-form").hidden = false;
  $("finish-form").scrollIntoView?.({ behavior: "smooth", block: "center" });
};

$("btn-write").onclick = async () => {
  const btn = $("btn-write");
  btn.disabled = true;
  try {
    const r = await api("/api/session/finish", {
      step_id: current.step_id,
      theme: $("f-theme").value,
      plan: $("f-plan").value,
      fact_tasks: $("f-tasks").value,
      stuck: $("f-stuck").value,
      useless: $("f-useless").value,
    });
    $("journal-tail").hidden = false;
    $("journal-tail").textContent = "Записано в research/self.md:\n\n" + r.tail.join("\n");
    $("f-tasks").value = "";
    $("f-stuck").value = "";
    $("f-useless").value = "";
    applyState(r.state);
    await loadTree(true);
    showWhatsNext();
  } catch (e) {
    alert("Не записалось: " + e.message);
  } finally {
    btn.disabled = false;
  }
};

function showWhatsNext() {
  const box = $("whats-next");
  const n = tree && tree.next_step;
  if (!n) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML =
    `<div class="label">Шаг закрыт. Дальше</div>
     <h3>${esc(n.module)}.${String(n.number).padStart(2, "0")} — ${esc(n.title)}</h3>
     <div class="meta">${esc(n.module_name)} · этап «${esc(n.stage)}» · ${esc(n.plan_hours)} ч</div>
     <button class="primary" id="next-go">Открыть следующий шаг</button>`;
  $("next-go").onclick = () => openStep(n.module, n.number);
  box.scrollIntoView?.({ behavior: "smooth", block: "center" });
}

/* ==================================================================
   АССИСТЕНТ
   ================================================================== */

function renderSuggestions() {
  const q = [
    "Объясни своими словами, что от меня требует этот шаг",
    "Что именно нужно сделать в задании 1.4 — по пунктам",
    "Разбери критерий готовности 1.5: как я пойму, что закрыл шаг",
  ];
  $("chat-suggest").innerHTML = q.map((t) => `<button data-q="${esc(t)}">${esc(t)}</button>`).join("");
  $("chat-suggest").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { $("chat-input").value = b.dataset.q; ask(); };
  });
}

async function ask() {
  const q = $("chat-input").value.trim();
  if (!q || !current) return;
  $("chat-input").value = "";
  $("chat-suggest").innerHTML = "";
  const log = $("chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="msg you">${esc(q)}</div>`);
  const pending = document.createElement("div");
  pending.className = "msg ai";
  pending.textContent = "думает…";
  log.appendChild(pending);
  log.scrollTop = log.scrollHeight;
  try {
    const r = await api("/api/assistant/ask", { step_id: current.step_id, question: q, history: chatHistory });
    chatHistory.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
    pending.innerHTML = esc(r.answer) + `<span class="note">В журнал: ${esc(r.note)}</span>`;
    await refreshState();
  } catch (e) {
    pending.className = "msg err";
    pending.textContent = e.message;
  }
  log.scrollTop = log.scrollHeight;
}

$("btn-ask").onclick = ask;
$("chat-input").onkeydown = (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) ask();
};

/* ==================================================================
   ПОМОЩЬ
   ================================================================== */

function openHome() {
  current = null;
  showScreen("home");
  highlightActive();
  renderTree();
}

$("brand").onclick = openHome;
document.querySelectorAll(".topnav button").forEach((b) => {
  b.onclick = () => ({ home: openHome, skills: openSkills, journal: openJournal })[b.dataset.screen]();
});

const closeHelp = () => { $("help").hidden = true; };
$("btn-help").onclick = () => { $("help").hidden = false; };
$("help-close").onclick = closeHelp;
$("help").onclick = (e) => { if (e.target === $("help")) closeHelp(); };
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("help").hidden) closeHelp();
});

try {
  if (!localStorage.getItem("seen-help")) {
    $("help").hidden = false;
    localStorage.setItem("seen-help", "1");
  }
} catch (e) { /* приватное окно — не беда */ }

loadTree();
