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
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    // Сервер убит, порт занят другим процессом, машина ушла в сон —
    // fetch падает до ответа, и без этой ветки на экране остаётся
    // молчание вместо причины.
    throw new Error(`сервер не отвечает (${path}). Запущен ли app/server.py?`);
  }
  let data;
  try {
    data = await res.json();
  } catch (e) {
    throw new Error(`сервер вернул не JSON на ${path} (HTTP ${res.status})`);
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status} на ${path}`);
  return data;
}

const esc = (s) => String(s == null ? "" : s)
  .replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* Формулировки умений приходят из blueprint дословно, вместе с его
   разметкой: `**до**`, `` `LEFT JOIN` ``. Экранированный текст показывал
   звёздочки и обратные кавычки как есть. */
const mdInline = (s) => esc(s)
  .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
  .replace(/`([^`]+)`/g, "<code>$1</code>");

const ic = (name, cls) =>
  `<svg class="ic${cls ? " " + cls : ""}" aria-hidden="true"><use href="/static/icons.svg#i-${name}"/></svg>`;

const pad2 = (n) => String(n).padStart(2, "0");

/** «1 умение, 2 умения, 5 умений». Без этого интерфейс пишет
    «Закрыто 1 умений» — мелочь, по которой сразу видно, что текст
    собран конкатенацией и никем не прочитан. */
function plural(n, one, few, many) {
  const d10 = n % 10, d100 = n % 100;
  if (d10 === 1 && d100 !== 11) return one;
  if (d10 >= 2 && d10 <= 4 && (d100 < 12 || d100 > 14)) return few;
  return many;
}
const nStep = (n) => `${n} ${plural(n, "шаг", "шага", "шагов")}`;
const nProject = (n) => `${n} ${plural(n, "проект", "проекта", "проектов")}`;
const pct = (done, total) => (total ? Math.round((done / total) * 100) : 0);

const STATUS_TEXT = { not_started: "не начат", running: "идёт", paused: "пауза", done: "закончен" };
const STATUS_ICON = { not_started: "square", running: "play", paused: "pause", done: "check" };

/* ==================================================================
   ВИДИМЫЕ СОСТОЯНИЯ

   На каждый запрос — три исхода, и каждый должен быть виден: идёт,
   пусто, не вышло. Молчащий экран и вечный «загрузка…» — это не
   состояния, а их отсутствие.
   ================================================================== */

function stateBox(kind, title, text, extra) {
  const icon = { loading: "loader", empty: "inbox", err: "alert-circle" }[kind] || "inbox";
  return `<div class="state ${kind === "err" ? "err" : ""}">
    ${ic(icon, kind === "loading" ? "ic-lg ic-spin" : "ic-lg")}
    <div><b>${esc(title)}</b>${text ? esc(text) : ""}${extra || ""}</div>
  </div>`;
}

const loadingBox = (what) => stateBox("loading", "Загружается", ` ${what}…`);
const emptyBox = (title, text) => stateBox("empty", title, text);

function errorBox(e, retryId) {
  return stateBox("err", "Не вышло", " " + (e && e.message ? e.message : String(e)),
    retryId ? `<div class="row" style="margin-top:8px">
      <button id="${retryId}">${ic("repeat")}Повторить</button></div>` : "");
}

/** Показать ошибку в контейнере и повесить «Повторить» на ту же операцию. */
function showError(boxId, e, retry) {
  const box = $(boxId);
  const rid = boxId + "-retry";
  box.innerHTML = errorBox(e, retry ? rid : null);
  box.hidden = false;
  if (retry) $(rid).onclick = retry;
}

/* ==================================================================
   ЭКРАНЫ

   Показан ровно один. Скрытие — только атрибутом `hidden` (в CSS он
   объявлен сильнее любого display).
   ================================================================== */

const SCREENS = ["home", "step-body", "module-body", "skills-body", "journal-body"];
const NAV_OF = { home: "home", "skills-body": "skills", "journal-body": "journal" };

function showScreen(id) {
  SCREENS.forEach((s) => { $(s).hidden = s !== id; });
  document.querySelectorAll(".topnav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.screen === NAV_OF[id]));
  $("step").scrollTop = 0;
}

/* ==================================================================
   ТЕМА

   Настройка вида, а не содержания: живёт в localStorage браузера и в
   `app/state/` не попадает. Значение по умолчанию — системное.
   ================================================================== */

$("btn-theme").onclick = () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) { /* приватное окно */ }
};

/* ==================================================================
   ДЕРЕВО — порядок прохождения по шести этапам части 6.2 blueprint
   ================================================================== */

