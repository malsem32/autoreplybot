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

const MOBILE_PLATFORMS = ["ios", "android", "android_x"];

function px(value) {
  return `${Math.max(0, Number(value) || 0)}px`;
}

/** Mirrors Telegram's safe areas into CSS variables used by the layout
 * (`--inset-top` / `--inset-bottom` in index.css). In fullscreen the app
 * draws under the status bar and Telegram's own close/menu buttons, so the
 * top inset is the device safe area plus Telegram's content safe area. */
function syncInsets() {
  const root = document.documentElement;
  const device = safe(() => WebApp.safeAreaInset) || {};
  const content = safe(() => WebApp.contentSafeAreaInset) || {};
  const fullscreen = Boolean(safe(() => WebApp.isFullscreen));
  root.dataset.fullscreen = fullscreen ? "true" : "false";
  root.style.setProperty(
    "--tg-inset-top",
    fullscreen ? px((device.top || 0) + (content.top || 0)) : "0px",
  );
  root.style.setProperty("--tg-inset-bottom", px((device.bottom || 0) + (content.bottom || 0)));
}

export function initTelegram() {
  safe(() => WebApp.ready());
  safe(() => WebApp.expand());
  safe(() => WebApp.disableVerticalSwipes?.());
  // Bot API 8.0+: real fullscreen on phones; desktop and web stay windowed.
  const mobile = MOBILE_PLATFORMS.includes(safe(() => WebApp.platform));
  if (mobile && safe(() => WebApp.isVersionAtLeast("8.0"))) {
    safe(() => WebApp.requestFullscreen());
    safe(() => WebApp.lockOrientation?.());
  }
  applyTheme();
  syncInsets();
  safe(() => WebApp.onEvent("themeChanged", applyTheme));
  for (const event of [
    "safeAreaChanged",
    "contentSafeAreaChanged",
    "fullscreenChanged",
    "viewportChanged",
  ]) {
    safe(() => WebApp.onEvent(event, syncInsets));
  }
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
