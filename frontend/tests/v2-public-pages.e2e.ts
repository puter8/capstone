import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('v2 welcome page fits a narrow phone and offers both sign-in choices', async ({ app, agent, browser, screen }) => {
  await app.open('/v2');
  await expect(screen.getByRole('button', 'Google로 시작하기')).toBeVisible();
  await expect(screen.getByRole('button', '카카오로 시작하기')).toBeVisible();
  await agent.assert('A dark screen shows the Pally wordmark, the character, the headline and two full-width sign-in buttons, with no content clipped horizontally.', { vision: true });
  expect(await browser.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
