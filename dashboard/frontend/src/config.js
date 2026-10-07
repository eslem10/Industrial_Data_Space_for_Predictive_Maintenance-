export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";

export const EDC_CONNECTOR_URLS = {
  F1: import.meta.env.VITE_EDC_F1_URL || "http://localhost:19193/management/v3",
  F2: import.meta.env.VITE_EDC_F2_URL || "http://localhost:21193/management/v3",
  F3: import.meta.env.VITE_EDC_F3_URL || "http://localhost:23193/management/v3"
};
