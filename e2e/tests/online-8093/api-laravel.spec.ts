import { test, expect, type APIRequestContext } from '@playwright/test';
import { API_URL, account, missing, type Role } from '../../data/env';
import { tokenFor } from '../../data/auth';

// ONLINE-8093 test cases 20-23 and 26 (ONLINE-8093.md), Laravel side. Read-only: the one POST fails validation.

const AI = `${API_URL}ai/`;

async function call(request: APIRequestContext, method: 'GET' | 'POST', path: string, token?: string, data?: unknown) {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = method === 'GET'
        ? await request.get(`${AI}${path}`, { headers })
        : await request.post(`${AI}${path}`, { headers, data: data ?? {} });
    return { status: response.status(), body: await response.text() };
}

function needs(role: Role) {
    test.skip(!account(role), missing(role));
}

test.describe('ONLINE-8093 · Laravel api/ai', () => {
    test('guest is unauthenticated on user/credits', async ({ request }) => {
        expect((await call(request, 'GET', 'user/credits')).status).toBe(401);
    });

    test('#21 teacher gets credits; admin context is forbidden to a teacher', async ({ request }) => {
        needs('teacher');
        const token = await tokenFor(request, 'teacher');
        const credits = await call(request, 'GET', 'user/credits', token);
        expect(credits.status, credits.body).toBe(200);
        expect(credits.body).toContain('credit');
        expect((await call(request, 'GET', 'admin/context', token)).status).toBe(403);
    });

    for (const role of ['districtAdmin', 'schoolAdmin'] as const) {
        test(`#21 ${role}: teacher-only user/credits is 404, admin/context is 200`, async ({ request }) => {
            needs(role);
            const token = await tokenFor(request, role);
            expect((await call(request, 'GET', 'user/credits', token)).status).toBe(404);
            const context = await call(request, 'GET', 'admin/context', token);
            expect(context.status, context.body).toBe(200);
        });
    }

    test('#22 AI flag off: user/credits is 404', async ({ request }) => {
        needs('noFlagTeacher');
        expect((await call(request, 'GET', 'user/credits', await tokenFor(request, 'noFlagTeacher'))).status).toBe(404);
    });

    test('#26 stats response over 512 KB is 422 and names the cap', async ({ request }) => {
        needs('teacher');
        const big = { response: { x: 'a'.repeat(513 * 1024) } };
        const result = await call(request, 'POST', 'stats', await tokenFor(request, 'teacher'), big);
        expect(result.status).toBe(422);
        expect(result.body).toContain('may not be larger than 512 KB');
    });

    // AiUnusedRoutesRemovedTest: every one of these is gone.
    const REMOVED: [method: 'GET' | 'POST', path: string, body?: unknown][] = [
        ['POST', 'generate/question'],
        ['POST', 'article/difficulty'],
        ['POST', 'adapt'],
        ['GET', 'random-article'],
        ['POST', 'credits/purchase'],
        ['GET', 'credits/expire'],
        ['POST', 'feedback', { rating: 1, ai_feature: 'adapt_content' }],
        ['GET', 'credits/packages'],
        ['POST', 'user/credits/redeem', { code: 'unused' }],
        ['GET', 'search-index/1'],
    ];
    for (const [method, path, body] of REMOVED) {
        test(`#23 removed route ${method} api/ai/${path} is 404`, async ({ request }) => {
            needs('teacher');
            const result = await call(request, method, path, await tokenFor(request, 'teacher'), body);
            expect(result.status, result.body.slice(0, 200)).toBe(404);
        });
    }
});
