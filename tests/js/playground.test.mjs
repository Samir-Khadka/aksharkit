// Smoke tests for site/app.js without a browser.
//
// What is real here: site/index.html (parsed into a small fake DOM),
// site/app.js (run unchanged), the archive built by scripts/build_site.py and
// the Python code inside it (run by the CPython in AKSHARKIT_PYTHON).
// What is faked: the DOM, fetch, and Pyodide itself. So these tests cover the
// page's wiring and the archive, NOT WebAssembly, the CDN or a real browser.
//
//   python scripts/build_site.py --out _site
//   AKSHARKIT_SITE=_site node --test tests/js/

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const SITE = path.resolve(process.env.AKSHARKIT_SITE || "_site");
const PYTHON = process.env.AKSHARKIT_PYTHON || "python3";
const VOID = new Set(["meta", "link", "input", "br", "hr", "img"]);

/* ---- a very small DOM -------------------------------------------------- */

// dataset.copyList <-> data-copy-list, as in a browser.
function kebab(key) {
  return String(key).replace(/[A-Z]/g, (letter) => "-" + letter.toLowerCase());
}

class Node {
  constructor(tag, attrs) {
    this.tagName = tag;
    this.attrs = attrs;
    this.children = [];
    this.parent = null;
    this.text = "";
    this.listeners = {};
    this.focused = false;
    const self = this;
    this.dataset = new Proxy(
      {},
      {
        get: (_, key) => self.attrs["data-" + kebab(key)],
        set: (_, key, value) => {
          self.attrs["data-" + kebab(key)] = String(value);
          return true;
        },
      }
    );
    this.classList = {
      toggle: (name, on) => {
        const names = new Set((self.attrs.class || "").split(/\s+/).filter(Boolean));
        if (on) names.add(name);
        else names.delete(name);
        self.attrs.class = Array.from(names).join(" ");
      },
      contains: (name) => (self.attrs.class || "").split(/\s+/).includes(name),
    };
  }
  get id() {
    return this.attrs.id;
  }
  get type() {
    return this.attrs.type || (this.tagName === "textarea" ? "textarea" : this.tagName === "select" ? "select-one" : "");
  }
  get className() {
    return this.attrs.class || "";
  }
  set className(value) {
    this.attrs.class = value;
  }
  get hidden() {
    return "hidden" in this.attrs;
  }
  set hidden(value) {
    if (value) this.attrs.hidden = "";
    else delete this.attrs.hidden;
  }
  get checked() {
    return "checked" in this.attrs;
  }
  set checked(value) {
    if (value) {
      if (this.attrs.type === "radio") {
        for (const other of this.root().all((n) => n.attrs.type === "radio" && n.attrs.name === this.attrs.name)) {
          delete other.attrs.checked;
        }
      }
      this.attrs.checked = "";
    } else delete this.attrs.checked;
  }
  get value() {
    if ("_value" in this) return this._value;
    if (this.tagName === "textarea") return this.textContent;
    if (this.tagName === "select") {
      const options = this.all((n) => n.tagName === "option");
      const chosen = options.find((o) => "selected" in o.attrs) || options[0];
      return chosen ? chosen.attrs.value : "";
    }
    return this.attrs.value || "";
  }
  set value(value) {
    this._value = String(value);
  }
  get textContent() {
    return this.text + this.children.map((c) => c.textContent).join("");
  }
  set textContent(value) {
    this.children = [];
    this.text = String(value);
  }
  get tabIndex() {
    return Number(this.attrs.tabindex || 0);
  }
  set tabIndex(value) {
    this.attrs.tabindex = String(value);
  }
  root() {
    let node = this;
    while (node.parent) node = node.parent;
    return node;
  }
  all(predicate, out = []) {
    for (const child of this.children) {
      if (predicate(child)) out.push(child);
      child.all(predicate, out);
    }
    return out;
  }
  getAttribute(name) {
    return name in this.attrs ? this.attrs[name] : null;
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
  }
  appendChild(child) {
    child.parent = this;
    this.children.push(child);
    return child;
  }
  replaceChildren(...nodes) {
    this.text = "";
    this.children = [];
    nodes.forEach((n) => this.appendChild(n));
  }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this);
  }
  focus() {
    this.focused = true;
  }
  addEventListener(type, fn) {
    (this.listeners[type] = this.listeners[type] || []).push(fn);
  }
  dispatch(type, extra = {}) {
    const event = { type, currentTarget: this, target: this, preventDefault() {}, ...extra };
    (this.listeners[type] || []).forEach((fn) => fn(event));
  }
}

function decode(text) {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#10;/g, "\n");
}

