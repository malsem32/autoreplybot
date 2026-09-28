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

  testRules: (accountId, text, inGroup = false) =>
    request(`/autoresponder/${accountId}/test`, {
      method: "POST",
      body: { text, in_group: inGroup },
    }),

  listLeads: (accountId, status) =>
    request(`/leads/${accountId}${status ? `?status=${status}` : ""}`),
  updateLead: (accountId, leadId, patch) =>
    request(`/leads/${accountId}/${leadId}`, { method: "PATCH", body: patch }),
  exportLeads: (accountId) => request(`/export/leads/${accountId}`, { method: "POST" }),
  exportCampaign: (accountId, campaignId) =>
    request(`/export/campaigns/${accountId}/${campaignId}`, { method: "POST" }),

  getTeam: (accountId) => request(`/team/${accountId}`),
  createTeamInvite: (accountId) => request(`/team/${accountId}/invite`, { method: "POST" }),
  removeTeamMember: (accountId, memberId) =>
    request(`/team/${accountId}/members/${memberId}`, { method: "DELETE" }),
  leaveTeam: (accountId) => request(`/team/${accountId}/leave`, { method: "POST" }),

  getAway: (accountId) => request(`/away/${accountId}`),
  setAway: (accountId, body) => request(`/away/${accountId}`, { method: "PUT", body }),
  stopAway: (accountId) => request(`/away/${accountId}`, { method: "DELETE" }),

  listSnippets: (accountId) => request(`/snippets/${accountId}`),
  createSnippet: (accountId, body) => request(`/snippets/${accountId}`, { method: "POST", body }),
  updateSnippet: (accountId, id, patch) =>
    request(`/snippets/${accountId}/${id}`, { method: "PATCH", body: patch }),
  deleteSnippet: (accountId, id) => request(`/snippets/${accountId}/${id}`, { method: "DELETE" }),

  getAi: (accountId) => request(`/ai/${accountId}`),
  saveAi: (accountId, body) => request(`/ai/${accountId}`, { method: "PUT", body }),
  previewAi: (accountId, text) =>
    request(`/ai/${accountId}/preview`, { method: "POST", body: { text } }),

  contactSupport: (text) => request("/support", { method: "POST", body: { text } }),

  getMe: () => request("/me"),
  updateMe: (patch) => request("/me", { method: "PATCH", body: patch }),

  listTemplates: () => request("/templates"),
  createTemplate: (template) => request("/templates", { method: "POST", body: template }),
  deleteTemplate: (id) => request(`/templates/${id}`, { method: "DELETE" }),

  getPro: () => request("/features/pro"),
  createProInvoice: (plan = "month") =>
    request("/features/pro/invoice", { method: "POST", body: { plan } }),
  startTrial: () => request("/features/pro/trial", { method: "POST" }),
  getReferrals: () => request("/referrals"),

  adminStats: () => request("/admin/stats"),
  adminTimeseries: () => request("/admin/timeseries"),
  adminUsers: (q = "", filter = "all", offset = 0) =>
    request(`/admin/users?q=${encodeURIComponent(q)}&filter=${filter}&offset=${offset}`),
  adminUser: (id) => request(`/admin/users/${id}`),
  adminGrantPro: (id, days, notify = true) =>
    request(`/admin/users/${id}/pro`, { method: "POST", body: { days, notify } }),
  adminRevokePro: (id) => request(`/admin/users/${id}/pro`, { method: "DELETE" }),
  adminGetPro: () => request("/admin/pro"),
  adminUpdatePro: (patch) => request("/admin/pro", { method: "PATCH", body: patch }),
  listProxies: () => request("/admin/proxies"),
  createProxy: (proxy) => request("/admin/proxies", { method: "POST", body: proxy }),
  updateProxy: (id, patch) => request(`/admin/proxies/${id}`, { method: "PATCH", body: patch }),
  deleteProxy: (id) => request(`/admin/proxies/${id}`, { method: "DELETE" }),
  checkAllProxies: () => request("/admin/proxies/check", { method: "POST" }),
};
