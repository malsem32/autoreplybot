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
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  sendCode: (phone) => request("/auth/send_code", { method: "POST", body: { phone } }),
  signIn: (phone, phone_code_hash, code) =>
    request("/auth/sign_in", { method: "POST", body: { phone, phone_code_hash, code } }),
  checkPassword: (phone, password) =>
    request("/auth/check_password", { method: "POST", body: { phone, password } }),

  listRules: (accountId) => request(`/autoresponder/${accountId}/rules`),
  createRule: (accountId, rule) =>
    request(`/autoresponder/${accountId}/rules`, { method: "POST", body: rule }),

  listCampaigns: (accountId) => request(`/broadcasts/${accountId}/campaigns`),
  createCampaign: (accountId, campaign) =>
    request(`/broadcasts/${accountId}/campaigns`, { method: "POST", body: campaign }),
  pauseCampaign: (accountId, campaignId) =>
    request(`/broadcasts/${accountId}/campaigns/${campaignId}/pause`, { method: "POST" }),
};