function parse(html) {
  const root = new Node("#document", {});
  let current = root;
  const pattern = /<!--[\s\S]*?-->|<!doctype[^>]*>|<\/([a-zA-Z0-9]+)\s*>|<([a-zA-Z0-9]+)((?:\s+[^\s=>\/]+(?:="[^"]*")?)*)\s*\/?>|([^<]+)/gi;
  let match;
  while ((match = pattern.exec(html))) {
    if (match[1]) {
      const tag = match[1].toLowerCase();
      assert.equal(current.tagName, tag, "mismatched closing tag </" + tag + "> inside <" + current.tagName + ">");
      current = current.parent;
    } else if (match[2]) {
      const attrs = {};
      for (const a of match[3].matchAll(/([^\s=>\/]+)(?:="([^"]*)")?/g)) {
        attrs[a[1].toLowerCase()] = a[2] === undefined ? "" : decode(a[2]);
      }
      const node = new Node(match[2].toLowerCase(), attrs);
      current.appendChild(node);
      if (!VOID.has(node.tagName)) current = node;
    } else if (match[4]) {
      const node = new Node("#text", {});
      node.text = decode(match[4]);
      current.appendChild(node);
    }
  }
  assert.equal(current, root, "unclosed <" + current.tagName + ">");
  return root;
}

function selectorPredicate(selector) {
  const match = /^\[([a-z-]+)(?:="([^"]*)")?\]$/.exec(selector);
  assert.ok(match, "the fake DOM only supports [attr] and [attr=\"value\"], got " + selector);
  return (node) => match[1] in node.attrs && (match[2] === undefined || node.attrs[match[1]] === match[2]);
}

/* ---- a fake Pyodide backed by real CPython -------------------------------- */

function makePyodide(log) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aksharkit-site-"));
  return {
    dir,
    unpackArchive(buffer, format, options) {
      log.unpack = { format, extractDir: options && options.extractDir, bytes: buffer.byteLength };
      const zip = path.join(dir, "archive.zip");
      fs.writeFileSync(zip, Buffer.from(buffer));
      const done = spawnSync(PYTHON, ["-c", "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])", zip, path.join(dir, "pkg")]);
      assert.equal(done.status, 0, String(done.stderr));
    },
    runPython(code) {
      log.python.push(code);
    },
    pyimport(name) {
      log.imported = name;
      return {
        run(tool, payload) {
          // -S -E: no site-packages, no environment: only the unpacked archive.
          const code =
            "import sys; sys.path.insert(0, sys.argv[1]); import " + name + " as g; " +
            "sys.stdout.reconfigure(encoding='utf-8'); sys.stdout.write(g.run(sys.argv[2], sys.argv[3]))";
          const done = spawnSync(PYTHON, ["-S", "-E", "-c", code, path.join(dir, "pkg"), tool, payload], { encoding: "utf-8" });
          assert.equal(done.status, 0, done.stderr);
          log.calls.push(tool);
          return done.stdout;
        },
      };
    },
  };
}

/* ---- running the page ------------------------------------------------------ */

async function settle(ms = 30) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function openPage(options = {}) {
  const doc = parse(fs.readFileSync(path.join(SITE, "index.html"), "utf-8"));
  const log = { python: [], calls: [], scripts: [], fetched: [], pyodideOptions: null, address: [], windowListeners: {} };
  let cdnFailures = options.cdnFailures || 0;
  const head = doc.all((n) => n.tagName === "head")[0];
  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    WebAssembly,
    location: { hash: options.hash || "", href: "https://example.test/aksharkit/" + (options.hash || "") },
    history: {
      replaceState(_state, _title, url) {
        log.address.push(url);
        sandbox.location.hash = url;
        sandbox.location.href = "https://example.test/aksharkit/" + url;
      },
    },
    addEventListener(type, fn) {
      log.windowListeners[type] = fn;
    },
    navigator: options.noClipboard ? {} : { clipboard: { writeText: async (text) => void (log.copied = text) } },
    fetch: async (url) => {
      log.fetched.push(url);
      const file = path.join(SITE, url);
      if (options.missingArchive || !fs.existsSync(file)) {
        return { ok: false, status: 404 };
      }
      const data = fs.readFileSync(file);
      return { ok: true, status: 200, arrayBuffer: async () => data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) };
    },
  };
  sandbox.document = {
    readyState: "complete",
    head: {
      appendChild(script) {
        head.appendChild(script);
        log.scripts.push({ src: script.src, integrity: script.integrity, crossOrigin: script.crossOrigin });
        setTimeout(() => {
          if (cdnFailures > 0) {
            cdnFailures -= 1;
            script.onerror();
            return;
          }
          sandbox.loadPyodide = async (opts) => {
            log.pyodideOptions = opts;
            return makePyodide(log);
          };
          script.onload();
        }, 0);
      },
    },
    getElementById: (id) => doc.all((n) => n.attrs.id === id)[0] || null,
    querySelectorAll: (selector) => doc.all(selectorPredicate(selector)),
    createElement: (tag) => new Node(tag, {}),
    addEventListener() {},
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(SITE, "app.js"), "utf-8"), sandbox, { filename: "app.js" });
  const page = {
    doc,
    log,
    sandbox,
    $: (id) => {
      const el = sandbox.document.getElementById(id);
      assert.ok(el, "no element with id " + id);
      return el;
    },
    out: (key) => {
      const els = sandbox.document.querySelectorAll('[data-out="' + key + '"]');
      assert.ok(els.length > 0, "no output for " + key);
      return els[0].textContent;
    },
    async waitFor(predicate, what) {
      for (let i = 0; i < 400; i += 1) {
        if (predicate()) return;
        await settle(25);
      }
      assert.fail("timed out waiting for " + what);
    },
    async edit(id, change) {
      const el = page.$(id);
      change(el);
      const before = log.calls.length;
      el.dispatch("input");
      el.dispatch("change");
      await page.waitFor(() => log.calls.length > before, "an update after editing " + id);
      await settle();
    },
  };
  return page;
}

