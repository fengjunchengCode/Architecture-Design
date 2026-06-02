(function (root) {
  "use strict";

  const PLACEHOLDER = "暂无图纸说明。";

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function parseInline(line) {
    const runs = [];
    let index = 0;
    while (index < line.length) {
      if (line.startsWith("**", index)) {
        const end = line.indexOf("**", index + 2);
        if (end > index + 2) {
          runs.push({ role: "heading", text: line.slice(index + 2, end) });
          index = end + 2;
          continue;
        }
      }
      if (line[index] === "*" && line[index + 1] !== "*") {
        const end = line.indexOf("*", index + 1);
        if (end > index + 1 && line[end + 1] !== "*") {
          runs.push({ role: "brand", text: line.slice(index + 1, end) });
          index = end + 1;
          continue;
        }
      }
      let next = line.length;
      const nextHeading = line.indexOf("**", index + 1);
      const nextBrand = line.indexOf("*", index + 1);
      if (nextHeading !== -1) next = Math.min(next, nextHeading);
      if (nextBrand !== -1) next = Math.min(next, nextBrand);
      runs.push({ role: "body", text: line.slice(index, next) });
      index = next;
    }
    return runs.filter((run) => run.text);
  }

  function applyColonFallback(runs) {
    if (runs.some((run) => run.role !== "body")) return runs;
    const text = runs.map((run) => run.text).join("");
    const match = text.match(/^([^：:]{1,28}[：:])(.*)$/);
    if (!match) return runs;
    return [
      { role: "heading", text: match[1] },
      ...(match[2] ? [{ role: "body", text: match[2] }] : []),
    ];
  }

  function parse(markup) {
    const source = String(markup || "").replace(/\r\n?/g, "\n");
    const lines = source.split(/\n+/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return [];
    return lines.map((line) => ({ runs: applyColonFallback(parseInline(line)) }));
  }

  function renderRun(run) {
    const text = escapeHtml(run.text);
    if (run.role === "heading") {
      return `<strong class="ppt-text-heading" data-ppt-text-heading="true">${text}</strong>`;
    }
    if (run.role === "brand") {
      return `<strong class="ppt-text-brand" data-ppt-text-brand="true">${text}</strong>`;
    }
    return text;
  }

  function renderHtml(markup, options = {}) {
    const bodyStyle = options.bodyStyle || "";
    const paragraphs = parse(markup);
    if (!paragraphs.length) {
      return `<p class="ppt-text-body ppt-text-line" data-ppt-text-line="true" data-ppt-placeholder="true" style="${bodyStyle}">${PLACEHOLDER}</p>`;
    }
    return paragraphs
      .map((paragraph) => {
        const content = paragraph.runs.map(renderRun).join("");
        return `<p class="ppt-text-body ppt-text-line" data-ppt-text-line="true" style="${bodyStyle}">${content}</p>`;
      })
      .join("");
  }

  function serializeInline(node) {
    if (!node) return "";
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const element = node;
    if (element.tagName === "BR") return "\n";
    const content = Array.from(element.childNodes).map(serializeInline).join("");
    if (!content) return "";
    if (element.dataset?.pptTextHeading === "true") return `**${content}**`;
    if (element.dataset?.pptTextBrand === "true") return `*${content}*`;
    return content;
  }

  function serializeElement(element) {
    if (!element) return "";
    if (element.dataset?.pptTextEmpty === "true" && element.innerText.trim() === PLACEHOLDER) return "";
    const lines = Array.from(element.querySelectorAll("[data-ppt-text-line='true']"));
    if (!lines.length) return (element.innerText || "").replace(/\u00a0/g, " ").trim();
    return lines
      .map((line) => {
        if (line.dataset.pptPlaceholder === "true" && line.innerText.trim() === PLACEHOLDER) return "";
        return Array.from(line.childNodes).map(serializeInline).join("").replace(/\u00a0/g, " ").trim();
      })
      .filter(Boolean)
      .join("\n");
  }

  function wrapSelection(marker) {
    const selection = root.getSelection && root.getSelection();
    if (!selection || selection.rangeCount === 0 || !selection.toString()) return false;
    const range = selection.getRangeAt(0);
    const text = selection.toString();
    range.deleteContents();
    range.insertNode(root.document.createTextNode(`${marker}${text}${marker}`));
    selection.removeAllRanges();
    return true;
  }

  const api = { PLACEHOLDER, parse, renderHtml, serializeElement, wrapSelection };
  root.PptTextMarkup = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
