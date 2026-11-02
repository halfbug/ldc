import { test, expect, type Page } from '@playwright/test';
import { HISTORY_ARTICLE_PATH, account, missing } from '../../data/env';
import { installAuthToken, tokenFor } from '../../data/auth';
import { Scout } from '../../pages/scout';
import { shot } from '../../data/shot';

// Release 2: District Insights speed and figures (ONLINE-7970), exports under the new limits (ONLINE-8053),
// admin Scout on Insights (ONLINE-7806, ONLINE-8060), and approving / declining a Scout change (ONLINE-8050, 8057).

async function openInsights(page: Page, report: string, heading: string): Promise<Scout> {
    const scout = new Scout(page);
    await page.goto(report);
    await scout.appReady();
    await page.getByTestId('tab-insights').click();
    await expect(page.getByRole('heading', { name: heading })).toBeVisible({ timeout: 60_000 });
    return scout;
}

async function figuresReady(page: Page): Promise<number> {
    const started = Date.now();
    await expect(page.locator('#insights-stands, :text("Has No Current Classes")').first()).toBeVisible({ timeout: 300_000 });
    return Math.round((Date.now() - started) / 1000);
}

test.describe('Release 2 · District Insights (district admin)', () => {
    test.skip(!account('districtAdmin'), missing('districtAdmin'));

    test.beforeEach(async ({ context, request }) => {
        await installAuthToken(context, await tokenFor(request, 'districtAdmin'));
    });

    test('[ONLINE-7970] Insights builds for the default window and a fresh 12-week window', async ({ page }) => {
        test.setTimeout(600_000);
        await openInsights(page, 'districtadmin/reports/assessment-score', 'District Insights');
        const first = await figuresReady(page);
        await shot(page, 'ONLINE-7970', '01-default-window');
        const headline = await page.locator('#insights-stands').innerText().catch(() => '');
        await page.locator('.v-field').filter({ has: page.getByRole('combobox', { name: 'Time window' }) }).click();
        await page.getByRole('option', { name: '12 weeks' }).click();
        const second = await figuresReady(page);
        await shot(page, 'ONLINE-7970', '02-12-week-window');
        await expect(page.getByText(/error|went wrong/i)).toHaveCount(0);
        test.info().annotations.push({ type: 'timing', description: `default ${first}s, 12 weeks ${second}s` });
        console.log(`ONLINE-7970 timing: default ${first}s, 12 weeks ${second}s; headline: ${headline.slice(0, 160)}`);
    });

    test('[ONLINE-8053] a meeting export downloads with no rate-limit error', async ({ page }) => {
        await openInsights(page, 'districtadmin/reports/assessment-score', 'District Insights');
        await figuresReady(page);
        await page.getByText('#Meeting Exports').click().catch(() => undefined);
        const card = page.locator('.v-card').filter({ hasText: 'District Summary' }).first();
        await card.scrollIntoViewIfNeeded();
        const download = page.waitForEvent('download', { timeout: 120_000 });
        await card.getByRole('button', { name: 'CSV' }).click();
        const file = await download;
        expect(file.suggestedFilename()).toMatch(/\.csv$/i);
        await shot(page, 'ONLINE-8053', '01-export-downloaded');
        await expect(page.getByText(/Too many requests/i)).toHaveCount(0);
    });

    test('[ONLINE-7806] What Scout Can Do lists the admin questions; an Insights question answers through the admin door', async ({ page }) => {
        const scout = await openInsights(page, 'districtadmin/reports/assessment-score', 'District Insights');
        await figuresReady(page);
        await page.getByRole('button', { name: 'Ask Scout About These Figures' }).click();
        await expect(scout.input).toBeVisible();
        await page.getByText('What Scout Can Do').first().click();
        await expect(page.locator('[aria-label="What Scout can do"]')).toBeVisible();
        await shot(page, 'ONLINE-7806', '01-admin-what-scout-can-do');
        await page.keyboard.press('Escape');
        await scout.newChat();
        const turn = await scout.ask('Which schools need support?', 'v2/admin/turn');
        expect(turn.status()).toBe(200);
        await shot(page, 'ONLINE-7806', '02-admin-answer');
        await expect(page.getByText(/Didn.t Finish|couldn.t find that conversation/i)).toHaveCount(0);
    });

    test('[ONLINE-8060] a few admin questions in a row all answer (under the 10-a-minute limit)', async ({ page }) => {
        test.setTimeout(420_000);
        const scout = await openInsights(page, 'districtadmin/reports/assessment-score', 'District Insights');
        await figuresReady(page);
        await page.getByRole('button', { name: 'Ask Scout About These Figures' }).click();
        await scout.newChat();
        for (const ask of ['How many teachers had digital activity?', 'What is the assessment average?', 'Which school has the most classes?']) {
            const turn = await scout.ask(ask, 'v2/admin/turn');
            expect(turn.status()).toBe(200);
        }
        await shot(page, 'ONLINE-8060', '01-admin-questions-in-a-row');
        await expect(page.getByText(/too many|slow down|limit/i)).toHaveCount(0);
    });
});

