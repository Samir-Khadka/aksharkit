/* aksharkit playground.
 *
 * Loads Pyodide (Python compiled to WebAssembly) from the jsDelivr CDN,
 * unpacks pkg/aksharkit.zip (the library's own source files, built by
 * scripts/build_site.py) and calls aksharkit_playground.run(tool, json).
 * Every result on the page comes from the Python package itself.
 */
"use strict";

const PYODIDE_VERSION = "0.29.5";
const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/";
// SHA-384 of pyodide.js for exactly this version (jsDelivr files are immutable).
const PYODIDE_INTEGRITY =
  "sha384-VR47TfKeAmT7vMej7bwOVg0tHTQLLGMSIpsXtFMCZG5OpKZSIXoSLtGY//qHcxc6";
const PACKAGE_ARCHIVE = "pkg/aksharkit.zip";
// The build stamps "?v=<hash>" on this script's address (scripts/build_site.py).
// The archive is fetched with the same stamp, so a browser that cached an older
// page never mixes a new interface with an old library.
const ASSET_QUERY = (function () {
  try {
    const self = typeof document !== "undefined" ? document.currentScript : null;
    return self && self.src ? new URL(self.src).search : "";
  } catch (error) {
    return "";
  }
})();
const PACKAGE_DIR = "/home/pyodide/aksharkit_pkg";
const TOOLS = ["normalize", "numbers", "words", "dates", "calendar", "datemath", "tokenize", "detect", "translit"];
const MAX_LINK_LENGTH = 1800; // longer inputs are left out of the shareable link
const DEBOUNCE_MS = 150;

let runPython = null; // set once the library is loaded
let booting = false;

function byId(id) {
  return document.getElementById(id);
}

function all(selector) {
  return Array.from(document.querySelectorAll(selector));
}

/* ---- status ------------------------------------------------------------ */

function setStatus(state, text) {
  const status = byId("status");
  status.dataset.state = state;
  byId("status-text").textContent = text;
}

function showLoadError(message) {
  setStatus("error", "Not running.");
  byId("load-error-text").textContent = message;
  byId("load-error").hidden = false;
}

/* ---- loading Pyodide and the library ----------------------------------- */

function loadScript(src, integrity) {
  return new Promise(function (resolve, reject) {
    const script = document.createElement("script");
    script.src = src;
    script.integrity = integrity;
    script.crossOrigin = "anonymous";
    script.onload = function () {
      resolve();
    };
    script.onerror = function () {
      script.remove();
      reject(new Error("Could not download the Python runtime from cdn.jsdelivr.net."));
    };
    document.head.appendChild(script);
  });
}

async function boot() {
  if (booting || runPython) {
    return;
  }
  booting = true;
  byId("load-error").hidden = true;
  try {
    if (typeof WebAssembly !== "object") {
      throw new Error("This browser does not support WebAssembly.");
    }
    setStatus("loading", "Loading the Python runtime. The first visit downloads about 5 MB.");
    if (typeof globalThis.loadPyodide !== "function") {
      await loadScript(PYODIDE_BASE + "pyodide.js", PYODIDE_INTEGRITY);
    }
    const pyodide = await globalThis.loadPyodide({ indexURL: PYODIDE_BASE });

    setStatus("loading", "Loading aksharkit.");
    const response = await fetch(PACKAGE_ARCHIVE + ASSET_QUERY);
    if (!response.ok) {
      throw new Error("Could not load " + PACKAGE_ARCHIVE + " (HTTP " + response.status + ").");
    }
    const archive = await response.arrayBuffer();
    const dir = JSON.stringify(PACKAGE_DIR);
    pyodide.runPython("import os\nos.makedirs(" + dir + ", exist_ok=True)\n");
    pyodide.unpackArchive(archive, "zip", { extractDir: PACKAGE_DIR });
    pyodide.runPython(
      "import importlib, sys\n" +
        "if " + dir + " not in sys.path:\n" +
        "    sys.path.insert(0, " + dir + ")\n" +
        "importlib.invalidate_caches()\n"
    );
    const glue = pyodide.pyimport("aksharkit_playground");
    runPython = function (tool, payload) {
      return JSON.parse(glue.run(tool, JSON.stringify(payload)));
    };

    const info = runPython("info", {});
    if (!info.ok) {
      throw new Error(info.error);
    }
    byId("version").textContent = "aksharkit " + info.result.version;
    setStatus(
      "ready",
      "Ready. aksharkit " + info.result.version + " on Python " + info.result.python + ", running in your browser."
    );
    TOOLS.forEach(function (tool) {
      update(tool);
    });
  } catch (error) {
    runPython = null;
    showLoadError(error && error.message ? error.message : String(error));
  } finally {
    booting = false;
  }
}

