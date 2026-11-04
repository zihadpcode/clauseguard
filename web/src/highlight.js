// Port of clauseguard/highlight.py: marks validated spans in the plan text.
// Display only; a span this can't place is just not highlighted.
(function (root) {
  "use strict";

  const SINGLE = "'\u2018\u2019\u201a\u201b\u2032\u02bc";
  const DOUBLE = '"\u201c\u201d\u201e\u201f\u2033';
  const RE_SYNTAX = /[.*+?^${}()|[\]\\/]/g;

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[c]);

  function spanPattern(span) {
    span = span.trim();
    if (span.endsWith(".")) span = span.slice(0, -1);
    const parts = [];
    for (const ch of span) {
      if (/\s/u.test(ch)) {
        if (parts[parts.length - 1] !== "\\s+") parts.push("\\s+");
      } else if (SINGLE.includes(ch)) {
        parts.push(`[${SINGLE}]`);
      } else if (DOUBLE.includes(ch)) {
        parts.push(`[${DOUBLE}]`);
      } else {
        parts.push(ch.replace(RE_SYNTAX, "\\$&"));
      }
    }
    return new RegExp(parts.join("") + "\\.?", "iu");
  }

  function findSpans(planText, spans) {
    const found = [];
    for (const [checkId, status, span] of spans) {
      if (!span) continue;
      const m = spanPattern(span).exec(planText);
      if (m) found.push([m.index, m.index + m[0].length, checkId, status]);
    }
    found.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const out = [];
    let lastEnd = -1;
    for (const f of found) {
      if (f[0] >= lastEnd) {
        out.push(f);
        lastEnd = f[1];
      }
    }
    return out;
  }

  function highlightHtml(planText, spans) {
    let html = "";
    let pos = 0;
    for (const [start, end, checkId, status] of findSpans(planText, spans)) {
      const short = checkId.replace(/^PFAS_/, "").replace(/_01$/, "");
      html += esc(planText.slice(pos, start));
      html += `<mark class="hl hl--${esc(status)}" title="${esc(checkId)}">${esc(planText.slice(start, end))}<sup>${esc(short)}</sup></mark>`;
      pos = end;
    }
    return html + esc(planText.slice(pos));
  }

  const api = { findSpans, highlightHtml, esc };
  root.CGHighlight = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
