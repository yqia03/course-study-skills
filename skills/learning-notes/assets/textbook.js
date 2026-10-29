/* Offline enhancement: the full book index is embedded by build_textbook.py. */
(() => {
  "use strict";
  const data = JSON.parse(document.getElementById("ln-book-data").textContent);
  const panel = document.getElementById("ln-panel");
  const menu = document.getElementById("ln-menu");
  const find = document.getElementById("ln-find");
  const input = document.getElementById("ln-search");
  const results = document.getElementById("ln-results");
  const resultList = document.getElementById("ln-result-list");
  const resultCount = document.getElementById("ln-result-count");
  const navigation = document.getElementById("ln-navigation");
  const tabs = [...panel.querySelectorAll('[role="tab"]')];
  let returnFocus = null;
  let shouldRestore = true;
  let readingPosition = {x: 0, y: 0};
  const normalize = value => value.normalize("NFKC").toLocaleLowerCase().replace(/\s+/g, " ").trim();
  const indexed = data.entries.map(entry => ({...entry, titleText: normalize(entry.title),
    aliasText: normalize(entry.aliases.join(" ")), bodyText: normalize(entry.text)}));

  function selectTab(tab, focus = true) {
    for (const item of tabs) {
      const active = item === tab;
      item.setAttribute("aria-selected", String(active));
      item.tabIndex = active ? 0 : -1;
      document.getElementById(item.getAttribute("aria-controls")).hidden = !active;
    }
    if (focus) tab.focus();
  }
  for (const [index, tab] of tabs.entries()) {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); selectTab(tabs[next]); }
    });
  }
  function search() {
    const query = normalize(input.value);
    const terms = query.split(" ").filter(Boolean);
    navigation.hidden = Boolean(query);
    results.hidden = !query;
    resultList.replaceChildren();
    if (!query) { resultCount.textContent = ""; return; }
    const matches = indexed.map(entry => {
      if (!terms.every(term => `${entry.titleText} ${entry.aliasText} ${entry.bodyText}`.includes(term))) return null;
      const titleHit = terms.every(term => entry.titleText.includes(term));
      const aliasHit = terms.every(term => `${entry.titleText} ${entry.aliasText}`.includes(term));
      return {entry, score: titleHit ? 3 : aliasHit ? 2 : 1};
    }).filter(Boolean).sort((a, b) => b.score - a.score);
    resultCount.textContent = matches.length ? `找到 ${matches.length} 个知识块` : "没有找到匹配内容；试试英文原名、缩写或更短的关键词。";
    for (const {entry} of matches) {
      const li = document.createElement("li");
      const link = document.createElement("a");
      const destination = new URL(entry.href, window.location.href);
      destination.searchParams.set("q", input.value.trim());
      link.href = destination.href;
      link.textContent = entry.title;
      const location = document.createElement("span");
      location.className = "search-location";
      location.textContent = entry.chapter;
      const context = document.createElement("p");
      // Normalize snippet text too, keeping offsets correct for case/width variants.
      const positions = terms.map(term => entry.bodyText.indexOf(term)).filter(position => position >= 0);
      const start = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 36);
      context.textContent = `${start ? "…" : ""}${entry.bodyText.slice(start, start + 170)}${entry.bodyText.length > start + 170 ? "…" : ""}`;
      li.append(location, link, context);
      resultList.append(li);
    }
  }
  function openPanel(searchMode) {
    returnFocus = document.activeElement;
    readingPosition = {x: window.scrollX, y: window.scrollY};
    shouldRestore = true;
    if (!searchMode) { input.value = ""; search(); }
    panel.showModal();
    document.documentElement.classList.add("ln-panel-open");
    menu.setAttribute("aria-expanded", "true");
    find.setAttribute("aria-expanded", "true");
    if (searchMode) input.focus({preventScroll: true});
    else tabs.find(tab => tab.getAttribute("aria-selected") === "true").focus({preventScroll: true});
    window.scrollTo(readingPosition.x, readingPosition.y);
  }
  panel.addEventListener("close", () => {
    document.documentElement.classList.remove("ln-panel-open");
    menu.setAttribute("aria-expanded", "false");
    find.setAttribute("aria-expanded", "false");
    if (shouldRestore) {
      if (returnFocus) returnFocus.focus({preventScroll: true});
      window.scrollTo(readingPosition.x, readingPosition.y);
    }
  });
  panel.addEventListener("click", event => {
    if (event.target !== panel) return;
    const rect = panel.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) panel.close();
  });
  document.getElementById("ln-close").addEventListener("click", () => panel.close());
  menu.addEventListener("click", () => openPanel(false));
  find.addEventListener("click", () => openPanel(true));
  input.addEventListener("input", search);

  function revealTarget() {
    const url = new URL(window.location.href);
    let id;
    try { id = decodeURIComponent(url.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    const terms = normalize(url.searchParams.get("q") || "").split(" ").filter(Boolean);
    if (terms.length) for (const detail of document.querySelectorAll("main details")) {
      if (terms.some(term => normalize(detail.textContent).includes(term))) detail.open = true;
    }
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === "DETAILS") parent.open = true;
    }
    target.setAttribute("tabindex", "-1");
    target.focus({preventScroll: true});
    target.scrollIntoView({block: "start"});
  }
  panel.addEventListener("click", event => {
    const link = event.target.closest("a[href]");
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const destination = new URL(link.href);
    if (!link.closest("#ln-result-list")) destination.searchParams.delete("q");
    shouldRestore = false;
    panel.close();
    if (destination.origin === window.location.origin && destination.pathname === window.location.pathname) {
      event.preventDefault();
      try { history.replaceState(null, "", destination.href); }
      catch { window.location.href = destination.href; return; }
      revealTarget();
    }
  });
  window.addEventListener("hashchange", revealTarget);
  if (window.location.hash) requestAnimationFrame(revealTarget);
  const printState = new Map();
  window.addEventListener("beforeprint", () => {
    for (const detail of document.querySelectorAll("main details")) {
      printState.set(detail, detail.open); detail.open = true;
    }
  });
  window.addEventListener("afterprint", () => {
    for (const [detail, open] of printState) detail.open = open;
    printState.clear();
  });
  menu.hidden = false;
  find.hidden = false;
})();