async function ready(options) {
  const page = await openPage(options);
  await page.waitFor(() => page.$("status").dataset.state !== "loading", "the page to finish loading");
  await settle();
  return page;
}

/* ---- tests -------------------------------------------------------------------- */

test("the built site has what the page needs", () => {
  for (const name of ["index.html", "app.js", "style.css", "pkg/aksharkit.zip", "pkg/manifest.json"]) {
    assert.ok(fs.existsSync(path.join(SITE, name)), name + " is missing from " + SITE);
  }
  assert.ok(!fs.existsSync(path.join(SITE, "playground.py")), "the glue belongs inside the archive only");
});

test("boot loads the pinned Pyodide, unpacks the archive and fills every tab", async () => {
  const page = await ready();
  const manifest = JSON.parse(fs.readFileSync(path.join(SITE, "pkg/manifest.json"), "utf-8"));

  assert.equal(page.$("status").dataset.state, "ready");
  assert.ok(page.$("load-error").hidden);
  assert.match(page.$("status-text").textContent, new RegExp("^Ready\\. aksharkit " + manifest.version.replace(/\./g, "\\.") + " on Python 3\\."));
  assert.equal(page.$("version").textContent, "aksharkit " + manifest.version);

  assert.deepEqual(page.log.scripts.length, 1);
  assert.match(page.log.scripts[0].src, /^https:\/\/cdn\.jsdelivr\.net\/pyodide\/v\d+\.\d+\.\d+\/full\/pyodide\.js$/);
  assert.match(page.log.scripts[0].integrity, /^sha384-[A-Za-z0-9+/]{64}$/);
  assert.equal(page.log.scripts[0].crossOrigin, "anonymous");
  assert.equal(page.log.pyodideOptions.indexURL + "pyodide.js", page.log.scripts[0].src);
  assert.deepEqual(page.log.fetched, ["pkg/aksharkit.zip"]);
  assert.equal(page.log.unpack.format, "zip");
  assert.ok(page.log.python.some((code) => code.includes(page.log.unpack.extractDir) && code.includes("sys.path")));
  assert.equal(page.log.imported, "aksharkit_playground");
  assert.deepEqual(page.log.calls, ["info", "normalize", "aksharas", "numbers", "words", "dates", "calendar", "datemath", "tokenize", "sort", "detect", "translit"]);
  assert.deepEqual(page.log.address, [], "loading the page must not rewrite the address");

  assert.equal(page.out("normalize.text"), "राम घर गयो। आज पानी पर्\u200dयो॥");
  assert.match(page.out("normalize.note"), /^Changed: \d+ characters in, \d+ out\.$/);
  assert.equal(page.out("numbers.grouped"), "12,50,500.50");
  assert.equal(page.out("numbers.grouped_devanagari"), "१२,५०,५००.५०");
  assert.equal(page.out("numbers.devanagari"), "१२५०५००.५०");
  assert.match(page.out("numbers.words"), /^बाह्र लाख पचास हजार पाँच सय दशमलव/);
  assert.match(page.out("numbers.currency"), /रुपैयाँ पचास पैसा मात्र$/);
  assert.equal(page.out("dates.bs_iso"), "2083-08-07");
  assert.equal(page.out("dates.bs_long_ne"), "२०८३ मंसिर ७, सोमबार");
  assert.equal(page.out("dates.ad_long"), "23 November 2026, Monday");
  assert.equal(page.out("dates.fiscal_year"), "2083/84");
  assert.equal(page.out("translit.text"), "namaste, nepāla rāmro cha| dhanyavāda!");
  assert.match(page.out("translit.note"), /^IAST scheme/);
  assert.equal(page.$("out-translit-text").attrs.lang, "ne-Latn");

  assert.equal(page.out("words.number"), "1250500");
  assert.equal(page.out("words.grouped"), "12,50,500");
  assert.equal(page.out("words.grouped_devanagari"), "१२,५०,५००");
  assert.equal(page.out("words.respelt"), "बाह्र लाख पचास हजार पाँच सय");

  assert.equal(page.out("calendar.title"), "मंसिर २०८३");
  assert.equal(page.out("calendar.span"), "29 days: 17 November 2026 to 15 December 2026");
  assert.match(page.out("calendar.text"), /^मंसिर २०८३\nआइत\tसोम/);
  assert.equal(page.$("out-calendar-grid").attrs.lang, "ne");
  const headCells = page.$("out-calendar-head").children[0].children;
  assert.deepEqual(headCells.map((c) => c.textContent), ["आइत", "सोम", "मङ्गल", "बुध", "बिही", "शुक्र", "शनि"]);
  assert.ok(headCells.every((c) => c.tagName === "th" && c.attrs.scope === "col"));
  const weeks = page.$("out-calendar-weeks").children;
  assert.equal(weeks.length, 5);
  assert.deepEqual(weeks[0].children.map((c) => c.textContent), ["", "", "१", "२", "३", "४", "५"]);
  assert.deepEqual(weeks[0].children.map((c) => c.className), ["blank", "blank", "", "", "", "", ""]);
  assert.deepEqual(weeks[4].children.map((c) => c.textContent), ["२७", "२८", "२९", "", "", "", ""]);

  assert.equal(page.out("datemath.moved"), "2060-04-11");
  assert.equal(page.out("datemath.until"), "2083-08-07");
  assert.equal(page.out("datemath.gap"), "23 years, 6 months, 22 days");
  assert.equal(page.out("datemath.age"), "23");
  assert.match(page.out("datemath.days"), /^\d+$/);

  assert.equal(page.out("detect.script"), "Mixed (more than one script)");
  assert.match(page.out("detect.shares"), /^Devanagari [\d.]+% \(\d+\) · Latin [\d.]+% \(13\) · digits [\d.]+% \(10\)$/);
  const scriptChips = page.$("out-detect-tokens").children;
  assert.equal(scriptChips[0].textContent, "Facebook");
  assert.equal(scriptChips[0].className, "chip script-latin");
  assert.equal(scriptChips[1].textContent, "मा");
  assert.equal(scriptChips[1].attrs.lang, "ne");
  assert.equal(scriptChips[1].attrs.title, "devanagari");
  assert.match(page.out("detect.romanised"), /^Romanised-Nepali word list: 0% of the Latin-letter words are on it\. Not enough/);

  const chips = page.$("out-tokenize-tokens").children;
  assert.ok(chips.length > 10);
  assert.equal(chips[0].textContent, "डा");
  assert.ok(chips.some((c) => c.textContent === "२,९१,६४,५७८" && c.className.includes("kind-number")));
  assert.ok(chips.some((c) => c.className.includes("stop")));
  assert.deepEqual(
    page.$("out-tokenize-sentences").children.map((c) => c.textContent),
    ["डा. राम आए।", "नेपालको जनसंख्या २,९१,६४,५७८ छ।", "मूल्य रु. 99.50 हो।", "ठिक छ?"]
  );
  assert.match(page.out("tokenize.count"), /^\(\d+ tokens, \d+ words, 4 sentences\)$/);

  // Added in 0.5.
  const units = page.$("out-aksharas-units").children;
  assert.deepEqual(
    units.map((c) => c.textContent),
    ["न", "म", "स्ते", ",", "का", "ठ", "मा", "डौँ", "उ", "प", "त्य", "का", "मा", "स्वा", "ग", "त", "छ", "।"]
  );
  assert.ok(units.every((c) => c.tagName === "li" && c.className === "chip"));
  assert.equal(page.out("aksharas.count"), "(22 aksharas, 18 without spaces, from 36 characters)");
  assert.equal(page.out("aksharas.truncated"), "नमस्ते, काठमा…");
  assert.equal(page.out("sort.text"), "अंक\nआमा\nकं\nकमल\nकाम\nतारा\nहात\nक्षेत्र\nत्रिशूल\nज्ञान");
  assert.equal(page.out("sort.count"), "(10 lines)");
  assert.deepEqual(
    page.$("out-sort-lines").children.map((c) => c.textContent),
    ["अंक", "आमा", "कं", "कमल", "काम", "तारा", "हात", "क्षेत्र", "त्रिशूल", "ज्ञान"]
  );
  assert.equal(page.out("numbers.ordinal"), "पाँचौँ");
  assert.equal(page.out("dates.pattern"), "7 Mangsir 2083, Sombar");
  assert.equal(page.out("dates.pattern_ne"), "७ मंसिर २०८३, सोमबार");
});