/* ---- reading the form ---------------------------------------------------- */

function collect(tool) {
  const payload = {};
  all('[data-tool="' + tool + '"]').forEach(function (el) {
    const field = el.dataset.field;
    if (el.type === "checkbox") {
      payload[field] = el.checked;
    } else if (el.type === "radio") {
      if (el.checked) {
        payload[field] = el.value;
      }
    } else {
      payload[field] = el.value;
    }
  });
  return payload;
}

/* ---- writing results ------------------------------------------------------ */

function setOut(key, text, failed) {
  all('[data-out="' + key + '"]').forEach(function (el) {
    el.textContent = text;
    el.classList.toggle("failed", Boolean(failed));
  });
}

function clearOutputs(tool) {
  all("[data-out]").forEach(function (el) {
    if (el.dataset.out.split(".")[0] === tool) {
      el.textContent = "";
      el.classList.toggle("failed", false);
    }
  });
  if (tool === "tokenize") {
    byId("out-tokenize-tokens").replaceChildren();
    byId("out-tokenize-sentences").replaceChildren();
  }
  if (tool === "detect") {
    byId("out-detect-tokens").replaceChildren();
  }
  if (tool === "calendar") {
    byId("out-calendar-head").replaceChildren();
    byId("out-calendar-weeks").replaceChildren();
  }
}

function showError(tool, message) {
  const box = byId("err-" + tool);
  box.textContent = message;
  box.hidden = !message;
}

function item(tag, text, className) {
  const el = document.createElement(tag);
  el.textContent = text;
  if (className) {
    el.className = className;
  }
  return el;
}

function fill(parent, nodes) {
  parent.replaceChildren.apply(parent, nodes);
}

function setRows(tool, r) {
  Object.keys(r).forEach(function (key) {
    setOut(tool + "." + key, r[key].value, !r[key].ok);
  });
}

function percent(share) {
  return Math.round(share * 1000) / 10 + "%";
}

const SCRIPT_NAMES = {
  devanagari: "Devanagari",
  latin: "Latin",
  digits: "Digits only",
  mixed: "Mixed (more than one script)",
  other: "Another script",
  none: "Nothing to classify",
};

const RENDER = {
  normalize: function (r) {
    setOut("normalize.text", r.text);
    setOut(
      "normalize.note",
      r.changed
        ? "Changed: " + r.before + " characters in, " + r.after + " out."
        : "Already in canonical form; nothing changed."
    );
  },
  numbers: function (r) {
    setRows("numbers", r);
  },
  words: function (r) {
    setRows("words", r);
  },
  datemath: function (r) {
    setRows("datemath", r);
  },
  calendar: function (r) {
    setOut("calendar.title", r.title);
    setOut("calendar.span", r.span);
    setOut("calendar.text", r.text);
    const table = byId("out-calendar-grid");
    table.setAttribute("lang", r.lang);
    const headRow = item("tr", "", "");
    fill(
      headRow,
      r.head.map(function (name) {
        const cell = item("th", name, "");
        cell.setAttribute("scope", "col");
        return cell;
      })
    );
    fill(byId("out-calendar-head"), [headRow]);
    fill(
      byId("out-calendar-weeks"),
      r.weeks.map(function (week) {
        const row = item("tr", "", "");
        fill(
          row,
          week.map(function (day) {
            return item("td", day, day ? "" : "blank");
          })
        );
        return row;
      })
    );
  },
  detect: function (r) {
    setOut("detect.script", SCRIPT_NAMES[r.script] || r.script);
    const parts = [];
    [
      ["devanagari", "Devanagari"],
      ["latin", "Latin"],
      ["digit", "digits"],
      ["other", "other"],
    ].forEach(function (pair) {
      if (r.counts[pair[0]] > 0) {
        parts.push(pair[1] + " " + percent(r.shares[pair[0]]) + " (" + r.counts[pair[0]] + ")");
      }
    });
    setOut("detect.shares", parts.length ? parts.join(" · ") : "No letters or digits.");
    fill(
      byId("out-detect-tokens"),
      r.tokens.map(function (t) {
        const chip = item("li", t.text, "chip script-" + t.script);
        chip.setAttribute("title", t.script);
        if (t.script === "devanagari") {
          chip.setAttribute("lang", "ne");
        }
        return chip;
      })
    );
    let note = "";
    if (r.counts.latin > 0) {
      note =
        "Romanised-Nepali word list: " +
        percent(r.romanised_score) +
        " of the Latin-letter words are on it. " +
        (r.romanised
          ? "This looks like Nepali typed in Latin letters. That is a rough guess from a short word list, not a language test."
          : "Not enough to call it romanised Nepali. The check is a rough guess from a short word list.");
    }
    setOut("detect.romanised", note);
  },
  dates: function (r) {
    Object.keys(r).forEach(function (key) {
      setOut("dates." + key, r[key]);
    });
  },
  tokenize: function (r) {
    const tokens = byId("out-tokenize-tokens");
    tokens.replaceChildren.apply(
      tokens,
      r.tokens.map(function (t) {
        return item("li", t.text, "chip kind-" + t.kind + (t.stop ? " stop" : ""));
      })
    );
    const sentences = byId("out-tokenize-sentences");
    sentences.replaceChildren.apply(
      sentences,
      r.sentences.map(function (s) {
        return item("li", s, "");
      })
    );
    setOut(
      "tokenize.count",
      "(" + r.tokens.length + " tokens, " + r.words + " words, " + r.sentences.length + " sentences)"
    );
  },
  translit: function (r) {
    setOut("translit.text", r.text);
    byId("out-translit-text").setAttribute("lang", r.lang);
    setOut(
      "translit.note",
      r.approximate
        ? "Simple scheme: approximate. It cannot tell t from ṭ, d from ḍ, s from ś or ṣ, or short vowels from long ones."
        : "IAST scheme: converting this back gives the original text."
    );
  },
};

