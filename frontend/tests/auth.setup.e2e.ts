import { test } from '@e2e-dev/web';
import { expect } from 'e2e';

test.setup('sign in to Pally with Kakao', { sessions: ['member'], timeout: 180_000 }, async ({ app, browser, screen, session }) => {
  await app.open('/');
  await screen.getByRole('button', '카카오로 시작하기').tap();
  // A person completes Kakao sign-in and onboarding in the headed browser.
  await expect(browser).toHaveURL('/home', { timeout: 170_000 });
  await session.save('member');
});
