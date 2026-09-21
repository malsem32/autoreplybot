import WebApp from "@twa-dev/sdk";

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `tma ${WebApp.initData}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const error = new Error(detail.detail || `Request failed: ${res.status}`);
    error.status = res.status;
    throw error;
  }
  if (res.status === 204) return null;
  return res.json();
}

async function uploadPhoto(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/uploads/photo", {
    method: "POST",
    headers: { Authorization: `tma ${WebApp.initData}` },
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listAccounts: () => request("/auth/accounts"),
  sendCode: (phone) => request("/auth/send_code", { method: "POST", body: { phone } }),
  signIn: (phone, phone_code_hash, code) =>
    request("/auth/sign_in", { method: "POST", body: { phone, phone_code_hash, code } }),
  checkPassword: (phone, password) =>
    request("/auth/check_password", { method: "POST", body: { phone, password } }),
  qrStart: () => request("/auth/qr/start", { method: "POST" }),
  qrPoll: (requestId) => request(`/auth/qr/${requestId}/poll`),

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

  adminStats: () => request("/admin/stats"),
  adminGetTagFeature: () => request("/admin/tag-feature"),
  adminUpdateTagFeature: (patch) => request("/admin/tag-feature", { method: "PATCH", body: patch }),

  getTagFeatureStatus: () => request("/features/tag-broadcast"),
  createTagFeatureInvoice: () => request("/features/tag-broadcast/invoice", { method: "POST" }),
};