test("editing a field re-runs the tool; errors show and clear", async () => {
  const page = await ready();

  await page.edit("dir-bs2ad", (el) => (el.checked = true));
  assert.ok(page.$("err-dates").hidden); // 2026-11-23 is also a valid BS date
  assert.equal(page.out("dates.ad_iso"), "1970-03-06");
  await page.edit("in-dates", (el) => (el.value = "२०८३-०१-०१"));
  assert.ok(page.$("err-dates").hidden);
  assert.equal(page.out("dates.ad_iso"), "2026-04-14");
  assert.equal(page.out("dates.ad_long"), "14 April 2026, Tuesday");

  await page.edit("in-dates", (el) => (el.value = "2090-01-01"));
  assert.ok(!page.$("err-dates").hidden);
  assert.match(page.$("err-dates").textContent, /outside the verified table/);
  assert.equal(page.out("dates.ad_iso"), "");

  await page.edit("in-dates", (el) => (el.value = "2062-02-10"));
  assert.match(page.$("err-dates").textContent, /disagree by one day/);
  await page.edit("opt-disputed", (el) => (el.checked = true));
  assert.ok(page.$("err-dates").hidden);
  assert.equal(page.out("dates.ad_iso"), "2005-05-23"); // 1 Jestha 2062 = 14 May 2005 in the majority reading

  await page.edit("in-numbers", (el) => (el.value = "abc"));
  assert.match(page.$("err-numbers").textContent, /not a number/);
  assert.equal(page.out("numbers.words"), "");
  await page.edit("in-numbers", (el) => (el.value = "100000000000000"));
  assert.ok(page.$("err-numbers").hidden);
  assert.equal(page.out("numbers.grouped"), "10,00,00,00,00,00,000");
  const words = page.doc.all((n) => n.attrs["data-out"] === "numbers.words")[0];
  assert.ok(words.classList.contains("failed"), "a number too large for words is reported in its own row");

  await page.edit("opt-scheme", (el) => (el.value = "simple"));
  assert.equal(page.out("translit.text"), "namaste, nepal ramro chha. dhanyavad!");
  assert.match(page.out("translit.note"), /approximate/);
  await page.edit("tr-devanagari", (el) => (el.checked = true));
  await page.edit("in-translit", (el) => (el.value = "mero ghar"));
  assert.equal(page.out("translit.text"), "मेरो घर");

  await page.edit("opt-danda", (el) => (el.checked = false));
  assert.match(page.out("normalize.text"), /\|\|$/);
});

