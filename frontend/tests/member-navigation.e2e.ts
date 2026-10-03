import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test('member can open feedback from home', { session: 'member' }, async ({ app, agent, browser, screen }) => {
  await app.open('/home');
  await expect(screen.getByRole('navigation', '하단 내비게이션')).toBeVisible();
  await agent.act('Use the bottom navigation to open 피드백. Do not start a conversation or change any data.');
  await expect(browser).toHaveURL('/history');
  await expect(screen.getByRole('heading', 'History')).toBeVisible();
  await expect(screen.getByRole('alert').filter({ hasText: /\S/ })).toHaveCount(0);
});
