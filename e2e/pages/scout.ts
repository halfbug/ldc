import { expect, type Locator, type Page, type Response } from '@playwright/test';

// Scout's window. Labels come from frontend-v3 (NavbarAiButton.vue, AiComposer.vue, ai/context/assistantPanel.ts).
export class Scout {
    readonly dialog: Locator;
    readonly input: Locator;
    readonly send: Locator;
    readonly stop: Locator;

    constructor(private readonly page: Page) {
        this.dialog = page.getByRole('dialog', { name: 'Scout (AI Assistant)' });
        this.input = page.getByLabel('Message the assistant');
        this.send = page.getByRole('button', { name: 'Send message' });
        this.stop = page.getByRole('button', { name: 'Stop generating' });
    }

    async appReady(): Promise<void> {
        await this.page.waitForFunction(() => {
            const app = (document.querySelector('#__nuxt') as { __vue_app__?: { $nuxt?: { isHydrating?: boolean } } } | null)?.__vue_app__;
            return app?.$nuxt?.isHydrating === false;
        }, undefined, { timeout: 60_000 });
    }

    async open(): Promise<void> {
        await this.page.getByRole('button', { name: /^(Scout \(AI Assistant\)|Restore Scout)$/ }).first().click();
        await expect(this.input).toBeVisible({ timeout: 30_000 });
        await this.dismissTour();
    }

    // "Meet Scout, your teaching assistant" opens on an account's first visit and covers the window.
    async dismissTour(): Promise<void> {
        const later = this.page.getByRole('button', { name: 'Maybe Later' });
        await later.waitFor({ state: 'visible', timeout: 5_000 }).catch(() => undefined);
        if (await later.isVisible()) await later.click();
    }

    async newChat(): Promise<void> {
        const button = this.page.getByRole('button', { name: 'New Chat' }).first();
        if (await button.isVisible()) await button.click();
    }

    async showConversations(): Promise<void> {
        const show = this.page.getByRole('button', { name: 'Show conversations' }).first();
        if (await show.isVisible()) await show.click();
    }

    // Sends `text` and resolves with the turn's response (teacher or admin door), once the reply has finished.
    async ask(text: string, door: 'v2/turn' | 'v2/admin/turn' = 'v2/turn'): Promise<Response> {
        const turn = this.page.waitForResponse((r) => r.url().includes(`/assistant/${door}`) && r.request().method() === 'POST', { timeout: 120_000 });
        await this.input.fill(text);
        await this.send.click();
        const response = await turn;
        // Not response.finished(): Playwright doesn't reliably settle it for a streamed (SSE) body. The turn is over
        // when the composer's Stop button goes away.
        await expect(this.stop).toBeVisible({ timeout: 10_000 }).catch(() => undefined);
        await expect(this.stop).toBeHidden({ timeout: 150_000 });
        return response;
    }

    // Starts a turn without waiting for it to finish (for Stop, New Chat and switching mid-answer).
    async start(text: string, door: 'v2/turn' | 'v2/admin/turn' = 'v2/turn'): Promise<void> {
        const turn = this.page.waitForResponse((r) => r.url().includes(`/assistant/${door}`) && r.request().method() === 'POST', { timeout: 60_000 });
        await this.input.fill(text);
        await this.send.click();
        await turn;
    }

    replies(): Locator {
        return this.page.locator('.chat-row--ai');
    }

    lastReply(): Locator {
        return this.page.locator('.chat-row--ai').last();
    }

    sidebarRow(threadId: string): Locator {
        return this.page.locator(`[data-thread-id="${threadId}"]`);
    }
}
