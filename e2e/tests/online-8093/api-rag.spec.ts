import { test, expect } from '@playwright/test';
import { AI_HOST, CORE_URL, GW_URL, account, missing } from '../../data/env';
import { tokenFor } from '../../data/auth';

// ONLINE-8093 test cases 2, 20, 23 and 24, rag side. Every call is refused before a model runs, so nothing here
// spends credits. Paced for the throttle, which also counts refused requests.

const PAUSE_MS = 13_000;
const host = `host=${encodeURIComponent(AI_HOST)}`;

test.describe('ONLINE-8093 · rag API Gateway', () => {
    test.skip(!GW_URL, 'set E2E_GW_URL (the gateway base ending in /v3)');
    test.beforeEach(() => {
        test.skip(!GW_URL?.endsWith('/v3'), `E2E_GW_URL must end in /v3 (case 2); got ${GW_URL}`);
    });

    test('#2 /v3 thread route answers; unprefixed and removed routes are 404', async ({ request }) => {
        test.skip(!account('teacher'), missing('teacher'));
        const headers = { Authorization: `Bearer ${await tokenFor(request, 'teacher')}` };

        const noThread = await request.post(`${GW_URL}/assistant/thread/messages?${host}`, { headers, data: {} });
        expect(noThread.status()).toBe(400);
        expect(await noThread.text()).toContain('thread_id is required');
        await new Promise((r) => setTimeout(r, PAUSE_MS));

        const root = GW_URL!.replace(/\/v3$/, '');
        for (const path of ['assistant/thread/listing', 'v3/generate', 'v3/generate-from-topic']) {
            const gone = await request.post(`${root}/${path}?${host}`, { headers, data: {} });
            expect(gone.status(), `${path}: ${await gone.text()}`).toBe(404);
            await new Promise((r) => setTimeout(r, PAUSE_MS));
        }
    });
});

test.describe('ONLINE-8093 · rag Function URL', () => {
    test.skip(!CORE_URL, 'set E2E_CORE_URL (the Lambda Function URL root)');

    test('#24 no token is 401; a path outside /assistant/v2/ is 404', async ({ request }) => {
        const anonymous = await request.post(`${CORE_URL}/assistant/v2/turn?${host}`, { data: {} });
        expect(anonymous.status()).toBe(401);
        expect(await anonymous.text()).toContain('not_signed_in');
        await new Promise((r) => setTimeout(r, PAUSE_MS));

        test.skip(!account('teacher'), missing('teacher'));
        const headers = { Authorization: `Bearer ${await tokenFor(request, 'teacher')}` };
        const outside = await request.post(`${CORE_URL}/assistant/v1/turn?${host}`, { headers, data: {} });
        expect(outside.status()).toBe(404);
        expect(await outside.text()).toContain('not_found');
    });

    test('#20 a teacher on the admin door is 403 scout_off', async ({ request }) => {
        test.skip(!account('teacher'), missing('teacher'));
        await new Promise((r) => setTimeout(r, PAUSE_MS));
        const headers = { Authorization: `Bearer ${await tokenFor(request, 'teacher')}` };
        const refused = await request.post(`${CORE_URL}/assistant/v2/admin/turn?${host}`, { headers, data: {} });
        expect(refused.status()).toBe(403);
        expect(await refused.text()).toContain('scout_off');
    });
});
