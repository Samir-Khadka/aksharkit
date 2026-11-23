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
        get: (_, key) => self.attrs["data-" + String(key)],
        set: (_, key, value) => {
          self.attrs["data-" + String(key)] = String(value);
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
    .replace(/&quot;/g, '"');
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
  const log = { python: [], calls: [], scripts: [], fetched: [], pyodideOptions: null };
  let cdnFailures = options.cdnFailures || 0;
  const head = doc.all((n) => n.tagName === "head")[0];
  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    WebAssembly,
    location: { hash: options.hash || "" },
    navigator: { clipboard: { writeText: async (text) => void (log.copied = text) } },
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
  assert.deepEqual(page.log.calls, ["info", "normalize", "numbers", "dates", "tokenize", "translit"]);

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
  assert.equal(tabs.length, 6);
  assert.equal(panels.length, 6);
  const visible = () => panels.filter((p) => !p.hidden).map((p) => p.id);
  assert.deepEqual(visible(), ["panel-normalize"]);

  page.$("tab-dates").dispatch("click");
  assert.deepEqual(visible(), ["panel-dates"]);
  assert.deepEqual(tabs.filter((t) => t.attrs["aria-selected"] === "true").map((t) => t.id), ["tab-dates"]);
  assert.deepEqual(tabs.filter((t) => t.tabIndex === 0).map((t) => t.id), ["tab-dates"]);

  page.$("tab-dates").dispatch("keydown", { key: "ArrowRight" });
  assert.deepEqual(visible(), ["panel-tokenize"]);
  assert.ok(page.$("tab-tokenize").focused);
  page.$("tab-tokenize").dispatch("keydown", { key: "End" });
  assert.deepEqual(visible(), ["panel-preeti"]);
  page.$("tab-preeti").dispatch("keydown", { key: "ArrowRight" });
  assert.deepEqual(visible(), ["panel-normalize"]);
  page.$("tab-normalize").dispatch("keydown", { key: "ArrowLeft" });
  assert.deepEqual(visible(), ["panel-preeti"]);
  page.$("tab-preeti").dispatch("keydown", { key: "Home" });
  assert.deepEqual(visible(), ["panel-normalize"]);
  assert.match(page.$("panel-preeti").textContent, /Coming soon — needs a verified mapping/);
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