function update(tool, fromUser) {
  if (fromUser) {
    writeState(tool);
  }
  if (!runPython) {
    return;
  }
  let answer;
  try {
    answer = runPython(tool, collect(tool));
  } catch (error) {
    answer = { ok: false, error: "Unexpected error: " + (error && error.message ? error.message : error) };
  }
  if (answer.ok) {
    showError(tool, "");
    RENDER[tool](answer.result);
  } else {
    clearOutputs(tool);
    showError(tool, answer.error);
  }
}

/* ---- state in the address ---------------------------------------------------
 *
 * The part after "#" is "<tab>" or "<tab>?<field>=<value>&...", so a result
 * can be shared as a link. Nothing is stored on the device or sent anywhere:
 * browsers do not send the part after "#" to the server.
 */

function readState() {
  const raw = String(location.hash || "").replace(/^#/, "");
  const cut = raw.indexOf("?");
  const state = { tab: cut < 0 ? raw : raw.slice(0, cut), fields: {} };
  if (cut >= 0) {
    raw
      .slice(cut + 1)
      .split("&")
      .forEach(function (pair) {
        const eq = pair.indexOf("=");
        if (eq <= 0) {
          return;
        }
        try {
          state.fields[decodeURIComponent(pair.slice(0, eq))] = decodeURIComponent(pair.slice(eq + 1));
        } catch (error) {
          // a broken escape in a hand-edited link: skip that field
        }
      });
  }
  return state;
}

function applyState(state) {
  const tab = byId("tab-" + state.tab);
  if (!tab) {
    return false;
  }
  selectTab(tab, false);
  all('[data-tool="' + state.tab + '"]').forEach(function (el) {
    const field = el.dataset.field;
    if (!Object.prototype.hasOwnProperty.call(state.fields, field)) {
      return;
    }
    const value = state.fields[field];
    if (el.type === "checkbox") {
      el.checked = value === "1";
    } else if (el.type === "radio") {
      if (el.value === value) {
        el.checked = true;
      }
    } else {
      el.value = value;
    }
  });
  return true;
}

function stateFor(name) {
  if (TOOLS.indexOf(name) < 0) {
    return "#" + name;
  }
  const payload = collect(name);
  const pairs = Object.keys(payload).map(function (field) {
    const value = payload[field];
    const text = value === true ? "1" : value === false ? "0" : String(value);
    return encodeURIComponent(field) + "=" + encodeURIComponent(text);
  });
  const hash = "#" + name + "?" + pairs.join("&");
  return hash.length > MAX_LINK_LENGTH ? "#" + name : hash;
}

function writeState(name) {
  if (typeof history === "object" && history && typeof history.replaceState === "function") {
    history.replaceState(null, "", stateFor(name));
  }
}

function currentTabName() {
  const selected = all('[role="tab"]').filter(function (tab) {
    return tab.getAttribute("aria-selected") === "true";
  })[0];
  return selected ? selected.id.replace("tab-", "") : TOOLS[0];
}

/* ---- tabs ------------------------------------------------------------------ */

function selectTab(tab, focus) {
  all('[role="tab"]').forEach(function (other) {
    const selected = other === tab;
    other.setAttribute("aria-selected", selected ? "true" : "false");
    other.tabIndex = selected ? 0 : -1;
    byId(other.getAttribute("aria-controls")).hidden = !selected;
  });
  if (focus) {
    tab.focus();
  }
  if (typeof tab.scrollIntoView === "function") {
    tab.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
}

function onTabKey(event) {
  const tabs = all('[role="tab"]');
  const index = tabs.indexOf(event.currentTarget);
  let next = -1;
  if (event.key === "ArrowRight") {
    next = (index + 1) % tabs.length;
  } else if (event.key === "ArrowLeft") {
    next = (index - 1 + tabs.length) % tabs.length;
  } else if (event.key === "Home") {
    next = 0;
  } else if (event.key === "End") {
    next = tabs.length - 1;
  }
  if (next >= 0) {
    event.preventDefault();
    selectTab(tabs[next], true);
    writeState(currentTabName());
  }
}

/* ---- wiring ------------------------------------------------------------------ */

function debounce(fn, wait) {
  let timer = null;
  return function () {
    clearTimeout(timer);
    timer = setTimeout(fn, wait);
  };
}

function flash(button, text) {
  const label = button.dataset.label || button.textContent;
  button.dataset.label = label;
  button.textContent = text;
  setTimeout(function () {
    button.textContent = label;
  }, 1200);
}

function copyText(button, text) {
  if (!text) {
    return;
  }
  if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
    flash(button, "Copy is not available");
    return;
  }
  navigator.clipboard.writeText(text).then(
    function () {
      flash(button, "Copied");
    },
    function () {
      flash(button, "Could not copy");
    }
  );
}

function copyOutput(button) {
  const source = all('[data-out="' + button.dataset.copy + '"]')[0];
  copyText(button, source ? source.textContent : "");
}

function copyList(button) {
  const list = byId(button.dataset.copyList);
  const lines = Array.from(list.children).map(function (child) {
    const note = child.getAttribute("title");
    return note ? child.textContent + "\t" + note : child.textContent;
  });
  copyText(button, lines.join("\n"));
}

function useExample(button) {
  const target = byId(button.dataset.example);
  target.value = button.dataset.value;
  update(target.dataset.tool, true);
  if (typeof target.focus === "function") {
    target.focus();
  }
}

function init() {
  all('[role="tab"]').forEach(function (tab) {
    tab.addEventListener("click", function () {
      selectTab(tab, false);
      writeState(currentTabName());
    });
    tab.addEventListener("keydown", onTabKey);
  });
  applyState(readState());
  if (typeof globalThis.addEventListener === "function") {
    globalThis.addEventListener("hashchange", function () {
      const state = readState();
      if (applyState(state) && TOOLS.indexOf(state.tab) >= 0) {
        update(state.tab, false);
      }
    });
  }

  TOOLS.forEach(function (tool) {
    const refresh = debounce(function () {
      update(tool, true);
    }, DEBOUNCE_MS);
    all('[data-tool="' + tool + '"]').forEach(function (el) {
      el.addEventListener("input", refresh);
      el.addEventListener("change", refresh);
    });
  });

  all("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      copyOutput(button);
    });
  });
  all("[data-copy-list]").forEach(function (button) {
    button.addEventListener("click", function () {
      copyList(button);
    });
  });
  all("[data-example]").forEach(function (button) {
    button.addEventListener("click", function () {
      useExample(button);
    });
  });
  byId("btn-share").addEventListener("click", function () {
    const name = currentTabName();
    writeState(name);
    const base = String(location.href || "").split("#")[0];
    copyText(byId("btn-share"), base + stateFor(name));
  });

  byId("btn-today").addEventListener("click", function () {
    if (!runPython) {
      return;
    }
    const info = runPython("info", {});
    if (info.ok && info.result.today_ad) {
      const toAd = byId("dir-bs2ad").checked;
      byId("in-dates").value = toAd ? info.result.today_bs : info.result.today_ad;
      update("dates", true);
    } else {
      showError("dates", "Today is outside the verified table (BS 2000 to 2083).");
    }
  });

  byId("retry").addEventListener("click", boot);
  boot();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
