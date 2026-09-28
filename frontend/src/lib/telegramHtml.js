/** Renders the subset of HTML Telegram (Pyrogram's HTML parser) supports
 * into safe preview markup. Anything else is shown as plain text, so the
 * preview can never execute markup typed by the user. */

const INLINE = {
  b: "strong",
  strong: "strong",
  i: "em",
  em: "em",
  u: "u",
  ins: "u",
  s: "s",
  del: "s",
  strike: "s",
  code: "code",
  pre: "pre",
  blockquote: "blockquote",
};

const SAFE_HREF = /^(https?:\/\/|tg:\/\/)/i;

function escape(text) {
  return text.replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function renderNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return escape(node.textContent).replace(/\n/g, "<br>");
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return "";
  const tag = node.tagName.toLowerCase();
  const inner = Array.from(node.childNodes).map(renderNode).join("");

  if (INLINE[tag]) return `<${INLINE[tag]}>${inner}</${INLINE[tag]}>`;
  if (tag === "spoiler" || tag === "tg-spoiler") return `<span class="spoiler">${inner}</span>`;
  if (tag === "a") {
    const href = node.getAttribute("href") || "";
    if (SAFE_HREF.test(href)) {
      return `<a href="${escape(href)}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
    }
    return inner;
  }
  if (tag === "br") return "<br>";
  return inner;
}

export function renderTelegramHtml(source) {
  const doc = new DOMParser().parseFromString(`<body>${source}</body>`, "text/html");
  return (
    Array.from(doc.body.childNodes)
      .map(renderNode)
      .join("")
      // Block elements already break the line, like in Telegram.
      .replace(/(<\/(?:blockquote|pre)>)<br>/g, "$1")
  );
}

/** Length as Telegram counts it: formatting tags don't count. */
export function visibleLength(source) {
  return source.replace(/<[^>]+>/g, "").length;
}

/** Resolves `{a|b|c}` spintax groups, like workers/spintax.py. */
export function renderSpintax(text) {
  const re = /\{([^{}]+)\}/;
  let out = text;
  let guard = 0;
  while (re.test(out) && guard++ < 100) {
    out = out.replace(re, (_, group) => {
      const options = group.split("|");
      return options[Math.floor(Math.random() * options.length)];
    });
  }
  return out;
}
