import { test, expect, type Page, type Response } from '@playwright/test';
import { AI_TURNS, CHIP_LABEL, CHIP_PAGE_PATH, HISTORY_ARTICLE_PATH, LEGACY_THREAD_TITLE, SEARCH_TERM, account, missing } from '../../data/env';
import { installAuthToken, tokenFor } from '../../data/auth';
import { Scout } from '../../pages/scout';
import { snap } from '../../data/snap';

// ONLINE-8093 teacher cases (ONLINE-8093.md). Cases that send a real turn spend Scout credits and run only with
// E2E_AI_TURNS=1; cases that need a specific page or thread run only when its E2E_* input is set.

test.describe('ONLINE-8093 · teacher Scout', () => {
    test.skip(!account('teacher'), missing('teacher'));

    let gatewayErrors: string[];

    test.beforeEach(async ({ page, context, request }) => {
        await installAuthToken(context, await tokenFor(request, 'teacher'));
        gatewayErrors = [];
        page.on('response', (r: Response) => {
            if (r.url().includes('/assistant/thread') && r.status() >= 400) gatewayErrors.push(`${r.status()} ${r.url()}`);
        });
    });

    async function openScout(page: Page, path = ''): Promise<Scout> {
        const scout = new Scout(page);
        await page.goto(path);
        await scout.appReady();
        await scout.open();
        return scout;
    }

    test('#2 the sidebar loads through the /v3 gateway with no errors', async ({ page }) => {
        const listing = page.waitForResponse((r) => r.url().includes('/assistant/thread/listing'));
        const scout = await openScout(page);
        await scout.showConversations();
        const response = await listing;
        // A local stack calls rag directly (no API Gateway, so no /v3): E2E_EXPECT_V3=0 there.
        if (process.env.E2E_EXPECT_V3 !== '0') {
            expect(new URL(response.url()).pathname).toMatch(/\/v3\/assistant\/thread\/listing$/);
        }
        await snap(page, 'sidebar');
        expect(response.status()).toBe(200);
        expect(gatewayErrors).toEqual([]);
    });

    test('#1 #3 #9 a plain turn streams, the chat gets one title with no student name, and no "K-12"', async ({ page }) => {
        test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
        const scout = await openScout(page);
        await scout.newChat();

        // The title request follows the turn (POST /assistant/thread after /v2/turn).
        const created = page.waitForResponse((r) => /\/assistant\/thread(\?|$)/.test(r.url()) && r.request().method() === 'POST', { timeout: 150_000 });
        const turn = await scout.ask('Write a short lesson plan for my students about reading a map.');
        await snap(page, 'lesson-plan-reply');
        expect(turn.status()).toBe(200);
        const thread = await created;
        expect(thread.status()).toBe(200);
        const { title } = (await thread.json()) as { title?: string };
        expect(title, 'one title from generate_title').toBeTruthy();
        expect(title).not.toMatch(/Student \d+/);

        const reply = await scout.lastReply().innerText();
        expect(reply.length).toBeGreaterThan(20);
        expect(reply).not.toMatch(/\bK[-–]12\b/);
        expect(reply).not.toMatch(/content check/i);
        expect(gatewayErrors).toEqual([]);
    });

    test('#4 a history article lesson plan is not stopped by the content check', async ({ page }) => {
        test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
        test.skip(!HISTORY_ARTICLE_PATH, 'set E2E_HISTORY_ARTICLE_PATH to a history article (war, slavery, Loyalists)');
        const scout = await openScout(page, HISTORY_ARTICLE_PATH);
        await scout.newChat();
        const turn = await scout.ask('Make a lesson plan on this article.');
        await snap(page, 'history-article');
        expect(turn.status()).toBe(200);
        await expect(page.getByText(/content check/i)).toHaveCount(0);
    });

    test('#15 Stop before the first token says so and cancels the turn', async ({ page }) => {
        test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
        const scout = await openScout(page);
        await scout.newChat();
        const cancel = page.waitForRequest((r) => r.url().includes('/assistant/v2/turn/cancel'), { timeout: 30_000 }).catch(() => null);
        await scout.input.fill('Write a detailed five-day unit plan on the water cycle with assessments.');
        await scout.send.click();
        await scout.stop.click();
        await page.waitForTimeout(1500);
        await snap(page, 'stopped');
        await expect(page.getByText('You stopped this answer before it started.').or(page.locator('.ai-message__stopped')).first()).toBeVisible();
        const request = await cancel;
        if (request) expect((await request.response())?.status()).toBe(200);
    });

    test('#10 a chip-started chat can be continued by typing (no 409)', async ({ page }) => {
        test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
        test.skip(!CHIP_LABEL, 'set E2E_CHIP_LABEL (and E2E_CHIP_PAGE_PATH) to an action chip');
        const scout = await openScout(page, CHIP_PAGE_PATH);
        await scout.newChat();
        const recorded = page.waitForResponse((r) => r.url().includes('/assistant/thread/record'), { timeout: 60_000 });
        await page.getByRole('button', { name: CHIP_LABEL }).first().click();
        expect((await recorded).status()).toBe(200);
        const turn = await scout.ask('Thanks. Can you summarise what you just did in one sentence?');
        expect(turn.status()).toBe(200);
        await expect(page.getByText(/thread_is_v1|409/)).toHaveCount(0);
    });

    test('#12 an old (pre-release) chat opens with its messages', async ({ page }) => {
        test.skip(!LEGACY_THREAD_TITLE, 'set E2E_LEGACY_THREAD_TITLE to a chat from before the release');
        const scout = await openScout(page);
        await scout.showConversations();
        const messages = page.waitForResponse((r) => r.url().includes('/thread/messages'));
        await page.getByRole('button', { name: `Open ${LEGACY_THREAD_TITLE}` }).first().click();
        const response = await messages;
        await page.waitForTimeout(1500);
        await snap(page, 'legacy-thread');
        expect(response.status()).toBe(200);
        const body = (await response.json()) as { messages?: unknown[] };
        // Empty means not migrated: core_legacy_threads has no copy (migrate-legacy-threads --apply not run).
        expect(body.messages?.length ?? 0, 'blank chat: has migrate-legacy-threads run on this environment?').toBeGreaterThan(0);
    });

    test('#14 a chat opened from search is revealed in the sidebar', async ({ page }) => {
        test.skip(!SEARCH_TERM, 'set E2E_SEARCH_TERM to a word in an old chat title');
        const scout = await openScout(page);
        await scout.showConversations();
        await page.getByRole('button', { name: 'Search your chats' }).first().click();
        await page.getByRole('textbox', { name: 'Search your chats' }).or(page.getByLabel('Search your chats')).last().fill(SEARCH_TERM!);
        // AiThreadSearch: results are role="option" in a role="listbox"; the last one is usually the oldest.
        const result = page.getByRole('listbox').getByRole('option').filter({ hasText: new RegExp(SEARCH_TERM!, 'i') }).last();
        await snap(page, 'search-results');
        await result.click();
        const active = page.locator('.history-item.active-chat');
        await expect(active).toBeVisible({ timeout: 60_000 });
        await expect(active).toBeInViewport();
        await snap(page, 'search-reveal');
    });
});
