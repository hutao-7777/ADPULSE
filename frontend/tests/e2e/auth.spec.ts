import { test, expect } from '@playwright/test';

test.describe('smoke tests', () => {
  test('dashboard loads and shows seeded KPIs', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: '发布商仪表盘' })).toBeVisible();
  });

  test('api keys page loads with correct Chinese text', async ({ page }) => {
    await page.goto('/api-keys');
    await expect(page.getByRole('heading', { name: 'API 密钥' })).toBeVisible();
    await expect(page.getByText('管理用于 DSP/RTB 集成的 API Key')).toBeVisible();
    await expect(page.getByRole('button', { name: '新增 API Key' })).toBeVisible();
  });

  test('navigation between pages works', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: '媒体主' }).click();
    await expect(page).toHaveURL(/\/publishers/);
    await page.getByRole('link', { name: '广告位' }).click();
    await expect(page).toHaveURL(/\/ad-units/);
    await page.getByRole('link', { name: '流量质量' }).click();
    await expect(page).toHaveURL(/\/traffic/);
    await page.getByRole('link', { name: 'API 密钥' }).click();
    await expect(page).toHaveURL(/\/api-keys/);
  });
});
