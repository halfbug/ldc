import { mkdirSync } from 'node:fs';
import { test, type Page } from '@playwright/test';

// A named screenshot for the test report: results/screens/<case>-<label>.png, also attached to the HTML report.
export async function snap(page: Page, label: string): Promise<void> {
    const info = test.info();
    const name = `${info.title.match(/#\d+/)?.[0]?.slice(1).padStart(2, '0') ?? 'xx'}-${label}`.replace(/[^\w-]+/g, '-');
    mkdirSync('results/screens', { recursive: true });
    const path = `results/screens/${name}.png`;
    await page.screenshot({ path });
    await info.attach(label, { path, contentType: 'image/png' });
}
