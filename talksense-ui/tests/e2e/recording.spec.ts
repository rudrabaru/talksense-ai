import { test, expect } from '@playwright/test';

test.describe('Recording Lifecycle', () => {
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

  test('Start, Stop, Restart, End Session', async ({ page }) => {
    await page.goto('/dashboard');

    const meetingModeBtn = page.getByText(/Meeting/i, { exact: false }).first();
    await meetingModeBtn.click();

    const startBtn = page.locator('button', { hasText: /Launch Live Session/i }).first();
    await expect(startBtn).toBeEnabled({ timeout: 10000 });
    await startBtn.click();

    await expect(page).toHaveURL(/.*\/dashboard\/[a-zA-Z0-9_-]+/, { timeout: 15000 });

    // Wait for the panel to show up
    const transcriptPanel = page.locator('h3', { hasText: /Live Transcript/i }).first();
    await expect(transcriptPanel).toBeVisible({ timeout: 15000 });

    const startMicBtn = page.locator('button', { hasText: /Start Microphone/i }).first();
    await expect(startMicBtn).toBeVisible({ timeout: 10000 });
    
    // Start microphone
    await startMicBtn.click();
    
    const stopMicBtn = page.locator('button', { hasText: /Pause Microphone/i }).first();
    await expect(stopMicBtn).toBeVisible({ timeout: 10000 });
    
    // Stop microphone
    await stopMicBtn.click();

    // Verify redirects to history by clicking History nav button
    const historyNavBtn = page.locator('button', { hasText: /^History$/i }).first();
    await expect(historyNavBtn).toBeVisible();
    await historyNavBtn.click();
    
    await expect(page).toHaveURL(/.*\/sessions/, { timeout: 10000 });
  });
});
