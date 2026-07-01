import { test, expect } from '@playwright/test';

test.describe('Transcript rendering', () => {
  test.beforeEach(({ page }) => {
    page.on('pageerror', (err) => {
      throw new Error(`Uncaught exception: ${err.message}`);
    });
  });

  test('Mocks transcript websocket and verifies rendering', async ({ page }) => {
    // Intercept the transcript WebSocket
    let transcriptWsServer;
    await page.routeWebSocket(/.*\/ws\/transcript\/.*/, ws => {
      transcriptWsServer = ws;
      // Accept connection but do not connect to the real backend
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
    await expect.poll(() => transcriptWsServer).toBeTruthy();

    // Wait for REST reconcileState to finish so it doesn't overwrite our mock data
    await page.waitForTimeout(2000);

    // Inject mock transcript
    transcriptWsServer.send(JSON.stringify({
      segment_id: "mock_123",
      speaker: "Speaker 1",
      text: "This is a mock injected transcript.",
      start: 0.0,
      end: 2.5
    }));

    // Verify UI updates
    const transcriptText = page.locator('text="This is a mock injected transcript."');
    await expect(transcriptText).toBeVisible({ timeout: 10000 });

    const speakerLabel = page.getByText('Speaker 1').first();
    await expect(speakerLabel).toBeVisible();
  });
});
