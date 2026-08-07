import { test, expect } from '@playwright/test';

test.describe('Launch Flow', () => {
  test.beforeEach(async ({ page }) => {
    page.on('pageerror', (err) => {
      throw new Error(`Uncaught exception: ${err.message}`);
    });
    await page.route(/.*localhost:8000\/sessions.*/, async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ json: { session_id: 'mock_session_123', ws_token: 'fake_token' }, headers: { 'Access-Control-Allow-Origin': '*' } });
      } else {
        await route.fulfill({ json: { id: 'mock_session_123', mode: 'meeting', status: 'active' }, headers: { 'Access-Control-Allow-Origin': '*' } });
      }
    });
    await page.route(/.*localhost:8000\/dashboard\/.*/, async route => {
      await route.fulfill({ json: { status: 'active', transcript_segments: [] }, headers: { 'Access-Control-Allow-Origin': '*' } });
    });
    await page.route(/.*localhost:8000\/clients.*/, async route => {
      await route.fulfill({ json: [], headers: { 'Access-Control-Allow-Origin': '*' } });
    });
    await page.routeWebSocket(/.*localhost:8000\/ws\/.*/, ws => {
      ws.onMessage(() => {});
    });
  });

  test('Starts a live session from the dashboard', async ({ page }) => {
    await page.goto('/dashboard');

    const meetingModeBtn = page.getByText(/Meeting/i, { exact: false }).first();
    await meetingModeBtn.click();

    const startBtn = page.locator('button', { hasText: /Launch Live Session/i }).first();
    await expect(startBtn).toBeEnabled({ timeout: 10000 });
    await startBtn.click();

    await expect(page).toHaveURL(/.*\/dashboard\/[a-zA-Z0-9_-]+/, { timeout: 15000 });

    // Wait for the panel to show up, meaning the session loaded and WS connected
    const transcriptPanel = page.locator('h3', { hasText: /Live Transcript/i }).first();
    await expect(transcriptPanel).toBeVisible({ timeout: 15000 });

    // Verify Start Microphone button is present
    const startMicBtn = page.locator('button', { hasText: /Start Microphone/i }).first();
    await expect(startMicBtn).toBeVisible({ timeout: 10000 });
  });
});
