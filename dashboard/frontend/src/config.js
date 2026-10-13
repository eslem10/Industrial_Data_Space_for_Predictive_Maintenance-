const rawBase = import.meta.env.VITE_API_BASE_URL;

// Normalize: remove trailing slash and trailing '/api'
// because components fetch `${API_BASE_URL}/api/...`
export const API_BASE_URL = (() => {
  if (rawBase === undefined || rawBase === null) {
    return "http://localhost:3001";
  }
  return rawBase.trim().replace(/\/+$/, "").replace(/\/api$/, "");
})();

export const EDC_CONNECTOR_URLS = {
  F1: import.meta.env.VITE_EDC_F1_URL || "http://localhost:19193/management/v3",
  F2: import.meta.env.VITE_EDC_F2_URL || "http://localhost:21193/management/v3",
  F3: import.meta.env.VITE_EDC_F3_URL || "http://localhost:23193/management/v3"
};
