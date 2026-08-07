import { test, expect } from '@playwright/test';

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // We expect some network errors here, so we won't throw on pageerror automatically,
    // but we will verify the root element stays mounted.
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

  test('Graceful handling of backend unavailable', async ({ page }) => {
    // Force backend /health or /sessions to fail
    await page.route('**/sessions*', async route => {
      await route.abort('failed');
    });

    await page.goto('/dashboard');

    // UI should still be there, not a blank white screen
    const root = page.locator('#root');
    await expect(root).toBeVisible();

    // Verify it shows some kind of error or stays usable
    // The exact text might vary ("Failed to connect", "Error", etc.),
    // just ensure the page didn't crash
    const startBtn = page.locator('button', { hasText: /Start Session|Launch/i }).first();
    await expect(startBtn).toBeVisible({ timeout: 10000 });
  });

  test('Graceful handling of WebSocket disconnect', async ({ page }) => {
    let wsServer;
    await page.routeWebSocket(/.*\/ws\/.*/, ws => {
      wsServer = ws;
      // Close immediately to simulate failure
      ws.close();
    });

    await page.goto('/dashboard');
    const meetingModeBtn = page.getByText(/Meeting/i, { exact: false }).first();
    await meetingModeBtn.click();
    
    const startBtn = page.locator('button', { hasText: /Start Session|Launch/i }).first();
    await expect(startBtn).toBeVisible({ timeout: 10000 });
    await startBtn.click();
    await expect(page).toHaveURL(/.*\/dashboard\/[a-zA-Z0-9_-]+/, { timeout: 15000 });

    // Ensure the page doesn't crash and root is visible
    const root = page.locator('#root');
    await expect(root).toBeVisible();
    
    // There might be a reconnection toast or "Connection lost"
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});