test("today button, copy buttons and tabs", async () => {
  const page = await ready();

  page.$("in-dates").value = "";
  page.$("btn-today").dispatch("click");
  await settle(100);
  if (page.$("in-dates").value) {
    assert.match(page.$("in-dates").value, /^\d{4}-\d{2}-\d{2}$/);
    assert.equal(page.out("dates.ad_iso"), page.$("in-dates").value);
  } else {
    // After 13 April 2027 today is outside the calendar table.
    assert.match(page.$("err-dates").textContent, /outside the verified table/);
  }

  const copy = page.doc.all((n) => n.attrs["data-copy"] === "translit.text")[0];
  copy.dispatch("click");
  await settle();
  assert.equal(page.log.copied, page.out("translit.text"));

  const tabs = page.doc.all((n) => n.attrs.role === "tab");
  const panels = page.doc.all((n) => n.attrs.role === "tabpanel");
  assert.equal(tabs.length, 12);
  assert.equal(panels.length, 12);
  const visible = () => panels.filter((p) => !p.hidden).map((p) => p.id);
  assert.deepEqual(visible(), ["panel-normalize"]);

  page.$("tab-dates").dispatch("click");
  assert.deepEqual(visible(), ["panel-dates"]);
  assert.deepEqual(tabs.filter((t) => t.attrs["aria-selected"] === "true").map((t) => t.id), ["tab-dates"]);
  assert.deepEqual(tabs.filter((t) => t.tabIndex === 0).map((t) => t.id), ["tab-dates"]);

  assert.equal(page.log.address.at(-1), "#dates?direction=ad2bs&text=" + page.$("in-dates").value + "&allow_disputed=0&pattern=" + encodeURIComponent("%-d %B %Y, %A"));

  page.$("tab-dates").dispatch("keydown", { key: "ArrowRight" });
  assert.deepEqual(visible(), ["panel-calendar"]);
  assert.ok(page.$("tab-calendar").focused);
  assert.equal(page.log.address.at(-1), "#calendar?text=2083-08&devanagari=1&allow_disputed=0");
  page.$("tab-calendar").dispatch("keydown", { key: "End" });
  assert.equal(page.log.address.at(-1), "#preeti");
  assert.deepEqual(visible(), ["panel-preeti"]);
  page.$("tab-preeti").dispatch("keydown", { key: "ArrowRight" });
  assert.deepEqual(visible(), ["panel-normalize"]);
  page.$("tab-normalize").dispatch("keydown", { key: "ArrowLeft" });
  assert.deepEqual(visible(), ["panel-preeti"]);
  page.$("tab-preeti").dispatch("keydown", { key: "Home" });
  assert.deepEqual(visible(), ["panel-normalize"]);
  assert.match(page.$("panel-preeti").textContent, /Coming soon — needs a verified mapping/);
});

test("every result has a working copy button", async () => {
  const page = await ready();
  const buttons = page.doc.all((n) => "data-copy" in n.attrs);
  assert.ok(buttons.length >= 30);
  for (const button of buttons) {
    const key = button.attrs["data-copy"];
    page.log.copied = undefined;
    button.dispatch("click");
    await settle(5);
    assert.equal(page.log.copied, page.out(key), "copy button for " + key);
    assert.ok(page.log.copied.length > 0, key + " should not be empty");
    assert.equal(button.textContent, "Copied");
  }
  assert.match(page.out("calendar.text"), /\t/);

  const lists = page.doc.all((n) => "data-copy-list" in n.attrs);
  assert.deepEqual(lists.map((b) => b.attrs["data-copy-list"]), ["out-aksharas-units", "out-tokenize-tokens", "out-tokenize-sentences", "out-detect-tokens"]);
  lists[0].dispatch("click");
  await settle(5);
  assert.match(page.log.copied, /^न\nम\nस्ते\n,\nका\n/);
  lists[2].dispatch("click");
  await settle(5);
  assert.equal(page.log.copied, "डा. राम आए।\nनेपालको जनसंख्या २,९१,६४,५७८ छ।\nमूल्य रु. 99.50 हो।\nठिक छ?");
  lists[3].dispatch("click");
  await settle(5);
  assert.match(page.log.copied, /^Facebook\tlatin\nमा\tdevanagari\n/);

  await settle(1300);
  assert.ok(buttons.every((b) => b.textContent === "Copy"), "the label comes back");
});

test("copying without clipboard access says so instead of failing", async () => {
  const page = await ready({ noClipboard: true });
  const button = page.doc.all((n) => n.attrs["data-copy"] === "numbers.words")[0];
  button.dispatch("click");
  await settle(5);
  assert.equal(button.textContent, "Copy is not available");
});

