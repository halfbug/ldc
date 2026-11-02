import { test, expect, type APIRequestContext } from '@playwright/test';
import { API_URL, account, missing } from '../../data/env';
import { tokenFor } from '../../data/auth';

// Release 2 API checks: request size caps (ONLINE-8054), per-route limits (ONLINE-8053), the removed routes
// (ONLINE-8093, ONLINE-8055's redeem), and thread access across teachers (ONLINE-8093 T5).
// RAG_LOCAL is the rag the browser uses (the container forwards localhost:8002).

const AI = `${API_URL}ai/`;
const RAG = (process.env.E2E_RAG_LOCAL ?? 'http://localhost:8002').replace(/\/$/, '');

async function get(request: APIRequestContext, url: string, token: string) {
    return request.get(url, { headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' } });
}

test.describe('Release 2 · API', () => {
    test.skip(!account('teacher'), missing('teacher'));

    test('[ONLINE-8054] oversized stats and action previews answer 422', async ({ request }) => {
        const token = await tokenFor(request, 'teacher');
        const headers = { Authorization: `Bearer ${token}`, Accept: 'application/json' };
        const stats = await request.post(`${AI}stats`, { headers, data: { response: { x: 'a'.repeat(513 * 1024) } } });
        expect(stats.status()).toBe(422);
        expect(await stats.text()).toContain('may not be larger than');
        const preview = await request.post(`${AI}actions/preview`, { headers, data: { type: 'page.open', capability: 'page.open', params: { note: 'a'.repeat(600 * 1024) } } });
        expect(preview.status(), (await preview.text()).slice(0, 200)).toBe(422);
    });

    test('[ONLINE-8055] [ONLINE-8093] the redeem and other removed AI routes are gone', async ({ request }) => {
        const token = await tokenFor(request, 'teacher');
        const headers = { Authorization: `Bearer ${token}`, Accept: 'application/json' };
        for (const path of ['user/credits/redeem', 'credits/purchase', 'adapt', 'generate/question']) {
            expect((await request.post(`${AI}${path}`, { headers, data: {} })).status(), path).toBe(404);
        }
        expect((await get(request, `${AI}credits/packages`, token)).status()).toBe(404);
        expect((await get(request, `${AI}search-index/1`, token)).status()).toBe(404);
    });

    test('[ONLINE-8093] T5 another teacher cannot read a teacher\'s thread', async ({ request }) => {
        test.skip(!process.env.E2E_OTHER_TEACHER_USERNAME, 'set E2E_OTHER_TEACHER_USERNAME / _PASSWORD');
        const owner = await tokenFor(request, 'teacher');
        const credits = await (await get(request, `${AI}user/credits`, owner)).json();
        const listing = await request.post(`${RAG}/assistant/thread/listing`, {
            headers: { Authorization: `Bearer ${owner}` }, data: { user_id: String(credits.user_id), limit: 5, offset: 0 },
        });
        expect(listing.status()).toBe(200);
        const thread = (await listing.json()).threads.find((t: { core?: string }) => t.core === 'v2');
        test.skip(!thread, 'the teacher has no v2 thread yet');
        const login = await request.post(`${API_URL}auth/login`, {
            data: { username: process.env.E2E_OTHER_TEACHER_USERNAME, password: process.env.E2E_OTHER_TEACHER_PASSWORD },
        });
        const other = (await login.json()).access_token as string;
        const read = await request.post(`${RAG}/assistant/v2/thread/messages`, {
            headers: { Authorization: `Bearer ${other}` }, data: { thread_id: thread.thread_id },
        });
        const body = await read.text();
        console.log(`T5 other teacher → ${read.status()} ${body.slice(0, 160)}`);
        expect(read.status() === 403 || read.status() === 404 || !/"messages":\s*\[\s*\{/.test(body)).toBe(true);
    });

    test('[ONLINE-8053] heavy routes have their own per-user limit (catalog-search 30/min)', async ({ request }) => {
        test.setTimeout(120_000);
        const token = await tokenFor(request, 'teacher');
        const statuses: number[] = [];
        for (let i = 0; i < 32; i += 1) {
            statuses.push((await get(request, `${AI}catalog-search?term=maps`, token)).status());
        }
        console.log(`catalog-search statuses: ${statuses.join(',')}`);
        expect(statuses.slice(0, 30).every((s) => s !== 429)).toBe(true);
        expect(statuses.slice(30)).toContain(429);
    });
});
