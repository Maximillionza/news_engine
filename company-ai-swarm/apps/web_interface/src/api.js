// Thin fetch wrapper over the gateway's dashboard endpoints (apps/api_gateway/dashboard_api.py).
// Same-origin in production (served from /ui by the gateway); the vite dev server proxies.

const apiKey = () => localStorage.getItem("company.apiKey") || "dev-only-api-key";

async function req(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  activity: () => req("/activity"),
  chatHistory: () => req("/chat"),
  // Phase B (Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2): fire-and-forget -
  // resolves with { objective_id, status: "queued" }, not an immediate reply. Poll
  // objectiveResult() until it settles, then chatHistory() to pick up the coo's reply.
  chatSend: (message, filePath) =>
    req("/chat", {
      method: "POST",
      body: JSON.stringify({ message, ...(filePath ? { file_path: filePath } : {}) }),
    }),
  objectiveResult: (objectiveId) => req(`/objectives/${objectiveId}/result`),
  uploadFile: (filename, contentBase64) =>
    req("/files", {
      method: "POST",
      body: JSON.stringify({ filename, content_base64: contentBase64 }),
    }),
  proposalAction: (id, action) => req(`/proposals/${id}/${action}`, { method: "POST" }),
};

export function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