test.describe('Release 2 · School Insights (school admin)', () => {
    test.skip(!account('schoolAdmin'), missing('schoolAdmin'));

    test('[ONLINE-7806] school admin asks Scout on School Insights', async ({ page, context, request }) => {
        await installAuthToken(context, await tokenFor(request, 'schoolAdmin'));
        const scout = await openInsights(page, 'school-admin/reports/assessment-score', 'School Insights');
        await figuresReady(page);
        await page.getByRole('button', { name: 'Ask Scout About These Figures' }).click();
        await scout.newChat();
        const turn = await scout.ask('Which classes have had no scored assessment lately?', 'v2/admin/turn');
        expect(turn.status()).toBe(200);
        await shot(page, 'ONLINE-7806', '03-school-admin-answer');
    });
});

test.describe('Release 2 · approving a Scout change (teacher)', () => {
    test.skip(!account('teacher'), missing('teacher'));
    test.skip(!HISTORY_ARTICLE_PATH, 'set E2E_HISTORY_ARTICLE_PATH');

    test.beforeEach(async ({ context, request }) => {
        await installAuthToken(context, await tokenFor(request, 'teacher'));
    });

    async function propose(page: Page): Promise<Scout> {
        const scout = new Scout(page);
        await page.goto(HISTORY_ARTICLE_PATH!);
        await scout.appReady();
        await scout.open();
        await scout.newChat();
        await scout.ask('Assign this article to my class, due 2026-11-06.');
        const card = page.locator('.ai-approval__btn--proceed').last();
        // Scout may first confirm a step (save a copy, then assign); answering yes reaches the approval card.
        for (let round = 0; round < 2 && !(await card.isVisible().catch(() => false)); round += 1) {
            await scout.ask('Yes, do that.');
        }
        await expect(card).toBeVisible({ timeout: 60_000 });
        return scout;
    }

    test('[ONLINE-8057] declining a proposed change leaves nothing applied', async ({ page }) => {
        await propose(page);
        await shot(page, 'ONLINE-8057', '01-approval-card');
        const confirms: string[] = [];
        page.on('request', (r) => { if (/\/ai\/actions\/[^/]+\/confirm/.test(r.url())) confirms.push(r.url()); });
        await page.locator('.ai-approval__btn--decline').last().click();
        await expect(page.getByText('Declined').last()).toBeVisible({ timeout: 30_000 });
        await shot(page, 'ONLINE-8057', '02-declined');
        expect(confirms).toEqual([]);
    });

    test('[ONLINE-8050] double-clicking Approve applies the change once', async ({ page }) => {
        await propose(page);
        const calls: string[] = [];
        page.on('response', (r) => { if (/\/ai\/actions\/[^/?]+\/(confirm|result)/.test(r.url())) calls.push(`${r.url().split('/ai/actions/')[1].replace(/^[^/]+/, 'id').split('?')[0]} ${r.status()}`); });
        await page.locator('.ai-approval__btn--proceed').last().dblclick();
        await expect(page.getByText('Approved', { exact: true }).last()).toBeVisible({ timeout: 60_000 });
        await page.waitForTimeout(4_000);
        await shot(page, 'ONLINE-8050', '01-approved-once');
        console.log(`ONLINE-8050 action calls: ${calls.join(', ')}`);
        expect(calls.filter((c) => c.startsWith('id/confirm 2')).length, calls.join(', ')).toBeLessThanOrEqual(1);
        expect(calls.filter((c) => c.startsWith('id/result 2')).length, calls.join(', ')).toBeLessThanOrEqual(1);
        await expect(page.locator('.ai-approval__btn--proceed')).toHaveCount(0);
    });
});