test("example buttons fill the input and run the tool", async () => {
  const page = await ready();
  const examples = page.doc.all((n) => "data-example" in n.attrs);
  assert.ok(examples.length >= 37);
  const pick = (target, value) => {
    const found = examples.find((b) => b.attrs["data-example"] === target && b.attrs["data-value"] === value);
    assert.ok(found, "no example " + value + " for " + target);
    return found;
  };

  page.$("tab-words").dispatch("click");
  pick("in-words", "एक लाख पच्चीस हजार").dispatch("click");
  assert.equal(page.$("in-words").value, "एक लाख पच्चीस हजार");
  assert.equal(page.out("words.number"), "125000");
  assert.ok(page.$("in-words").focused);
  assert.equal(page.log.address.at(-1), "#words?text=" + encodeURIComponent("एक लाख पच्चीस हजार"));

  pick("in-words", "पाँच सय रुपैयाँ पचास पैसा मात्र").dispatch("click");
  assert.equal(page.out("words.number"), "500.50");
  pick("in-calendar", "2083-12").dispatch("click");
  assert.equal(page.out("calendar.title"), "चैत २०८३");
  pick("in-detect", "timi kasto cha? malai ramro lagyo").dispatch("click");
  assert.equal(page.out("detect.script"), "Latin");
  assert.match(page.out("detect.romanised"), /looks like Nepali typed in Latin letters/);
  pick("in-datemath", "2083-03-32").dispatch("click");
  assert.equal(page.out("datemath.moved"), "2083-06-28");

  // Every example on the page is accepted by its tool.
  for (const button of examples) {
    button.dispatch("click");
    const tool = page.$(button.attrs["data-example"]).attrs["data-tool"];
    assert.ok(page.$("err-" + tool).hidden, button.attrs["data-value"] + ": " + page.$("err-" + tool).textContent);
  }
});

test("words to number, calendar and date maths report errors", async () => {
  const page = await ready();
  await page.edit("in-words", (el) => (el.value = "एक एक"));
  assert.match(page.$("err-words").textContent, /cannot follow each other/);
  assert.equal(page.out("words.number"), "");
  await page.edit("in-words", (el) => (el.value = "दश"));
  assert.ok(page.$("err-words").hidden);
  assert.equal(page.out("words.number"), "10");

  await page.edit("in-calendar", (el) => (el.value = "2062-01"));
  assert.match(page.$("err-calendar").textContent, /disagree/);
  assert.equal(page.$("out-calendar-weeks").children.length, 0);
  assert.equal(page.out("calendar.text"), "");
  await page.edit("opt-calendar-disputed", (el) => (el.checked = true));
  assert.ok(page.$("err-calendar").hidden);
  await page.edit("opt-calendar-ne", (el) => (el.checked = false));
  assert.equal(page.out("calendar.title"), "Baishakh 2062");
  assert.equal(page.$("out-calendar-grid").attrs.lang, "en");

  await page.edit("in-datemath-until", (el) => (el.value = "2050-01-01"));
  assert.ok(page.$("err-datemath").hidden);
  const gap = page.doc.all((n) => n.attrs["data-out"] === "datemath.gap")[0];
  assert.ok(gap.classList.contains("failed"));
  assert.match(gap.textContent, /before the start date/);
  assert.equal(page.out("datemath.moved"), "2060-04-11");
  await page.edit("in-datemath-days", (el) => (el.value = "x"));
  assert.match(page.$("err-datemath").textContent, /whole number/);
});

test("the address carries the state, so a result can be shared as a link", async () => {
  const first = await ready();
  first.$("tab-numbers").dispatch("click");
  await first.edit("in-numbers", (el) => (el.value = "१२३४"));
  await first.edit("opt-only", (el) => (el.checked = false));
  const link = first.log.address.at(-1);
  assert.equal(link, "#numbers?text=" + encodeURIComponent("१२३४") + "&only=0&ordinal=5");

  first.$("tab-numbers").dispatch("click");
  first.$("btn-share").dispatch("click");
  await settle(5);
  assert.equal(first.log.copied, "https://example.test/aksharkit/" + link);
  assert.equal(first.$("btn-share").textContent, "Copied");

  const second = await ready({ hash: link });
  const panels = second.doc.all((n) => n.attrs.role === "tabpanel");
  assert.deepEqual(panels.filter((p) => !p.hidden).map((p) => p.id), ["panel-numbers"]);
  assert.equal(second.$("in-numbers").value, "१२३४");
  assert.equal(second.$("opt-only").checked, false);
  assert.equal(second.out("numbers.grouped"), "1,234");
  assert.doesNotMatch(second.out("numbers.currency"), /मात्र$/);
  assert.equal(second.out("dates.bs_iso"), "2083-08-07", "other tabs keep their defaults");

  const third = await ready({ hash: "#translit?direction=devanagari&scheme=simple&text=mero%20ghar" });
  assert.equal(third.out("translit.text"), "मेरो घर");
  assert.equal(third.$("out-translit-text").attrs.lang, "ne");
  assert.ok(third.$("tr-devanagari").checked);
  assert.ok(!third.$("tr-roman").checked);

  const fourth = await ready({ hash: "#dates?direction=bs2ad&text=2083-01-01&allow_disputed=0" });
  assert.equal(fourth.out("dates.ad_iso"), "2026-04-14");
});

test("odd addresses are ignored, long inputs are left out of the link", async () => {
  for (const hash of ["#nope?text=1", "#numbers?text=%E0%A4%A", "#numbers?=5&&x", "#?", "#numbers?unknown=1"]) {
    const page = await ready({ hash });
    assert.equal(page.$("status").dataset.state, "ready", hash);
    assert.equal(page.out("numbers.grouped"), "12,50,500.50", hash);
  }
  const page = await ready();
  await page.edit("in-normalize", (el) => (el.value = "नेपाल ".repeat(400)));
  assert.equal(page.log.address.at(-1), "#normalize");
});

