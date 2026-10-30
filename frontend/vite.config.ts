import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api requests are forwarded to the FastAPI backend (override with API_URL).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": process.env.API_URL ?? "http://localhost:8000" } },
});
