import { test, expect, type Page } from '@playwright/test';
import { AI_TURNS, account, missing } from '../../data/env';
import { installAuthToken, tokenFor } from '../../data/auth';
import { Scout } from '../../pages/scout';
import { snap } from '../../data/snap';

// ONLINE-8093 admin cases 16-18 (ONLINE-8093.md). The Insights tab and its "Ask Scout" button come from
// frontend-v3 (ReportTabs.vue / SchoolReportTabs.vue `data-cy="tab-insights"`, InsightsPage.vue).

const LEVELS = [
    { role: 'districtAdmin' as const, report: 'districtadmin/reports/assessment-score', heading: 'District Insights', case: '#16' },
    { role: 'schoolAdmin' as const, report: 'school-admin/reports/assessment-score', heading: 'School Insights', case: '#17' },
];

async function openInsights(page: Page, report: string, heading: string): Promise<Scout> {
    const scout = new Scout(page);
    await page.goto(report);
    await scout.appReady();
    await page.getByTestId('tab-insights').click();
    await expect(page.getByRole('heading', { name: heading })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('insights-bar')).toBeVisible({ timeout: 60_000 });
    return scout;
}

for (const level of LEVELS) {
    test.describe(`ONLINE-8093 · ${level.heading} Scout`, () => {
        test.skip(!account(level.role), missing(level.role));

        test.beforeEach(async ({ context, request }) => {
            await installAuthToken(context, await tokenFor(request, level.role));
        });

        test(`${level.case} Insights opens and Ask Scout is offered`, async ({ page }) => {
            await openInsights(page, level.report, level.heading);
            await snap(page, `${level.role}-insights`);
            await expect(page.getByRole('button', { name: 'Ask Scout About These Figures' })).toBeVisible();
        });

        test(`${level.case} an Insights question goes through the admin door`, async ({ page }) => {
            test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
            const scout = await openInsights(page, level.report, level.heading);
            const ask = page.getByRole('button', { name: 'Ask Scout About These Figures' });
            await expect(ask).toBeEnabled({ timeout: 120_000 });
            await ask.click();
            await expect(scout.input).toBeVisible();
            const turn = await scout.ask('Which classes are furthest behind on assignments?', 'v2/admin/turn');
            await snap(page, `${level.role}-admin-reply`);
            expect(turn.status()).toBe(200);
            const reply = await scout.lastReply().innerText();
            expect(reply.length).toBeGreaterThan(20);
            await expect(page.getByText("I couldn't find that conversation.")).toHaveCount(0);
        });

        test(`#18 ${level.heading}: a new question after reopening another chat starts a new chat`, async ({ page }) => {
            test.skip(!AI_TURNS, 'spends credits: set E2E_AI_TURNS=1');
            const scout = await openInsights(page, level.report, level.heading);
            await page.getByRole('button', { name: 'Ask Scout About These Figures' }).click();
            await scout.showConversations();
            const rows = page.locator('.history-item');
            await rows.first().waitFor({ state: 'visible', timeout: 20_000 }).catch(() => undefined);
            test.skip((await rows.count()) === 0, 'no earlier chat to reopen');
            const replay = page.waitForResponse((r) => r.url().includes('/thread/messages'));
            await rows.first().getByRole('button').first().click();
            const body = (await (await replay).json()) as { admin_can_continue?: boolean };
            const created = page.waitForResponse((r) => /\/assistant\/thread(\?|$)/.test(r.url()) && r.request().method() === 'POST', { timeout: 30_000 }).catch(() => null);
            const turn = await scout.ask('Summarise these figures in one sentence.', 'v2/admin/turn');
            expect(turn.status()).toBe(200);
            if (body.admin_can_continue === false) {
                expect(await created, 'ONLINE-7806: a thread admin Scout cannot continue starts a new chat').not.toBeNull();
            }
            await expect(page.getByText("I couldn't find that conversation.")).toHaveCount(0);
        });
    });
}