test("a changed address re-reads the state", async () => {
  const page = await ready();
  assert.equal(typeof page.log.windowListeners.hashchange, "function");
  page.sandbox.location.hash = "#words?text=" + encodeURIComponent("दुई करोड");
  page.log.windowListeners.hashchange();
  assert.equal(page.out("words.number"), "20000000");
  const panels = page.doc.all((n) => n.attrs.role === "tabpanel");
  assert.deepEqual(panels.filter((p) => !p.hidden).map((p) => p.id), ["panel-words"]);
  page.sandbox.location.hash = "#preeti";
  page.log.windowListeners.hashchange();
  assert.deepEqual(panels.filter((p) => !p.hidden).map((p) => p.id), ["panel-preeti"]);
});

test("a tab named in the address is opened", async () => {
  const page = await ready({ hash: "#translit" });
  const panels = page.doc.all((n) => n.attrs.role === "tabpanel");
  assert.deepEqual(panels.filter((p) => !p.hidden).map((p) => p.id), ["panel-translit"]);
});

test("a CDN failure shows the error state, and Try again recovers", async () => {
  const page = await ready({ cdnFailures: 1 });
  assert.equal(page.$("status").dataset.state, "error");
  assert.ok(!page.$("load-error").hidden);
  assert.match(page.$("load-error-text").textContent, /cdn\.jsdelivr\.net/);
  assert.equal(page.log.calls.length, 0);
  assert.equal(page.out("normalize.text"), "");

  page.$("retry").dispatch("click");
  await page.waitFor(() => page.$("status").dataset.state === "ready", "the retry to succeed");
  assert.ok(page.$("load-error").hidden);
  assert.equal(page.log.scripts.length, 2);
  assert.equal(page.out("dates.bs_iso"), "2083-08-07");
});

test("a missing archive shows the error state", async () => {
  const page = await ready({ missingArchive: true });
  assert.equal(page.$("status").dataset.state, "error");
  assert.match(page.$("load-error-text").textContent, /pkg\/aksharkit\.zip \(HTTP 404\)/);
});

