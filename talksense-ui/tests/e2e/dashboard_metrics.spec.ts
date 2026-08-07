import { test, expect } from '@playwright/test';

test.describe('Dashboard Metrics', () => {
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

  test('Dynamically renders mock metrics via websocket', async ({ page }) => {
    let metricsWsServer;
    await page.routeWebSocket(/.*\/ws\/metrics\/.*/, ws => {
      metricsWsServer = ws;
      ws.onMessage(() => {});
    });

    await page.goto('/dashboard');
    
    // Switch to Meeting Mode
    const meetingModeBtn = page.getByText(/Meeting/i, { exact: false }).first();
    await meetingModeBtn.click();

    // Launch a session
    const startBtn = page.locator('button', { hasText: /Launch Live Session/i }).first();
    await expect(startBtn).toBeEnabled({ timeout: 10000 });
    await startBtn.click();
    await expect(page).toHaveURL(/.*\/dashboard\/[a-zA-Z0-9_-]+/, { timeout: 15000 });

    // Wait for the panel to show up
    const transcriptPanel = page.locator('h3', { hasText: /Live Transcript/i }).first();
    await expect(transcriptPanel).toBeVisible({ timeout: 15000 });

    // Wait for routeWebSocket handler to have caught the socket
    await expect.poll(() => metricsWsServer).toBeTruthy();

    // Wait for REST reconcileState to finish so it doesn't overwrite our mock data
    await page.waitForTimeout(2000);

    // Send mock metrics
    metricsWsServer.send(JSON.stringify({
      health_score: 85,
      sentiment: "positive",
      filler_penalty: 0,
      pause_penalty: 0,
      speaking_ratio: { "Speaker 1": 75, "Speaker 2": 25 },
      last_updated: Date.now()
    }));

    const body = page.locator('body');
    await expect(body).toContainText(/85/, { timeout: 10000 });
    await expect(body).toContainText(/75/, { timeout: 10000 });
  });
});
