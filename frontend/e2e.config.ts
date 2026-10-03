import type { E2EConfig } from 'e2e';
import { web } from '@e2e-dev/web';
import { chatgpt } from 'e2e/oauth/chatgpt';

export default {
  agents: {
    default: {
      model: chatgpt('gpt-6.1-sol'),
      system: 'Test only the requested flow. Do not enter credentials, approve OAuth access, pay, delete data, or submit forms.',
    },
  },
  targets: [{
    name: 'mobile-360',
    engine: web({ viewport: { width: 360, height: 800 } }),
    app: {
      url: process.env.APP_URL ?? 'http://localhost:3000',
    },
  }],
} satisfies E2EConfig;
