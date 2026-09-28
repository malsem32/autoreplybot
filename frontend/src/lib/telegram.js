import WebApp from "@twa-dev/sdk";

/** Thin, crash-proof wrappers around the Telegram WebApp API: every call is
 * guarded so the app also runs in a plain browser during development. */

export const tg = WebApp;

function safe(fn) {
  try {
    return fn();
  } catch {
    return undefined;
  }
}

export const haptic = {
  tap: () => safe(() => WebApp.HapticFeedback.impactOccurred("light")),
  select: () => safe(() => WebApp.HapticFeedback.selectionChanged()),
  success: () => safe(() => WebApp.HapticFeedback.notificationOccurred("success")),
  error: () => safe(() => WebApp.HapticFeedback.notificationOccurred("error")),
  warning: () => safe(() => WebApp.HapticFeedback.notificationOccurred("warning")),
};

const THEME_COLORS = {
  dark: { bg: "#0B1633", header: "#0B1633" },
  light: { bg: "#EFF3FA", header: "#EFF3FA" },
};

export function applyTheme() {
  const scheme = WebApp.colorScheme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = scheme;
  safe(() => WebApp.setHeaderColor(THEME_COLORS[scheme].header));
  safe(() => WebApp.setBackgroundColor(THEME_COLORS[scheme].bg));
  safe(() => WebApp.setBottomBarColor?.(THEME_COLORS[scheme].bg));
}

export function initTelegram() {
  safe(() => WebApp.ready());
  safe(() => WebApp.expand());
  safe(() => WebApp.disableVerticalSwipes?.());
  applyTheme();
  safe(() => WebApp.onEvent("themeChanged", applyTheme));
}

/** Opens a Stars invoice; resolves with "paid" | "cancelled" | "failed" | "pending". */
export function openInvoice(link) {
  return new Promise((resolve) => {
    const opened = safe(() => {
      WebApp.openInvoice(link, (status) => resolve(status));
      return true;
    });
    if (!opened) {
      window.open(link, "_blank");
      resolve("pending");
    }
  });
}

export function shareLink(url, text) {
  const share = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  const opened = safe(() => {
    WebApp.openTelegramLink(share);
    return true;
  });
  if (!opened) window.open(share, "_blank");
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

export function openLink(url) {
  const opened = safe(() => {
    WebApp.openLink(url);
    return true;
  });
  if (!opened) window.open(url, "_blank");
}

export function confirmDialog(message) {
  return new Promise((resolve) => {
    const shown = safe(() => {
      WebApp.showConfirm(message, (ok) => resolve(Boolean(ok)));
      return true;
    });
    if (!shown) resolve(window.confirm(message));
  });
}

// Stacked back-button handlers: a sheet opened over a sheet (or over a
// sub-page) gets the button first; closing it hands it back to the one below.
const backStack = [];

function onBackClick() {
  backStack[backStack.length - 1]?.();
}

let backBound = false;

/** Shows Telegram's native back button, calling `onBack` while this
 * handler is the top-most one. Returns an unbind function. */
export function bindBackButton(onBack) {
  backStack.push(onBack);
  safe(() => {
    if (!backBound) {
      WebApp.BackButton.onClick(onBackClick);
      backBound = true;
    }
    WebApp.BackButton.show();
  });
  return () => {
    const index = backStack.lastIndexOf(onBack);
    if (index !== -1) backStack.splice(index, 1);
    if (!backStack.length) safe(() => WebApp.BackButton.hide());
  };
}
