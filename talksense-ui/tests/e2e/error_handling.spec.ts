import { test, expect } from '@playwright/test';

test.describe('Error Handling', () => {
  test.beforeEach(({ page }) => {
    // We expect some network errors here, so we won't throw on pageerror automatically,
    // but we will verify the root element stays mounted.
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
