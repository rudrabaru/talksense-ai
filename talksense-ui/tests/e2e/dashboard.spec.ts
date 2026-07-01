import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test('Dashboard loads with modes and audio sources', async ({ page }) => {
    await page.goto('/dashboard');

    // Verify Title
    await expect(page).toHaveTitle(/TalkSense AI|Vite \+ React/i);

    // Verify Session Modes
    await expect(page.getByText(/Meeting/i, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/Sales/i, { exact: false }).first()).toBeVisible();

    // Verify Audio Source select/options exist
    // The Audio Source might be a <select> or buttons.
    // In talksense-ui it is a select dropdown or group of radio buttons.
    // Let's verify standard keywords exist on the page
    const bodyText = page.locator('body');
    await expect(bodyText).toContainText(/Microphone/i);
    await expect(bodyText).toContainText(/System Audio/i);
    // Mixed audio might or might not be visible, but we verify it if it exists or just accept Microphone/System Audio.
  });
});
