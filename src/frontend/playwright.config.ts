import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../.. && . .venv/bin/activate && ENABLE_TRACING=false USE_AZURE_SERVICES=false uvicorn src.backend.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/benchmarking/capabilities",
      reuseExistingServer: true,
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: true,
    },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});