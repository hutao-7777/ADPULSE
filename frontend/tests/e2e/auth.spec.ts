import { test, expect } from '@playwright/test';

const uniqueEmail = () => `e2e+${Date.now()}@example.com`;
const password = 'TestPass123!';

test.describe('auth flow', () => {
  test('a user can register, log out, and log back in', async ({ page }) => {
    const email = uniqueEmail();

    // Register
    await page.goto('/register');
    await page.getByLabel('邮箱').fill(email);
    await page.getByLabel('密码').first().fill(password);
    await page.getByLabel('确认密码').fill(password);
    await page.getByRole('button', { name: '注册' }).click();

    // Should land on dashboard after successful registration
    await page.waitForURL('/dashboard');
    await expect(page.getByRole('heading', { name: /数据看板|Dashboard/ })).toBeVisible();

    // Log out
    await page.getByRole('button', { name: email }).click();
    await page.getByRole('button', { name: '退出登录' }).click();
    await page.waitForURL('/login');

    // Log back in
    await page.getByLabel('邮箱').fill(email);
    await page.getByLabel('密码').fill(password);
    await page.getByRole('button', { name: '登录' }).click();

    await page.waitForURL('/dashboard');
    await expect(page.getByRole('heading', { name: /数据看板|Dashboard/ })).toBeVisible();
  });

  test('protected routes redirect anonymous users to login', async ({ page }) => {
    await page.goto('/api-keys');
    await page.waitForURL('/login');
    await expect(page.getByRole('heading', { name: '欢迎回到 AdPulse' })).toBeVisible();
  });
});