async function loadTree(keepOpen) {
  try {
    tree = await api("/api/tree");
  } catch (e) {
    $("tree-body").innerHTML = errorBox(e, "tree-retry");
    $("tree-retry").onclick = () => loadTree(keepOpen);
    $("top-count").textContent = "нет связи";
    $("home-hero").innerHTML = errorBox(e);
    return;
  }
  renderTree();
  renderHome();

  const p = pct(tree.done, tree.total);
  $("top-bar").style.width = p + "%";
  $("top-pct").textContent = p + " %";
  $("top-count").textContent = `${tree.done} из ${tree.total} шагов`;
  $("top-progress").title =
    `${tree.done} из ${tree.total} содержательных шагов закрыто; ` +
    `проектов ${tree.projects_done} из ${tree.projects_total}. ` +
    `Проект — не шаг (часть 6.5 blueprint), поэтому счётчика два.`;

  $("help-intro").textContent =
    `Это не курс с видео. Это ${nStep(tree.total)} и ${nProject(tree.projects_total)}, ` +
    `которые вы делаете руками, и проверки, которые говорят «сошлось» или ` +
    `«не сошлось» — без «молодец, продолжай».`;

  if (!tree.assistant) {
    $("chat-hint").innerHTML =
      'Ключ не найден — чат и вердикт ИИ выключены. Заполните <code>app/.env</code> ' +
      'по образцу <code>app/.env.example</code> и перезапустите приложение. ' +
      'Всё остальное работает и без ключа.';
    $("chat-hint").classList.add("fail");
  }
  if (keepOpen) highlightActive();
}

function modIcon(mod) {
  if (mod.projects_total) return "briefcase";
  if (mod.module === "review") return "repeat";
  if (mod.module === "career") return "flag";
  return "book";
}

/** Маленькое кольцо прогресса модуля: доля закрытых шагов. */
function modRing(done, total) {
  const r = 6.5, c = 2 * Math.PI * r;
  const off = c * (1 - (total ? done / total : 0));
  return `<svg class="mod-ring" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
    <circle class="track" cx="9" cy="9" r="${r}"/>
    <circle class="val" cx="9" cy="9" r="${r}" stroke-dasharray="${c.toFixed(2)}"
            stroke-dashoffset="${off.toFixed(2)}"/></svg>`;
}

