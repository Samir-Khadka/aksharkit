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
const TOOLS = ["normalize", "aksharas", "numbers", "words", "dates", "calendar", "datemath", "tokenize", "sort", "detect", "translit", "preeti"];
const MAX_LINK_LENGTH = 1800; // longer inputs are left out of the shareable link
const DEBOUNCE_MS = 150;
const LIVE_LIMIT = 20000; // characters; longer Preeti text waits for the Convert button
const MAX_FILE_BYTES = 2 * 1024 * 1024;

// What the Preeti tab holds besides its form fields. None of it goes into the
// address: a file's text stays on this device.
const preetiFile = {
  fromFile: false, // the text box was filled from a file
  name: "", // that file's name, for the download name
  source: null, // { name, data }: a Word file waiting to be converted, as base64
  result: null, // { name, bytes }: the converted Word file
};

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
    // The line about an opened file stays until the file is put away.
    if (el.dataset.out.split(".")[0] === tool && el.dataset.out !== "preeti.file") {
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
  if (tool === "aksharas") {
    byId("out-aksharas-units").replaceChildren();
  }
  if (tool === "sort") {
    byId("out-sort-lines").replaceChildren();
  }
  if (tool === "calendar") {
    byId("out-calendar-head").replaceChildren();
    byId("out-calendar-weeks").replaceChildren();
  }
  if (tool === "preeti") {
    preetiFile.result = null;
    byId("btn-preeti-download").disabled = true;
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
  aksharas: function (r) {
    fill(
      byId("out-aksharas-units"),
      r.units
        .filter(function (unit) {
          return unit.text.trim() !== "";
        })
        .map(function (unit) {
          return item("li", unit.text, "chip");
        })
    );
    setOut(
      "aksharas.count",
      "(" + r.count + " aksharas, " + r.letters + " without spaces, from " + r.characters + " characters)"
    );
    setOut("aksharas.truncated", r.truncated.value, !r.truncated.ok);
  },
  sort: function (r) {
    setOut("sort.text", r.text);
    setOut("sort.count", "(" + r.count + (r.count === 1 ? " line)" : " lines)"));
    fill(
      byId("out-sort-lines"),
      r.lines.map(function (line) {
        return item("li", line, "");
      })
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
      const row = r[key];
      if (typeof row === "string") {
        setOut("dates." + key, row);
      } else {
        setOut("dates." + key, row.value, !row.ok); // the pattern rows can fail alone
      }
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
  preeti: function (r) {
    showDirection(r.to);
    setMarked("preeti.text", r.text, r.pieces);
    const tooMany = r.unmapped_count + (r.skipped_count || 0) > 0 && !r.pieces ? " Too many to highlight." : "";
    if (r.to === "preeti") {
      const parts = [];
      if (r.left_count) {
        parts.push(
          "Left in Unicode, highlighted (" + r.left_count + "): " + r.left.join(", ") + (r.left_count > r.left.length ? ", …" : "")
        );
      }
      if (r.unmapped.length) {
        parts.push("Characters with no Preeti key (" + r.unmapped_count + "): " + listChars(r.unmapped));
      }
      if (r.skipped_count) {
        parts.push("Words whose keys would not read back as the same text: " + r.skipped_count);
      }
      if (r.foreign_count) {
        parts.push(
          "Not Nepali, left as written (" +
            r.foreign_count +
            "): " +
            r.foreign.join(", ") +
            (r.foreign_count > r.foreign.length ? ", …" : "") +
            " — in the Preeti font these would show as other letters, so give them another font"
        );
      }
      setOut("preeti.unmapped", parts.length ? parts.join(". ") + "." + tooMany : r.text ? "Every Nepali word was written as Preeti keys." : "");
      setOut("preeti.confidence", r.text ? coverage(r.stats) : "");
    } else {
      setOut(
        "preeti.unmapped",
        r.unmapped.length
          ? "Left unchanged, no agreed letter (" + r.unmapped_count + "): " + listChars(r.unmapped) + tooMany
          : r.text
            ? "Every character had an agreed letter."
            : ""
      );
      setOut("preeti.confidence", confidence(r.stats, r.protected_count));
    }
    setOut("preeti.note", "Table: " + r.label + ". " + r.entries + " keys in use.");
    byId("btn-preeti-download").disabled = !r.text;
  },
};

/* ---- Preeti: direction, files, large text ---------------------------------- */

function listChars(chars) {
  return chars
    .map(function (u) {
      return u.char + " (" + u.code + ") ×" + u.count;
    })
    .join(", ");
}

function confidence(stats, protectedCount) {
  if (!stats || !stats.convertible) {
    return "";
  }
  let text =
    "Of " +
    stats.convertible +
    (stats.convertible === 1 ? " character" : " characters") +
    " to convert: " +
    stats.agreed +
    " by keys all tables agree on (" +
    percent(stats.agreed_share) +
    "), " +
    stats.majority +
    " by keys where one table differs (" +
    percent(stats.majority_share) +
    ")";
  if (stats.unconfirmed) {
    text += ", " + stats.unconfirmed + " by keys only one table has";
  }
  text += ", " + stats.unmapped + " left unchanged.";
  if (protectedCount) {
    text += " " + protectedCount + (protectedCount === 1 ? " web or e-mail address" : " web or e-mail addresses") + " left as written.";
  }
  return text;
}

// Text with the pieces that were left alone marked, so they are easy to find.
function setMarked(key, text, pieces) {
  all('[data-out="' + key + '"]').forEach(function (el) {
    el.classList.toggle("failed", false);
    if (!pieces) {
      el.textContent = text;
      return;
    }
    fill(
      el,
      pieces.map(function (piece) {
        return item(piece[1] ? "mark" : "span", piece[0], piece[1] ? "unmapped" : "");
      })
    );
  });
}

// How much of the Nepali text became keys. This counts words; it says nothing
// about whether a typist would have pressed the same keys.
function coverage(stats) {
  const share = stats.words ? Math.round(stats.share_words * 1000) / 10 : 0;
  return (
    stats.words_encoded +
    " of " +
    stats.words +
    " Nepali words written as Preeti keys (" +
    share +
    "%). Each of them was converted back and gave the same text. The keys are one valid way to type it by this experimental table, not necessarily the way a typist would; nobody has yet looked at them in the Preeti font."
  );
}

function showDirection(to) {
  const reverse = to === "preeti";
  byId("lbl-preeti-in-text").textContent = reverse ? "Unicode text" : "Preeti text";
  byId("lbl-preeti-in-note").textContent = reverse
    ? "(Nepali in Devanagari)"
    : "(shown in an ordinary font, so it looks like Latin letters — that is expected)";
  byId("lbl-preeti-text").textContent = reverse ? "Preeti keystrokes" : "Unicode";
  const input = byId("in-preeti");
  input.classList.toggle("plain-input", !reverse);
  input.setAttribute("lang", reverse ? "ne" : "zxx");
  const output = byId("out-preeti-text");
  output.classList.toggle("plain-input", reverse);
  output.setAttribute("lang", reverse ? "zxx" : "ne");
  byId("opt-preeti-font").disabled = reverse; // the keys are always set in the font named Preeti
  byId("note-preeti-reverse").hidden = !reverse;
  byId("examples-preeti").hidden = reverse;
  byId("examples-preeti-reverse").hidden = !reverse;
}

function toBase64(bytes) {
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    text += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  }
  return btoa(text);
}

function fromBase64(text) {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i);
  }
  return bytes;
}

