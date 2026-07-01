import { test, expect } from '@playwright/test';

test.describe('Navigation Flow', () => {
  test('Home page loads and basic navigation works', async ({ page }) => {
    // Navigate to Home Page
    await page.goto('/');

    // Verify Title
    await expect(page).toHaveTitle(/TalkSense AI|Vite \+ React/i);

    // Verify Dashboard navigation exists and works
    const dashboardLink = page.getByRole('button', { name: /Dashboard/i });
    await expect(dashboardLink).toBeVisible();
    await dashboardLink.click();
    await expect(page).toHaveURL(/.*\/dashboard/);

    // Go back to home
    await page.goto('/');

    // Verify History navigation exists and works
    const historyLink = page.getByRole('button', { name: /History/i });
    await expect(historyLink).toBeVisible();
    await historyLink.click();
    await expect(page).toHaveURL(/.*\/sessions/);

    // Go back to home
    await page.goto('/');

    // Verify Start Analysis button exists and works
    const startAnalysisBtn = page.getByRole('button', { name: /Start Analysis/i });
    await expect(startAnalysisBtn).toBeVisible();
    await startAnalysisBtn.click();
    await expect(page).toHaveURL(/.*\/upload/);

    // Verify no React crash (a basic root element should still be visible)
    const root = page.locator('#root');
    await expect(root).toBeVisible();
  });
});