test("aksharas, sort, ordinals and date patterns", async () => {
  const page = await ready();

  await page.edit("in-aksharas", (el) => (el.value = "श्रीमान् पर्\u200dयो"));
  assert.deepEqual(page.$("out-aksharas-units").children.map((c) => c.textContent), ["श्री", "मा", "न्", "प", "र्\u200dयो"]);
  assert.equal(page.out("aksharas.count"), "(6 aksharas, 5 without spaces, from 15 characters)");
  assert.equal(page.out("aksharas.truncated"), "श्रीमान् पर्\u200dयो");
  await page.edit("in-aksharas-limit", (el) => (el.value = "२"));
  assert.equal(page.out("aksharas.truncated"), "श्रीमा…");
  await page.edit("opt-aksharas-suffix", (el) => (el.checked = false));
  assert.equal(page.out("aksharas.truncated"), "श्रीमा");
  await page.edit("in-aksharas-limit", (el) => (el.value = "two"));
  const cut = page.doc.all((n) => n.attrs["data-out"] === "aksharas.truncated")[0];
  assert.ok(cut.classList.contains("failed"), "a bad limit is reported in its own row");
  assert.match(cut.textContent, /whole number/);
  assert.equal(page.$("out-aksharas-units").children.length, 5, "the split is still shown");
  await page.edit("in-aksharas-limit", (el) => (el.value = ""));
  assert.equal(page.out("aksharas.truncated"), "श्रीमान् पर्\u200dयो");
  await page.edit("in-aksharas", (el) => (el.value = ""));
  assert.equal(page.$("out-aksharas-units").children.length, 0);
  assert.equal(page.out("aksharas.count"), "(0 aksharas, 0 without spaces, from 0 characters)");

  await page.edit("opt-sort-conjuncts", (el) => (el.checked = false));
  assert.equal(page.out("sort.text"), "अंक\nआमा\nकं\nकमल\nकाम\nक्षेत्र\nज्ञान\nतारा\nत्रिशूल\nहात");
  await page.edit("opt-sort-reverse", (el) => (el.checked = true));
  assert.match(page.out("sort.text"), /^हात\nत्रिशूल\n/);
  await page.edit("in-sort", (el) => (el.value = "ख\n\nक\n  ख  \n"));
  assert.equal(page.out("sort.text"), "ख\nख\nक");
  assert.equal(page.out("sort.count"), "(3 lines)");
  await page.edit("opt-sort-unique", (el) => (el.checked = true));
  assert.equal(page.out("sort.text"), "ख\nक");
  await page.edit("in-sort", (el) => (el.value = "क"));
  assert.equal(page.out("sort.count"), "(1 line)");
  await page.edit("in-sort", (el) => (el.value = ""));
  assert.equal(page.out("sort.text"), "");
  assert.equal(page.$("out-sort-lines").children.length, 0);
  assert.ok(page.$("err-sort").hidden);

  page.$("tab-sort").dispatch("click");
  const names = page.doc.all((n) => n.attrs["data-example"] === "in-sort")[0];
  names.dispatch("click");
  assert.equal(page.$("in-sort").value.split("\n").length, 9, "an example holds one item per line");
  assert.match(page.log.address.at(-1), /^#sort\?text=.*%0A.*&conjunct_letters=0&reverse=1&unique=1$/);

  await page.edit("in-numbers-ordinal", (el) => (el.value = "२१"));
  assert.equal(page.out("numbers.ordinal"), "एक्काइसौँ");
  assert.equal(page.out("numbers.grouped"), "12,50,500.50", "the other rows are untouched");
  await page.edit("in-numbers-ordinal", (el) => (el.value = "101"));
  const ordinal = page.doc.all((n) => n.attrs["data-out"] === "numbers.ordinal")[0];
  assert.ok(ordinal.classList.contains("failed"));
  assert.match(ordinal.textContent, /1 to 100/);
  assert.ok(page.$("err-numbers").hidden);

  await page.edit("in-dates-pattern", (el) => (el.value = "%d/%m/%y (%a)"));
  assert.equal(page.out("dates.pattern"), "07/08/83 (Som)");
  assert.equal(page.out("dates.pattern_ne"), "०७/०८/८३ (सोम)");
  await page.edit("in-dates-pattern", (el) => (el.value = "%Q"));
  const pattern = page.doc.all((n) => n.attrs["data-out"] === "dates.pattern")[0];
  assert.ok(pattern.classList.contains("failed"));
  assert.match(pattern.textContent, /unknown token/);
  assert.equal(page.out("dates.bs_iso"), "2083-08-07", "a bad pattern does not blank the conversion");
  assert.ok(page.$("err-dates").hidden);
  await page.edit("in-dates-pattern", (el) => (el.value = "%Y %B %-d"));
  assert.ok(!pattern.classList.contains("failed"));

  // A BS date may be typed with a month name.
  await page.edit("dir-bs2ad", (el) => (el.checked = true));
  await page.edit("in-dates", (el) => (el.value = "२०८३ मंसिर ८"));
  assert.ok(page.$("err-dates").hidden);
  assert.equal(page.out("dates.ad_iso"), "2026-11-24");
  await page.edit("in-dates", (el) => (el.value = "8 Mangsir 2083"));
  assert.equal(page.out("dates.ad_iso"), "2026-11-24");
  await page.edit("in-dates", (el) => (el.value = "8 Mangsir 83"));
  assert.match(page.$("err-dates").textContent, /four digits/);
  assert.equal(page.out("dates.pattern"), "");
});

test("new tabs open from a link and keep their state", async () => {
  const hash = "#aksharas?text=" + encodeURIComponent("स्त्री शक्ति") + "&limit=1&suffix=0";
  const page = await ready({ hash });
  const panels = page.doc.all((n) => n.attrs.role === "tabpanel");
  assert.deepEqual(panels.filter((p) => !p.hidden).map((p) => p.id), ["panel-aksharas"]);
  assert.equal(page.out("aksharas.truncated"), "स्त्री");
  assert.deepEqual(page.$("out-aksharas-units").children.map((c) => c.textContent), ["स्त्री", "श", "क्ति"]);
  page.$("btn-share").dispatch("click");
  await settle(5);
  assert.equal(page.log.copied, "https://example.test/aksharkit/" + hash);

  const sorted = await ready({ hash: "#sort?text=" + encodeURIComponent("ख\nक\nज्ञ\nग") + "&conjunct_letters=0&reverse=0&unique=0" });
  assert.deepEqual(sorted.doc.all((n) => n.attrs.role === "tabpanel").filter((p) => !p.hidden).map((p) => p.id), ["panel-sort"]);
  assert.equal(sorted.out("sort.text"), "क\nख\nग\nज्ञ");
  assert.equal(sorted.$("opt-sort-conjuncts").checked, false);

  const dated = await ready({ hash: "#dates?direction=bs2ad&text=" + encodeURIComponent("7 Mangsir 2083") + "&pattern=" + encodeURIComponent("%A") });
  assert.equal(dated.out("dates.ad_iso"), "2026-11-23");
  assert.equal(dated.out("dates.pattern_ne"), "सोमबार");
});

test("the address follows the tab on screen, even with an edit still pending", async () => {
  const page = await ready();
  page.$("tab-numbers").dispatch("click");
  assert.match(page.log.address.at(-1), /^#numbers\?/);

  // Typing, then clicking another tab before the debounce has run: leaving the
  // field fires "change", which used to put the old tab back in the address.
  const field = page.$("in-numbers");
  field.value = "42";
  field.dispatch("input");
  field.dispatch("change");
  page.$("tab-dates").dispatch("click");
  assert.match(page.log.address.at(-1), /^#dates\?/, "the address changes at once");
  await settle(400);
  assert.match(page.log.address.at(-1), /^#dates\?/, "and is not put back by the pending edit");
  assert.equal(page.out("numbers.grouped"), "42", "the pending edit still ran");

  // The same with an example button on a tab that is no longer on screen.
  page.$("tab-preeti").dispatch("click");
  assert.equal(page.log.address.at(-1), "#preeti");
  page.$("in-words").value = "दुई";
  page.$("in-words").dispatch("input");
  await settle(400);
  assert.equal(page.log.address.at(-1), "#preeti");
  assert.equal(page.out("words.number"), "2");

  // Going back shows the edited value in the address.
  page.$("tab-numbers").dispatch("click");
  assert.equal(page.log.address.at(-1), "#numbers?text=42&only=1&ordinal=5");
});