function renderTree() {
  const filter = $("tree-filter").value.trim().toLowerCase();
  const box = $("tree-body");
  box.innerHTML = "";
  const currentStage = tree.next_step
    ? tree.stages.find((s) => s.modules.some((m) => m.module === tree.next_step.module))
    : null;

  for (const stage of tree.stages) {
    const modules = stage.modules
      .map((mod) => ({ mod, steps: mod.steps.filter((s) => matches(s, mod, filter)) }))
      .filter((x) => x.steps.length);
    if (!modules.length) continue;

    const el = document.createElement("div");
    const isCurrent = currentStage && currentStage.number === stage.number;
    el.className = "stage" + (isCurrent ? " current" : "");
    const sDone = stage.done + stage.projects_done;
    const sTotal = stage.total + stage.projects_total;
    el.innerHTML =
      `<div class="stage-head">` +
      `<span class="n">${stage.number}</span><span class="nm">${esc(stage.name)}</span>` +
      (isCurrent ? '<span class="now">идёт</span>' : "") +
      `<span class="h" title="часы этапа по blueprint 6.2">${esc(stage.hours)} ч</span></div>` +
      `<div class="stage-meter" title="${sDone} из ${sTotal} закрыто">` +
      `<i style="width:${pct(sDone, sTotal)}%"></i></div>`;

    for (const { mod, steps } of modules) {
      const m = document.createElement("div");
      m.className = "mod";
      const modDone = mod.done + mod.projects_done;
      const modTotal = mod.total + mod.projects_total;
      const complete = modTotal && modDone === modTotal ? " complete" : "";
      m.innerHTML =
        `<div class="mod-head${complete}" title="${esc(mod.kind)} · ${esc(mod.hours)} ч">` +
        modRing(modDone, modTotal) +
        `<span class="code">${esc(mod.module)}</span>` +
        `<span class="name">${esc(mod.name)}</span>` +
        `<span class="count">${modDone}/${modTotal}</span></div>`;
      const list = document.createElement("div");
      list.className = "mod-steps";
      list.hidden = !filter && !(current && current.module === mod.module);

      for (const st of steps) {
        const a = document.createElement("div");
        a.className = "step-link" + (st.declaration ? " decl" : "") + (st.project ? " project" : "") +
          (st.status === "done" ? " done" : "") + (st.status === "running" ? " running" : "");
        a.dataset.id = st.step_id;
        a.title = st.full_title + (st.status !== "not_started" ? ` — ${STATUS_TEXT[st.status]}` : "");
        const marks =
          (st.has_checks ? ic("terminal") : "") +
          (st.deferred ? ic("hand") : "") +
          (st.status === "done" ? ic("check") : "");
        const label = st.declaration
          ? "Декларация модуля — служебное, можно пропустить"
          : (st.project ? "Проект целиком — " + st.plan_hours + " ч" : st.title);
        a.innerHTML =
          `<span class="num">${st.declaration ? "—" : (st.project ? ic("briefcase") : pad2(st.number))}</span>` +
          `<span class="t">${esc(label)}</span><span class="marks">${marks}</span>`;
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
  if (!box.children.length) {
    box.innerHTML = emptyBox("Ничего не найдено", " по запросу «" + $("tree-filter").value.trim() + "».");
  }
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

$("tree-filter").oninput = () => { if (tree) renderTree(); };

/* ==================================================================
   СТАРТОВЫЙ ЭКРАН
   ================================================================== */

/** Середина вилки часов: «26–31» → 28.5. Нужна только как ширина
    сегмента маршрута, в числах на экране не показывается. */
function midHours(range) {
  const n = String(range).match(/[\d.,]+/g);
  if (!n) return 1;
  const v = n.map((x) => parseFloat(x.replace(",", ".")));
  return v.length > 1 ? (v[0] + v[1]) / 2 : v[0];
}

/** Полоса маршрута: шесть этапов шириной по часам, заполнение — по доле
    закрытого, текущий обведён. */
function routeBar() {
  const w = tree.stages.map((s) => midHours(s.hours));
  const sum = w.reduce((a, b) => a + b, 0) || 1;
  const cur = tree.next_step
    ? tree.stages.findIndex((s) => s.modules.some((m) => m.module === tree.next_step.module))
    : -1;
  const segs = tree.stages.map((s, k) => {
    const done = s.done + s.projects_done;
    const total = s.total + s.projects_total;
    return `<div class="seg${k === cur ? " current" : ""}"
      style="flex:${(w[k] / sum * 100).toFixed(2)}"
      title="Этап ${s.number}. ${esc(s.name)} — ${esc(s.hours)} ч, закрыто ${done} из ${total}">
      <i style="width:${pct(done, total)}%"></i></div>`;
  }).join("");
  // Подписи под каждым сегментом обрезались на узких этапах («Осн…»):
  // ширина сегмента задана часами, а не длиной названия. Название несёт
  // подсказка сегмента, а текущий этап назван словами в строке ниже.
  const here = cur >= 0
    ? `Идёт этап ${tree.stages[cur].number} из ${tree.stages.length} — «${esc(tree.stages[cur].name)}». `
    : "";
  return `<div class="route"><div class="track">${segs}</div>
    <div class="sum">${here}Закрыто ${nStep(tree.done)} из ${tree.total}
      и ${nProject(tree.projects_done)} из ${tree.projects_total}.</div></div>`;
}

function renderHome() {
  const t = tree.totals || {};
  $("home-lead").innerHTML =
    `Программа — это ${nStep(tree.total)} и ${nProject(tree.projects_total)} портфолио, ` +
    `разложенные по шести этапам: ${esc(t.hours)} ч, ` +
    `${esc(t.weeks_25)} недель при 25 ч/нед или ${esc(t.weeks_10)} при 10. ` +
    `Каждый шаг устроен одинаково: немного теории, разобранный пример, задание, ` +
    `которое вы делаете руками, и проверка — как убедиться, что получилось. ` +
    `Слева — всё в том порядке, в котором это надо проходить.`;

  const n = tree.next_step;
  if (n) {
    const chips = [
      `<span class="chip strong">${ic("clock")}<span>${esc(n.plan_hours)} ч по плану</span></span>`,
      n.has_checks ? `<span class="chip ok">${ic("terminal")}<span>проверяется скриптом</span></span>` : "",
      n.deferred ? `<span class="chip warn">${ic("hand")}<span>нужен ручной прогон</span></span>` : "",
      `<span class="chip">${ic("flag")}<span>этап «${esc(n.stage)}»</span></span>`,
    ].filter(Boolean).join("");
    $("home-hero").innerHTML = `<div class="hero">
      <div class="label">${tree.done
        ? `Вы остановились здесь — ${esc(n.module)} ${esc(n.module_name)}.`
        : `Начинается программа отсюда — ${esc(n.module)} ${esc(n.module_name)}.`}</div>
      <h2>${mdInline(n.title)}</h2>
      <div class="chips">${chips}</div>
      <button class="primary big" id="btn-go">Открыть ${n.project ? "проект" : "шаг"}</button>
      ${routeBar()}</div>`;
  } else {
    $("home-hero").innerHTML = `<div class="hero">
      <div class="label">Программа пройдена.</div>
      <h2>Все ${nStep(tree.total)} и ${nProject(tree.projects_total)} закрыты</h2>
      <div class="chips"><span class="chip">Журнал прохождения — <code>research/self.md</code></span></div>
      ${routeBar()}</div>`;
  }
  if (n) $("btn-go").onclick = () => openStep(n.module, n.number);

  const rows = tree.stages.map((s) => {
    const cur = tree.next_step && s.modules.some((m) => m.module === tree.next_step.module);
    const done = s.done + s.projects_done;
    const total = s.total + s.projects_total;
    return `<tr class="${cur ? "current" : ""}">
      <td><span class="nm">${s.number}. ${esc(s.name)}</span>
        <div class="mods">${s.modules.map((m) => esc(m.module)).join(" · ")}</div></td>
      <td class="num">${esc(s.hours)} ч</td>
      <td style="min-width:180px"><div class="meter">
        <div class="bar"><i style="width:${pct(done, total)}%"></i></div>
        <span class="txt">${done}/${total}</span></div></td></tr>`;
  }).join("");

  $("home-stages").innerHTML =
    `<h2>Шесть этапов</h2>
     <p class="section-note">Порядок, часы и недели — из <code>design/blueprint.md</code>,
       часть 6.2. Приложение их не пересчитывает и своей копии не держит.</p>
     <table class="stages">
       <tr><th>Этап</th><th class="num">Часы</th><th>Пройдено</th></tr>${rows}</table>`;
}

/* ==================================================================
   ЭКРАН МОДУЛЯ — из его же step-00.md
   ================================================================== */

let currentModule = null;

async function openModule(code) {
  showScreen("module-body");
  $("mod-title").textContent = code;
  $("mod-steps").innerHTML = loadingBox("модуль " + code);
  let m;
  try {
    m = await api(`/api/module/${code}`);
  } catch (e) {
    $("mod-steps").innerHTML = errorBox(e, "mod-retry");
    $("mod-retry").onclick = () => openModule(code);
    return;
  }
  currentModule = m;
  const isProject = m.projects_total > 0;

  $("mod-crumbs").innerHTML = m.stage
    ? `${ic("flag")} Этап ${m.stage.number} <b>${esc(m.stage.name)}</b><span>${esc(m.kind)}</span>`
    : esc(m.kind);
  $("mod-title").textContent = `${m.module} — ${m.name}`;
  $("mod-chips").innerHTML =
    `<span class="chip strong">${ic("clock")}<span>${esc(m.hours)} ч на весь ${esc(m.kind)}</span></span>` +
    (isProject
      ? `<span class="chip">${ic("briefcase")}<span>проект: один файл, шагов нет</span></span>`
      : `<span class="chip">${ic("book")}<span>${nStep(m.total)}, закрыто ${m.done}</span></span>`) +
    (m.skills.length
      ? `<span class="chip">${ic("target")}<span>умения: ${m.skills.map((s) => esc(s.id)).join(", ")}</span></span>`
      : "");

  $("mod-deferred").innerHTML = m.deferred.map((d) => `
    <div class="deferred-row">
      <div class="head">${ic("hand")} ${esc(d.section)}</div>
      <div>${esc(d.what)}</div>
      <div class="warn">Эти шаги делаются руками в настоящем приложении. Вердикт ИИ их не заменяет.</div>
    </div>`).join("");

  const nextStep = m.steps.find((st) => !st.declaration && st.status !== "done");
  $("mod-next").hidden = !nextStep;
  if (nextStep) {
    const skill = (nextStep.skill || "").split(/[(—;]/)[0].trim();
    $("mod-next").innerHTML =
      `<div class="label">${m.done || m.projects_done ? "Продолжить" : "Начать"} ${esc(m.module)}</div>
       <h3>${nextStep.project ? "" : pad2(nextStep.number) + ". "}${esc(nextStep.title)}</h3>
       <div class="meta">${esc(nextStep.plan_hours)} ч по плану${skill ? ", умение " + esc(skill) : ""}</div>
       <button class="primary" id="mod-go">Открыть ${nextStep.project ? "проект" : "шаг"}</button>`;
    $("mod-go").onclick = () => openStep(m.module, nextStep.number);
  }

  $("mod-steps-head").textContent = isProject ? "Что входит" : "Шаги модуля";
  $("mod-steps").innerHTML = m.steps.map((st) => `
    <div class="modstep ${st.declaration ? "decl" : ""} ${st.status === "done" ? "done" : ""}"
         data-n="${st.number}">
      <span class="n">${st.declaration ? "—" : (st.project ? ic("briefcase") : pad2(st.number))}</span>
      <span class="t">${esc(st.declaration
        ? "Справка модуля: датасет, схема, предусловие"
        : (st.project ? "Проект целиком: заказчик, задание, критерии приёмки" : st.title))}</span>
      <span class="meta">${st.declaration ? "служебное" : esc(st.plan_hours) + " ч"}
        ${st.has_checks ? ic("terminal") : ""}${st.deferred ? ic("hand") : ""}
        ${st.status === "done" ? ic("check") : ""}</span>
    </div>`).join("");
  $("mod-steps").querySelectorAll(".modstep").forEach((el) => {
    el.onclick = () => openStep(m.module, Number(el.dataset.n));
  });

  $("mod-skills").innerHTML = m.skills.length
    ? m.skills.map((sk) => skillCard(sk, [])).join("")
    : emptyBox(isProject ? "Своего умения у проекта нет" : "Своих умений части 1 blueprint нет",
        isProject
          ? " Проект не закрывает новое умение, а первый раз применяет уже закрытые на задаче с заказчиком (часть 5 blueprint)."
          : " Инфраструктурный блок.");

  $("mod-decl").innerHTML = m.declaration_html;
  $("mod-decl-wrap").hidden = !m.has_declaration;
  renderTree();
}

/* ==================================================================
   КАРТА УМЕНИЙ
   ================================================================== */

function skillCard(sk, steps) {
  const links = (steps || []).map((st) =>
    `<a data-step="${esc(st.step_id)}" class="${st.done ? "done" : ""}">${esc(st.step_id)}${st.done ? ic("check") : ""}</a>`).join("");
  return `<div class="skill ${sk.done ? "done" : ""}" id="skill-${esc(sk.id)}">
    <div><span class="id">${esc(sk.id)}</span><span class="st">${mdInline(sk.statement)}</span></div>
    <div class="how"><b>Как проверяется:</b> ${mdInline(sk.check)}</div>
    ${links ? `<div class="steps">${links}</div>` : ""}
  </div>`;
}

async function openSkills() {
  showScreen("skills-body");
  $("skills-list").innerHTML = loadingBox("карта умений");
  let d;
  try {
    d = await api("/api/skills");
  } catch (e) {
    $("skills-list").innerHTML = errorBox(e, "skills-retry");
    $("skills-retry").onclick = openSkills;
    return;
  }
  $("skills-lead").textContent =
    `${d.total} проверяемых умений — то, ради чего программа существует. ` +
    `Каждое сформулировано как «дано → делает → как проверяется»; умение считается ` +
    `закрытым, когда закрыты все шаги, которые его объявили.`;
  // Клетка на умение, группы разделены промежутком. Видно не «сколько
  // процентов», а какие именно закрыты и где дыра.
  const cells = d.groups.map((g) =>
    g.skills.map((sk) =>
      `<a data-skill="${esc(sk.id)}" class="${sk.done ? "done" : ""}"
        title="${esc(sk.id)} — ${esc(sk.statement)}">${esc(sk.id)}</a>`).join("")
  ).join('<span class="gap"></span>');
  $("skills-progress").innerHTML = `<div class="hero">
      <div class="label">Умение закрыто, когда закрыты все шаги, которые его объявили.
        Отметку «закончил» ставите вы — приложение не знает, что сделано вне его.</div>
      <h2>Закрыто ${d.done} ${plural(d.done, "умение", "умения", "умений")} из ${d.total}</h2>
      <div class="sk-grid">${cells}</div>
    </div>`;
  $("skills-progress").querySelectorAll("a[data-skill]").forEach((a) => {
    a.onclick = () => {
      const el = $("skill-" + a.dataset.skill);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    };
  });
  $("skills-list").innerHTML = d.groups.map((g) => `
    <div class="skgroup">
      <h3><b>${esc(g.group)}.</b> ${esc(g.name)}</h3>
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
  showScreen("journal-body");
  $("journal-records").innerHTML = loadingBox("журнал");
  let d;
  try {
    d = await api("/api/journal");
  } catch (e) {
    $("journal-records").innerHTML = errorBox(e, "journal-retry");
    $("journal-retry").onclick = openJournal;
    return;
  }
  const cal = (tree && tree.calibration) || null;
  $("journal-lead").innerHTML =
    `Файл <code>${esc(d.path)}</code> — единственное, что приложение пишет. ` +
    (cal
      ? `По нему потом чинятся оценки часов всей программы: ${cal.marked} из ${cal.total} вилок
         стоят с пометкой «требуется калибровка», и снять её может только замер фактического времени.`
      : `По нему потом чинятся оценки часов всей программы.`);

  const real = d.records.filter((r) => r.parsed);
  $("journal-summary").innerHTML = `
    <div class="card"><h3>${ic("file-text")}Записей</h3><span class="big">${real.length}</span>
      <p>строк в <code>${esc(d.path)}</code></p></div>
    <div class="card"><h3>${ic("clock")}План против факта</h3>
      <span class="big">${d.sum_fact} / ${d.sum_plan} ч</span>
      <p>по ${d.counted} записям, где заполнены оба поля. План — середина вилки шага,
         поэтому это ориентир, а не приговор оценке.</p></div>
    <div class="card"><h3>${ic("spark")}Обращений к стороне</h3><span class="big">${d.notes}</span>
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
          : `<tr class="raw"><td colspan="7">${esc(r.raw)}</td></tr>`).join("")}
      </table>`
    : emptyBox("Записей пока нет.", " Первая появится, когда вы закроете первый шаг.");
}

/* ==================================================================
   ШАГ
   ================================================================== */

async function openStep(module, number) {
  showScreen("step-body");
  $("step-title").textContent = `${module}.${pad2(number)}`;
  $("sections").innerHTML = loadingBox("шаг");
  let step;
  try {
    step = await api(`/api/step/${module}/${number}`);
  } catch (e) {
    $("sections").innerHTML = errorBox(e, "step-retry");
    $("step-retry").onclick = () => openStep(module, number);
    return;
  }
  current = step;
  chatHistory = [];
  $("chat-log").innerHTML = "";
  $("session-error").innerHTML = "";

  const where = current.project
    ? "проект целиком, один файл"
    : (current.position ? `шаг ${current.position} из ${current.of}` : "служебный файл");
  $("crumbs").innerHTML =
    `${ic(current.project ? "briefcase" : "book")} <b>${esc(current.module)} ${esc(current.module_name)}</b>` +
    `<span>${where}</span>` +
    `<span class="path" title="файл, который вы читаете">${esc(current.rel_path)}</span>`;
  $("step-title").textContent = current.title;

  const h = current.header;
  const skill = h["Умение"] || h["Умения"] || "";
  const chips = [];
  if (current.plan_hours !== "—") {
    chips.push(`<span class="chip strong">${ic("clock")}<span>${esc(current.plan_hours)} ч по плану</span></span>`);
  }
  if (skill) {
    // Шапка `Умение:` бывает абзацем на четыре строки — целиком она
    // распирала строку чипов на пол-экрана. Полный текст — в title.
    const short = skill.length > 64 ? skill.slice(0, 64).trimEnd() + "…" : skill;
    chips.push(`<span class="chip" title="${esc(skill)}">${ic("target")}<span>умение ${esc(short)}</span></span>`);
  }
  if (current.checks.length) {
    chips.push(`<span class="chip ok">${ic("terminal")}<span>проверяется скриптом</span></span>`);
  }
  if (current.deferred.length) {
    chips.push(`<span class="chip warn">${ic("hand")}<span>нужен ручной прогон</span></span>`);
  }
  if (h["Требуется до этого"]) {
    const need = h["Требуется до этого"].replace(/`/g, "");
    const short = need.length > 60 ? need.slice(0, 60).trimEnd() + "…" : need;
    chips.push(`<span class="chip" title="${esc(need)}"><span>до этого: ${esc(short)}</span></span>`);
  }
  $("step-chips").innerHTML = chips.join("");

  $("deferred").innerHTML = current.deferred.map((d) => `
    <div class="deferred-row">
      <div class="head">${ic("hand")} Здесь оценка ИИ не заменяет реальный прогон — ${esc(d.section)}</div>
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
    ? `<a data-step="${esc(x.step_id)}">${esc(x.step_id)} — ${esc(x.title)}</a>${x.done ? ic("check") : ""}`
    : `<a data-module="${esc(x.module)}">${esc(x.module)} ${esc(x.name)}</a> — закрыто ${x.done} из ${x.total}`;
  box.innerHTML = `<div class="prereq ${open.length ? "" : "ok"}">
      <b>${ic(open.length ? "hand" : "check")}${open.length
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
      `<span class="shint">${esc(s.hint)}</span>${ic("chevron-down", "caret")}</div>` +
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
  const link = (s, icon) => s
    ? `<a href="#" data-go="${s.module}/${s.number}">${ic(icon)}<span>${esc(s.module)}.${pad2(s.number)} ${esc(s.title)}</span></a>`
    : "<span></span>";
  $("step-nav").innerHTML =
    link(current.prev, "arrow-left") + link(current.next, "arrow-right");
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
    el.innerHTML = `<h3>${ic("terminal")}Проверка</h3>` +
      emptyBox("У этого шага нет скрипта.",
        " Критерий выше проверяется вашими руками — сверкой файла, числа или экрана. " +
        "Письменную часть можно отдать ассистенту (блок ниже).");
    return el;
  }
  el.innerHTML = `<h3>${ic("terminal")}Проверка скриптом</h3>
    <p class="hint">Запускается тот же файл, что написан в шаге, — вывод показывается
      дословно, как в терминале. Порог указан в критерии выше.</p>` +
    current.checks.map((c, i) => `
      <div class="check">
        <div class="cmd">${esc(c.raw)}${c.cwd && c.cwd !== "." ? ` (из ${esc(c.cwd)})` : ""}</div>
        <button data-check="${i}" class="primary">${ic("play")}Проверить</button>
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
  out.innerHTML = stateBox("loading", "Скрипт выполняется", " — таймаут 120 с.");
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
      `<div class="verdict-line" style="margin-top:10px">
         <span class="tag script">${ic("terminal")}РЕЗУЛЬТАТ СКРИПТА</span>
         <span>${esc(verdict)}${r.error ? " — " + esc(r.error) : ""}</span></div>` +
      `<pre class="out">${painted || "(пустой вывод)"}</pre>` +
      `<p class="hint">То же самое в терминале: <code>${esc(r.command)}</code> из <code>${esc(r.cwd)}</code></p>`;
  } catch (e) {
    out.innerHTML = errorBox(e);
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------- вердикт ИИ */

function buildVerdictPanel() {
  const el = document.createElement("div");
  el.className = "panel";
  el.innerHTML = `
    <h3>${ic("spark")}Проверка письменного ответа ассистентом</h3>
    <p class="hint">Для того, что скриптом не проверяется: письменные ответы, вопрос 1.8,
      описание сделанного в Power BI или Tableau. Ассистент сверит ваш текст с разделами
      1.5 и 1.6 этого шага. <b>Это слабее скрипта</b> — он проверяет формулировку, а не файл.</p>
    <label>Что проверяем<input id="v-task" placeholder="например: задание 13, или вопрос 1.8"></label>
    <label>Ваш ответ<textarea id="v-answer" rows="5" placeholder="напишите ответ своими словами"></textarea></label>
    <button id="btn-verdict" class="primary">${ic("spark")}Проверить по критерию</button>
    <div id="verdict-out"></div>`;
  el.querySelector("#btn-verdict").onclick = askVerdict;
  return el;
}

async function askVerdict() {
  const out = $("verdict-out");
  const btn = $("btn-verdict");
  btn.disabled = true;
  out.innerHTML = stateBox("loading", "Ассистент читает", " ваш ответ и разделы 1.5 и 1.6…");
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
        <div class="verdict-line"><span class="tag ai">${ic("spark")}ВЕРДИКТ ИИ ПО КРИТЕРИЮ — НЕ РЕЗУЛЬТАТ СКРИПТА</span></div>
        <div class="big">${esc(v.verdict)}</div>
        <p>${esc(v.explanation)}</p>
        ${list("Что ответ закрывает", v.matched)}
        ${list("Чего в ответе нет", v.missing)}
        ${list("Попадание в «Типичные ошибки» (1.6)", v.errors_hit)}
        <p class="hint">Это оценка текста, а не проверка файла. Ручной прогон инструмента она не заменяет.</p>
        <div class="msg"><span class="note">${ic("file-text")}
          <span>В журнал уйдёт: <code>${esc(v.note)}</code></span></span></div>
      </div>`;
    await refreshState();
  } catch (e) {
    out.innerHTML = errorBox(e);
  } finally {
    btn.disabled = false;
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
  $("btn-start-text").textContent = st.status === "paused" ? "Продолжил" : "Начал";
  $("btn-pause").hidden = !running;
  $("btn-finish").hidden = done || st.status === "not_started";
  $("btn-reopen").hidden = !done;
  $("finish-form").hidden = true;
  const pill = $("session-status");
  pill.innerHTML = ic(STATUS_ICON[st.status] || "square") + esc(STATUS_TEXT[st.status] || "");
  pill.className = "pill " + (st.status === "running" ? "running" : st.status === "done" ? "done" : "");
  $("session-hint").textContent = HINTS[st.status] || "";
}

async function refreshState() {
  const s = await api(`/api/step/${current.module}/${current.number}`);
  current.state = s.state;
  return s.state;
}

/** Кнопка сессии: отказ сервера обязан быть виден, а не проглочен. */
function sessionButton(id, action, after) {
  $(id).onclick = async () => {
    const btn = $(id);
    btn.disabled = true;
    $("session-error").innerHTML = "";
    try {
      applyState(await api(`/api/session/${action}`, { step_id: current.step_id }));
      if (after) await after();
    } catch (e) {
      showError("session-error", e, null);
    } finally {
      btn.disabled = false;
    }
  };
}

sessionButton("btn-start", "start");
sessionButton("btn-pause", "pause");
sessionButton("btn-reopen", "reopen", () => loadTree(true));
$("btn-cancel").onclick = () => { $("finish-form").hidden = true; };

$("btn-finish").onclick = () => {
  const fact = Math.floor(currentSeconds() / 900) * 0.25;
  $("f-theme").value = `${current.code} ${current.title}`;
  $("f-plan").value = current.plan_hours;
  $("f-fact").value = String(fact);
  $("finish-error").innerHTML = "";
  const notes = current.state.notes || [];
  $("f-notes").innerHTML = notes.length
    ? `<p class="hint">В «Где застрял» приложение допишет ${notes.length} ${plural(notes.length, "пометку", "пометки", "пометок")}
       об обращениях к ассистенту:<br>${notes.map((n) => `<code>${esc(n)}</code>`).join("<br>")}</p>`
    : `<p class="hint">Обращений к ассистенту за сессию не было — в журнале это тоже факт.</p>`;
  $("finish-form").hidden = false;
  $("finish-form").scrollIntoView?.({ behavior: "smooth", block: "center" });
};

$("btn-write").onclick = async () => {
  const btn = $("btn-write");
  btn.disabled = true;
  $("finish-error").innerHTML = "";
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
    showError("finish-error", e, null);
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
     <h3>${esc(n.project ? n.module : n.module + "." + pad2(n.number))} — ${esc(n.title)}</h3>
     <div class="meta">${esc(n.module_name)}, этап «${esc(n.stage)}», ${esc(n.plan_hours)} ч по плану</div>
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

/** Реплика чата: кто говорит — подписью, а не только цветом фона. */
function bubble(who, text, note) {
  const map = {
    you: { icon: "user", name: "Вы" },
    ai: { icon: "spark", name: "Ассистент" },
    err: { icon: "alert-circle", name: "Ошибка" },
  }[who];
  return `<div class="msg ${who}">
    <div class="who">${ic(map.icon)}${map.name}</div>
    <div class="body">${esc(text)}${note
      ? `<span class="note">${ic("file-text")}<span>Уйдёт в журнал: <code>${esc(note)}</code></span></span>`
      : ""}</div></div>`;
}

async function ask() {
  const q = $("chat-input").value.trim();
  if (!q) return;
  if (!current) {
    $("chat-log").insertAdjacentHTML("beforeend",
      bubble("err", "Сначала откройте шаг: ассистент отвечает по тексту открытого шага."));
    return;
  }
  $("chat-input").value = "";
  $("chat-suggest").innerHTML = "";
  const log = $("chat-log");
  log.insertAdjacentHTML("beforeend", bubble("you", q));
  const pending = document.createElement("div");
  pending.innerHTML = bubble("ai", "думает…");
  pending.querySelector(".body").innerHTML =
    `${ic("loader", "ic-spin")} думает…`;
  log.appendChild(pending);
  log.scrollTop = log.scrollHeight;
  try {
    const r = await api("/api/assistant/ask", { step_id: current.step_id, question: q, history: chatHistory });
    chatHistory.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
    pending.innerHTML = bubble("ai", r.answer, r.note);
    await refreshState();
  } catch (e) {
    pending.innerHTML = bubble("err", e.message);
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
  if (tree) renderTree();
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

$("tree-body").innerHTML = loadingBox("дерево программы");
loadTree();
