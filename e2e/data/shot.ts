import { mkdirSync } from 'node:fs';
import { test, type Page } from '@playwright/test';

// A screenshot named by ticket for the release report: results/screens/release2/<ticket>-<label>.png,
// also attached to the HTML report.
export async function shot(page: Page, ticket: string, label: string): Promise<void> {
    const dir = 'results/screens/release2';
    mkdirSync(dir, { recursive: true });
    const path = `${dir}/${ticket}-${label}.png`.replace(/[^\w./-]+/g, '-');
    await page.screenshot({ path });
    await test.info().attach(`${ticket} ${label}`, { path, contentType: 'image/png' });
}
