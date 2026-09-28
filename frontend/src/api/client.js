import WebApp from "@twa-dev/sdk";

/** Error with the HTTP status attached; `detail` is the backend's message
 * (already human-readable Russian for user-facing errors). */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const listeners = new Set();
/** Subscribe to API errors app-wide (used to open the Pro paywall on 402). */
export function onApiError(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function messageFor(status, detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors
    return "Проверьте правильность заполнения полей";
  }
  if (status === 401) return "Откройте приложение заново из Telegram";
  if (status === 429) return "Слишком много запросов — подождите немного";
  if (status >= 500) return "Сервер временно недоступен, попробуйте ещё раз";
  return `Ошибка запроса (${status})`;
}

async function send(path, init) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { Authorization: `tma ${WebApp.initData}`, ...(init.headers || {}) },
    });
  } catch {
    throw new ApiError("Нет соединения с сервером. Проверьте интернет", 0);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new ApiError(messageFor(res.status, body.detail), res.status);
    listeners.forEach((fn) => fn(error));
    throw error;
  }
  if (res.status === 204) return null;
  return res.json();
}

function request(path, { method = "GET", body } = {}) {
  return send(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
}

function uploadPhoto(file) {
  const form = new FormData();
  form.append("file", file);
  return send("/uploads/photo", { method: "POST", body: form });
}

export const api = {
  listAccounts: () => request("/auth/accounts"),
  updateAccount: (id, patch) => request(`/auth/accounts/${id}`, { method: "PATCH", body: patch }),
  deleteAccount: (id) => request(`/auth/accounts/${id}`, { method: "DELETE" }),

  sendCode: (phone) => request("/auth/send_code", { method: "POST", body: { phone } }),
  resendCode: (phone, phone_code_hash) =>
    request("/auth/resend_code", { method: "POST", body: { phone, phone_code_hash } }),
  cancelLogin: (phone) => request("/auth/cancel", { method: "POST", body: { phone } }),
  signIn: (phone, phone_code_hash, code) =>
    request("/auth/sign_in", { method: "POST", body: { phone, phone_code_hash, code } }),
  checkPassword: (phone, password) =>
    request("/auth/check_password", { method: "POST", body: { phone, password } }),
  qrStart: () => request("/auth/qr/start", { method: "POST" }),
  qrPoll: (id) => request(`/auth/qr/${id}/poll`),
  qrPassword: (id, password) =>
    request(`/auth/qr/${id}/password`, { method: "POST", body: { password } }),
  qrCancel: (id) => request(`/auth/qr/${id}/cancel`, { method: "POST" }),

  uploadPhoto,

  listRules: (accountId) => request(`/autoresponder/${accountId}/rules`),
  createRule: (accountId, rule) =>
    request(`/autoresponder/${accountId}/rules`, { method: "POST", body: rule }),
  updateRule: (accountId, ruleId, patch) =>
    request(`/autoresponder/${accountId}/rules/${ruleId}`, { method: "PATCH", body: patch }),
  deleteRule: (accountId, ruleId) =>
    request(`/autoresponder/${accountId}/rules/${ruleId}`, { method: "DELETE" }),

  listCampaigns: (accountId) => request(`/broadcasts/${accountId}/campaigns`),
  createCampaign: (accountId, campaign) =>
    request(`/broadcasts/${accountId}/campaigns`, { method: "POST", body: campaign }),
  updateCampaign: (accountId, campaignId, patch) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}`, { method: "PATCH", body: patch }),
  deleteCampaign: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}`, { method: "DELETE" }),
  pauseCampaign: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}/pause`, { method: "POST" }),
  resumeCampaign: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}/resume`, { method: "POST" }),
  listCampaignLogs: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}/logs`),
  getCampaignStats: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}/stats`),

  listTemplates: () => request("/templates"),
  createTemplate: (template) => request("/templates", { method: "POST", body: template }),
  deleteTemplate: (id) => request(`/templates/${id}`, { method: "DELETE" }),

  getPro: () => request("/features/pro"),
  createProInvoice: (plan = "month") =>
    request("/features/pro/invoice", { method: "POST", body: { plan } }),
  startTrial: () => request("/features/pro/trial", { method: "POST" }),
  getReferrals: () => request("/referrals"),

  adminStats: () => request("/admin/stats"),
  adminGetPro: () => request("/admin/pro"),
  adminUpdatePro: (patch) => request("/admin/pro", { method: "PATCH", body: patch }),
  listProxies: () => request("/admin/proxies"),
  createProxy: (proxy) => request("/admin/proxies", { method: "POST", body: proxy }),
  updateProxy: (id, patch) => request(`/admin/proxies/${id}`, { method: "PATCH", body: patch }),
  deleteProxy: (id) => request(`/admin/proxies/${id}`, { method: "DELETE" }),
  checkAllProxies: () => request("/admin/proxies/check", { method: "POST" }),
};
