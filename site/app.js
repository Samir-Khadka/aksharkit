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
const PACKAGE_DIR = "/home/pyodide/aksharkit_pkg";
const TOOLS = ["normalize", "numbers", "dates", "tokenize", "translit"];
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
    const response = await fetch(PACKAGE_ARCHIVE);
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
    TOOLS.forEach(update);
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
    Object.keys(r).forEach(function (key) {
      setOut("numbers." + key, r[key].value, !r[key].ok);
    });
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
    setOut(
      "translit.note",
      r.approximate
        ? "Simple scheme: approximate. It cannot tell t from ṭ, d from ḍ, s from ś or ṣ, or short vowels from long ones."
        : "IAST scheme: converting this back gives the original text."
    );
  },
};

function update(tool) {
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

function copyOutput(button) {
  const source = all('[data-out="' + button.dataset.copy + '"]')[0];
  const text = source ? source.textContent : "";
  if (!text || !navigator.clipboard) {
    return;
  }
  navigator.clipboard.writeText(text).then(function () {
    const label = button.textContent;
    button.textContent = "Copied";
    setTimeout(function () {
      button.textContent = label;
    }, 1200);
  });
}

function init() {
  all('[role="tab"]').forEach(function (tab) {
    tab.addEventListener("click", function () {
      selectTab(tab, false);
    });
    tab.addEventListener("keydown", onTabKey);
  });
  const wanted = byId("tab-" + String(location.hash || "").replace("#", ""));
  if (wanted) {
    selectTab(wanted, false);
  }

  TOOLS.forEach(function (tool) {
    const refresh = debounce(function () {
      update(tool);
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

  byId("btn-today").addEventListener("click", function () {
    if (!runPython) {
      return;
    }
    const info = runPython("info", {});
    if (info.ok && info.result.today_ad) {
      const toAd = byId("dir-bs2ad").checked;
      byId("in-dates").value = toAd ? info.result.today_bs : info.result.today_ad;
      update("dates");
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
