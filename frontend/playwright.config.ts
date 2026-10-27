import { defineConfig } from "@playwright/test";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");
export default defineConfig({
  testDir: "./e2e",
  testMatch: "*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  reporter: "list",
  outputDir: "../local-data/playwright-results",
  use: {
    baseURL: "http://127.0.0.1:8011",
    channel: "chrome",
    viewport: { width: 1440, height: 1000 },
    launchOptions: {
      args: [
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
      ],
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `cd "${root}" && .venv/bin/python -m uvicorn tests.e2e.server:app --host 127.0.0.1 --port 8011`,
    url: "http://127.0.0.1:8011/api/v1/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
