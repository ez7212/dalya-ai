import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 3000);
const baseUrl = process.env.BASE_URL || `http://${host}:${port}`;
const showcaseUrl = `${baseUrl}/component-showcase`;
const outputDir = path.resolve("test-results/component-showcase");

let devServer;
let browser;

async function isReachable(url) {
  try {
    const response = await fetch(url, { redirect: "manual" });
    return response.status < 500;
  } catch {
    return false;
  }
}

async function waitForReachable(url, timeoutMs = 60_000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    if (await isReachable(url)) {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Timed out waiting for ${url}`);
}

async function ensureDevServer() {
  if (await isReachable(showcaseUrl)) {
    console.log(`Using existing server at ${baseUrl}`);
    return;
  }

  console.log(`Starting Next dev server at ${baseUrl}`);
  devServer = spawn(
    "npm",
    ["run", "dev", "--", "--hostname", host, "--port", String(port)],
    {
      cwd: process.cwd(),
      env: { ...process.env, BROWSER: "none" },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  devServer.stdout.on("data", (chunk) => {
    process.stdout.write(`[next] ${chunk}`);
  });
  devServer.stderr.on("data", (chunk) => {
    process.stderr.write(`[next] ${chunk}`);
  });

  devServer.on("exit", (code) => {
    if (code !== null && code !== 0 && code !== 143) {
      console.error(`Next dev server exited with code ${code}`);
    }
  });

  await waitForReachable(showcaseUrl);
}

async function assertVisible(page, text, options = {}) {
  const locator = page.getByText(text, options).first();
  await locator.waitFor({ state: "visible", timeout: 10_000 });

  const box = await locator.boundingBox();
  if (!box || box.width <= 0 || box.height <= 0) {
    throw new Error(`Expected visible text with non-empty box: ${text}`);
  }
}

async function main() {
  await mkdir(outputDir, { recursive: true });
  await ensureDevServer();

  browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 380, height: 1200 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
  });

  await page.goto(showcaseUrl, { waitUntil: "networkidle" });

  const checks = [
    "Shared UI component showcase",
    "InspectionAudioInput",
    "ConversationView",
    "DraftMessageCard",
    "InterestedBuyersPanel",
    "UnitProfileView",
    "Property Advisor",
    "Voice note transcription",
    "offer:",
    "AED 2,300,000",
    "Low confidence",
    "Buyers who may be interested",
    "Agent-recorded",
    "Add or update notes",
    "No matching buyers yet",
  ];

  for (const text of checks) {
    await assertVisible(page, text, { exact: false });
  }

  const audioPlayers = await page.locator("audio").count();
  if (audioPlayers > 0) {
    throw new Error("Conversation showcase must not render an audio player");
  }

  await page.screenshot({
    path: path.join(outputDir, "component-showcase-380-full.png"),
    fullPage: true,
  });

  const components = [
    ["inspection-audio-input", "InspectionAudioInput"],
    ["conversation-view", "ConversationView"],
    ["draft-message-card", "DraftMessageCard"],
    ["interested-buyers-panel", "InterestedBuyersPanel"],
    ["unit-profile-view", "UnitProfileView"],
  ];

  for (const [fileName, heading] of components) {
    const section = page.getByText(heading, { exact: true }).first();
    await section.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: path.join(outputDir, `${fileName}-380.png`),
      fullPage: false,
    });
  }

  await browser.close();
  browser = undefined;
  console.log(`Component showcase visual verification passed: ${showcaseUrl}`);
  console.log(`Screenshots written to ${outputDir}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (browser) {
      await browser.close();
    }
    if (devServer && !devServer.killed) {
      devServer.kill("SIGTERM");
    }
  });
