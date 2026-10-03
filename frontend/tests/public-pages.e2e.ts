import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('welcome page fits a narrow phone and offers both sign-in choices', async ({ app, agent, browser, screen }) => {
  await app.open('/');
  await expect(screen.getByRole('button', 'Google로 시작하기')).toBeVisible();
  await expect(screen.getByRole('button', '카카오로 시작하기')).toBeVisible();
  await agent.assert('Both sign-in buttons are visible and usable on the phone screen, with no content clipped horizontally.', { vision: true });
  expect(await browser.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