function stem(name) {
  const cut = name.lastIndexOf(".");
  return (cut > 0 ? name.slice(0, cut) : name) || "aksharkit";
}

function saveFile(name, data, type) {
  const url = URL.createObjectURL(new Blob([data], { type: type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(function () {
    URL.revokeObjectURL(url);
  }, 1000);
}

function forgetPreetiFile() {
  preetiFile.fromFile = false;
  preetiFile.name = "";
  preetiFile.source = null;
  preetiFile.result = null;
  byId("file-preeti").value = "";
  setOut("preeti.file", "");
}

// Long text is not converted on every keystroke: the conversion runs on the
// page's own thread, so the page would stop answering while it works.
function preetiIsLive(force) {
  const length = byId("in-preeti").value.length;
  const large = length > LIVE_LIMIT;
  showDirection(collect("preeti").to);
  byId("btn-preeti-convert").hidden = !large;
  if (large && !force) {
    clearOutputs("preeti");
    showError("preeti", "");
  }
  setOut(
    "preeti.size",
    large
      ? "Large text (" +
          length +
          " characters). It is converted when you press Convert, not as you type, and the page may pause while it works."
      : ""
  );
  return !large || Boolean(force);
}

function convertWordFile() {
  const source = preetiFile.source;
  if (!source || !runPython) {
    return;
  }
  const options = collect("preeti");
  let answer;
  try {
    answer = runPython("preeti_docx", {
      data: source.data,
      font: byId("opt-preeti-font").value,
      to: options.to,
      unconfirmed: options.unconfirmed,
      strict: options.strict,
    });
  } catch (error) {
    answer = { ok: false, error: "Unexpected error: " + (error && error.message ? error.message : error) };
  }
  clearOutputs("preeti");
  if (!answer.ok) {
    showError("preeti", source.name + ": " + answer.error);
    setOut("preeti.file", "");
    return;
  }
  const r = answer.result;
  showError("preeti", "");
  if (r.to === "preeti") {
    showDirection("preeti");
    preetiFile.result = { name: stem(source.name) + "-preeti.docx", bytes: fromBase64(r.data) };
    setOut(
      "preeti.file",
      source.name +
        ": " +
        (r.runs_converted + r.runs_split) +
        " stretch(es) of Nepali text written as Preeti keys and set to the font named " +
        r.font +
        " (" +
        r.runs_split +
        " of them cut up because they also held other text); " +
        r.runs_untouched +
        " left as they were. Press Download result for the new file. It reads as Nepali only where the Preeti font is installed."
    );
    setOut(
      "preeti.unmapped",
      r.left_count
        ? "Left in Unicode, in the font they had (" + r.left_count + "): " + r.left.join(", ") + (r.left_count > r.left.length ? ", …" : "") + "."
        : r.stats.words
          ? "Every Nepali word was written as Preeti keys."
          : "No Nepali text in Devanagari was found in this file, so nothing was changed."
    );
    setOut("preeti.confidence", r.stats.words ? coverage(r.stats) : "");
    setOut("preeti.note", "Table: " + r.label + ".");
    byId("btn-preeti-download").disabled = false;
    return;
  }
  preetiFile.result = { name: stem(source.name) + "-unicode.docx", bytes: fromBase64(r.data) };
  setOut(
    "preeti.file",
    source.name +
      ": " +
      r.runs_converted +
      " stretch(es) of Preeti text converted and set to " +
      r.font +
      "; " +
      r.runs_untouched +
      " in other fonts left as they were. Press Download result for the new file. Fonts found: " +
      (r.fonts_seen.length
        ? r.fonts_seen
            .map(function (font) {
              return font[0] + " (" + font[1] + ")";
            })
            .join(", ")
        : "none") +
      "."
  );
  setOut(
    "preeti.unmapped",
    r.unmapped.length
      ? "Left unchanged, no agreed letter (" + r.unmapped_count + "): " + listChars(r.unmapped)
      : r.runs_converted
        ? "Every character had an agreed letter."
        : "No text in the Preeti font was found in this file, so nothing was changed."
  );
  setOut("preeti.confidence", confidence(r.stats, 0));
  setOut("preeti.note", "Table: " + r.label + ".");
  byId("btn-preeti-download").disabled = false;
}

async function openPreetiFile(file) {
  if (!file) {
    return;
  }
  const name = String(file.name || "file");
  const lower = name.toLowerCase();
  forgetPreetiFile();
  clearOutputs("preeti");
  showError("preeti", "");
  if (file.size > MAX_FILE_BYTES) {
    showError("preeti", name + " is larger than 2 MB. Use the command line for large files: aksharkit convert preeti.");
    return;
  }
  if (lower.endsWith(".doc")) {
    showError("preeti", name + " is an old .doc file. Open it in a word processor and save it as .docx first.");
    return;
  }
  let bytes;
  try {
    bytes = new Uint8Array(await file.arrayBuffer());
  } catch (error) {
    showError("preeti", "Could not read " + name + ".");
    return;
  }
  if (lower.endsWith(".docx")) {
    byId("in-preeti").value = "";
    preetiIsLive(false);
    preetiFile.fromFile = true;
    preetiFile.name = name;
    preetiFile.source = { name: name, data: toBase64(bytes) };
    writeState("preeti");
    convertWordFile();
    return;
  }
  if (bytes.indexOf(0) >= 0) {
    showError("preeti", name + " does not look like a text file. Only .txt and .docx files can be opened here.");
    return;
  }
  const encoding = byId("opt-preeti-encoding").value;
  let text;
  try {
    text = new TextDecoder(encoding, { fatal: true }).decode(bytes);
  } catch (error) {
    showError(
      "preeti",
      encoding === "utf-8"
        ? name + " is not valid UTF-8. If it came from an older Windows program, choose Windows-1252 and open it again."
        : name + " could not be read as " + encoding + "."
    );
    return;
  }
  byId("in-preeti").value = text;
  preetiFile.fromFile = true;
  preetiFile.name = name;
  setOut(
    "preeti.file",
    "Opened " + name + " (" + text.length + " characters). Its text is kept out of the address and the shareable link."
  );
  update("preeti", true);
}

function downloadPreeti() {
  if (preetiFile.result) {
    saveFile(
      preetiFile.result.name,
      preetiFile.result.bytes,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );
    return;
  }
  const text = byId("out-preeti-text").textContent;
  if (!text) {
    return;
  }
  const ending = collect("preeti").to === "preeti" ? "-preeti.txt" : "-unicode.txt";
  saveFile(stem(preetiFile.name || "aksharkit") + ending, text, "text/plain;charset=utf-8");
}

function update(tool, fromUser, force) {
  // The address describes the tab on screen. An edit that is still waiting out
  // its debounce when another tab is opened must not put the old tab back.
  if (fromUser && tool === currentTabName()) {
    writeState(tool);
  }
  if (!runPython) {
    return;
  }
  if (tool === "preeti") {
    if (preetiFile.source) {
      convertWordFile();
      return;
    }
    if (!preetiIsLive(force)) {
      return;
    }
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
  if (name === "preeti" && preetiFile.fromFile) {
    delete payload.text; // a file's text never goes into the address
  }
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
  if (target.id === "in-preeti") {
    forgetPreetiFile();
    // An example says which way it goes: Preeti keystrokes, or Nepali to turn into them.
    byId("opt-preeti-to").value = button.dataset.to === "preeti" ? "preeti" : "unicode";
  }
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

  // Typing in the box after a Word file was opened goes back to plain text.
  byId("in-preeti").addEventListener("input", function () {
    if (preetiFile.source) {
      forgetPreetiFile();
    }
  });
  byId("file-preeti").addEventListener("change", function (event) {
    const files = event.target.files;
    openPreetiFile(files && files[0]);
  });
  byId("opt-preeti-font").addEventListener("change", function () {
    if (preetiFile.source) {
      convertWordFile();
    }
  });
  byId("btn-preeti-convert").addEventListener("click", function () {
    update("preeti", true, true);
  });
  byId("btn-preeti-clear").addEventListener("click", function () {
    forgetPreetiFile();
    byId("in-preeti").value = "";
    update("preeti", true);
  });
  byId("btn-preeti-download").addEventListener("click", downloadPreeti);

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
