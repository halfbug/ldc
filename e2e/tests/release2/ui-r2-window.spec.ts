import { test, expect, type Page } from '@playwright/test';
import { account, missing } from '../../data/env';
import { installAuthToken, tokenFor } from '../../data/auth';
import { Scout } from '../../pages/scout';
import { shot } from '../../data/shot';

// Release 2 (ONLINE-5385_scout_release_2): the Scout window click-through (ONLINE-8027), cancelling abandoned turns
// (ONLINE-8051) and the duplicate-send refusal (ONLINE-5385). Teacher A = E2E_TEACHER_*.

const LONG_ASK = 'Write a detailed five-day unit plan on the water cycle with daily activities and an assessment.';

test.describe('Release 2 · Scout window (teacher)', () => {
    test.skip(!account('teacher'), missing('teacher'));

    test.beforeEach(async ({ context, request }) => {
        await installAuthToken(context, await tokenFor(request, 'teacher'));
    });

    async function openScout(page: Page): Promise<Scout> {
        const scout = new Scout(page);
        await page.goto('');
        await scout.appReady();
        await scout.open();
        return scout;
    }

    test('[ONLINE-8027] minimize, restore, maximize, close and reopen keep the window working', async ({ page }) => {
        const scout = await openScout(page);
        await shot(page, 'ONLINE-8027', '01-window-open');
        await page.getByRole('button', { name: 'Minimize assistant' }).click();
        await expect(scout.input).toBeHidden();
        await page.getByRole('button', { name: 'Restore Scout' }).first().click();
        await expect(scout.input).toBeVisible();
        await page.getByRole('button', { name: /Maximize assistant|Restore assistant size/ }).click();
        await expect(page.getByRole('button', { name: 'Restore assistant size' })).toBeVisible();
        await shot(page, 'ONLINE-8027', '02-window-maximized');
        await page.getByRole('button', { name: 'Restore assistant size' }).click();
        await page.getByRole('button', { name: 'Close assistant and clear this conversation' }).click();
        await expect(scout.input).toBeHidden();
        await scout.open();
        await expect(scout.input).toBeVisible();
    });

    test('[ONLINE-8027] composer: Shift+Enter adds a line, Enter sends, Send turns into Stop; footer actions show', async ({ page }) => {
        const scout = await openScout(page);
        await scout.newChat();
        let turns = 0;
        page.on('request', (r) => { if (r.url().includes('/assistant/v2/turn') && !r.url().includes('cancel')) turns += 1; });
        await scout.input.click();
        await scout.input.pressSequentially('First line');
        await scout.input.press('Shift+Enter');
        await scout.input.pressSequentially('Second line: what is a map key? One sentence.');
        expect(await scout.input.inputValue()).toContain('\n');
        expect(turns).toBe(0);
        const turn = page.waitForResponse((r) => r.url().includes('/assistant/v2/turn') && r.request().method() === 'POST');
        await scout.input.press('Enter');
        await expect(scout.stop).toBeVisible({ timeout: 15_000 });
        await shot(page, 'ONLINE-8027', '03-send-became-stop');
        expect((await turn).status()).toBe(200);
        await expect(scout.stop).toBeHidden({ timeout: 150_000 });
        await expect(scout.send).toBeVisible();
        const reply = scout.lastReply();
        await expect(reply.getByRole('button', { name: 'Good response' }).or(page.getByRole('button', { name: 'Good response' }).last())).toBeVisible();
        await expect(page.getByRole('button', { name: /^(Copy|Copied)$/ }).last()).toBeVisible();
        await shot(page, 'ONLINE-8027', '04-reply-footer');
        expect(turns).toBe(1);
    });

    test('[ONLINE-8027] chat sidebar: search, rename, pin and delete a chat', async ({ page }) => {
        const scout = await openScout(page);
        await scout.newChat();
        // Rename only after the chat's title request answers: before it, the row still holds a placeholder id and the
        // rename fails (a pre-existing race, recorded separately in the report).
        const titled = page.waitForResponse((r) => /\/assistant\/thread(\?|$)/.test(r.url()) && r.request().method() === 'POST', { timeout: 150_000 });
        await scout.ask('Name one ocean in one word.');
        await titled;
        await scout.showConversations();
        const row = page.locator('.history-item.active-chat');
        await expect(row).toBeVisible({ timeout: 30_000 });
        const name = `QA rename ${Date.now() % 100000}`;

        await row.hover();
        await row.getByRole('button', { name: /^Options for / }).click();
        await page.getByText('Rename', { exact: true }).click();
        await page.keyboard.press('ControlOrMeta+A');
        await page.keyboard.type(name);
        await page.keyboard.press('Enter');
        await expect(page.locator('.history-item').filter({ hasText: name })).toBeVisible();

        const renamed = page.locator('.history-item').filter({ hasText: name });
        await renamed.hover();
        await renamed.getByRole('button', { name: /^Options for / }).click();
        await page.getByText('Pin', { exact: true }).click();
        await shot(page, 'ONLINE-8027', '05-sidebar-renamed-pinned');

        await page.getByRole('button', { name: 'Search your chats' }).first().click();
        await page.getByLabel('Search your chats').last().fill('QA rename');
        await expect(page.getByRole('listbox').getByRole('option').filter({ hasText: name })).toBeVisible();
        await shot(page, 'ONLINE-8027', '06-sidebar-search');
        await page.keyboard.press('Escape');

        await renamed.hover();
        await renamed.getByRole('button', { name: /^Options for / }).click();
        await page.getByText('Delete', { exact: true }).click();
        const confirm = page.getByRole('button', { name: /^Delete$/ }).last();
        if (await confirm.isVisible().catch(() => false)) await confirm.click();
        await expect(page.locator('.history-item').filter({ hasText: name })).toHaveCount(0, { timeout: 20_000 });
    });

    test('[ONLINE-8027] What Scout Can Do and Tours open', async ({ page }) => {
        await openScout(page);
        await page.getByText('What Scout Can Do').first().click();
        const drawer = page.locator('[aria-label="What Scout can do"]');
        await expect(drawer).toBeVisible();
        await shot(page, 'ONLINE-8027', '07-what-scout-can-do');
        await expect(drawer.getByText(/Tours?/).first()).toBeVisible();
    });

    test('[ONLINE-8027] editing an earlier question and resending replaces the answer', async ({ page }) => {
        const scout = await openScout(page);
        await scout.newChat();
        await scout.ask('Name one primary color. One word.');
        const human = page.locator('.chat-row--human').last();
        await human.hover();
        await page.getByRole('button', { name: 'Edit' }).last().click();
        const editor = page.locator('.edit-actions').last().locator('xpath=ancestor::*[contains(@class,"v-input")][1]').locator('textarea').first();
        await editor.fill('Name one secondary color. One word.');
        const resend = page.waitForResponse((r) => r.url().includes('/assistant/v2/turn') && r.request().method() === 'POST', { timeout: 60_000 });
        await page.locator('.edit-actions button').last().click();
        expect((await resend).status()).toBe(200);
        await expect(scout.stop).toBeHidden({ timeout: 150_000 });
        await expect(page.locator('.chat-row--human').last()).toContainText('secondary color');
        await shot(page, 'ONLINE-8027', '08-edited-and-resent');
    });

    test('[ONLINE-8051] New Chat while answering cancels the turn and the new chat works', async ({ page }) => {
        const scout = await openScout(page);
        await scout.newChat();
        const cancel = page.waitForRequest((r) => r.url().includes('/assistant/v2/turn/cancel'), { timeout: 30_000 });
        await scout.start(LONG_ASK);
        await expect(scout.stop).toBeVisible();
        await page.getByRole('button', { name: 'New Chat' }).first().click();
        const sent = await cancel;
        expect(sent.postDataJSON()?.turn_id).toBeTruthy();
        expect((await sent.response())?.status()).toBe(200);
        const turn = await scout.ask('Name one continent. One word.');
        expect(turn.status()).toBe(200);
        await expect(page.locator('.chat-row--human')).toHaveCount(1);
        await shot(page, 'ONLINE-8051', '01-new-chat-after-cancel');
    });

    test('[ONLINE-8051] switching to another chat while answering cancels; no reply lands in the wrong chat', async ({ page }) => {
        const scout = await openScout(page);
        await scout.showConversations();
        const rows = page.locator('.history-item');
        await expect(rows.nth(1)).toBeVisible({ timeout: 30_000 });
        await scout.newChat();
        const marker = `Q${Date.now() % 100000}`;
        const cancel = page.waitForRequest((r) => r.url().includes('/assistant/v2/turn/cancel'), { timeout: 30_000 });
        await scout.start(`${LONG_ASK} Label it ${marker}.`);
        await rows.nth(1).getByRole('button').first().click();
        expect((await (await cancel).response())?.status()).toBe(200);
        await page.waitForTimeout(8_000);
        await expect(page.locator('.chat-row--human').filter({ hasText: marker })).toHaveCount(0);
        await expect(scout.stop).toBeHidden();
        await shot(page, 'ONLINE-8051', '02-switched-chat-clean');
    });

    test('[ONLINE-5385] a second send in the same chat while one is answering shows the still-answering sentence', async ({ page, context }) => {
        const scout = await openScout(page);
        await scout.newChat();
        await scout.ask('Name one planet. One word.');
        const threadRow = page.locator('.history-item.active-chat');
        await expect(threadRow).toBeVisible({ timeout: 30_000 });
        const threadId = await threadRow.getAttribute('data-thread-id');

        const second = await context.newPage();
        const scout2 = new Scout(second);
        await second.goto('');
        await scout2.appReady();
        await scout2.open();
        await scout2.showConversations();
        await second.locator(`[data-thread-id="${threadId}"]`).getByRole('button').first().click();
        await expect(second.locator('.chat-row--human').first()).toBeVisible({ timeout: 30_000 });

        await scout.start(LONG_ASK);
        await scout2.start('And name one more planet.');
        await expect(second.getByText(/Scout is still answering/i).first()).toBeVisible({ timeout: 60_000 });
        await shot(second, 'ONLINE-5385', '01-second-tab-still-answering');
        await expect(second.getByText(/Didn.t Finish|Ask Again/)).toHaveCount(0);
        await expect(scout.stop).toBeHidden({ timeout: 180_000 });
        await shot(page, 'ONLINE-5385', '02-first-tab-answer-kept');
    });
});
