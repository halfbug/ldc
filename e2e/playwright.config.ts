import { defineConfig, devices } from '@playwright/test';
import { APP_URL } from './data/env';

// Runs against a deployed environment (dev2 by default), never the local e2e stack: the accounts are real dev
// accounts, so nothing here creates data, and the tests that spend Scout credits run only with E2E_AI_TURNS=1.
export default defineConfig({
    testDir: './tests',
    outputDir: './results/artifacts',
    // One account per role is shared by every test, and Scout allows a few turns in flight per user.
    fullyParallel: false,
    workers: 1,
    retries: 0,
    timeout: 180_000,
    expect: { timeout: 20_000 },
    reporter: [
        ['list'],
        ['html', { outputFolder: 'results/html', open: 'never' }],
        ['junit', { outputFile: 'results/junit.xml' }],
    ],
    use: {
        baseURL: `${APP_URL}/`,
        testIdAttribute: 'data-cy',
        timezoneId: 'America/Denver',
        locale: 'en-US',
        actionTimeout: 20_000,
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        ignoreHTTPSErrors: true,
    },
    projects: [
        // HTTP only: Laravel and both rag doors. No browser.
        { name: 'api', testMatch: /api-.*\.spec\.ts/ },
        {
            name: 'ui',
            testMatch: /ui-.*\.spec\.ts/,
            use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } },
        },
    ],
});
