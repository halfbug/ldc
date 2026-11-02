// Every value comes from the environment (see .env.example); nothing secret is stored here.

export const APP_URL = (process.env.E2E_APP_URL ?? 'https://dev2-online.studiesweekly.com/beta').replace(/\/$/, '');
// Trailing slash: paths below are relative to it.
export const API_URL = `${(process.env.E2E_API_URL ?? 'https://dev2-online-api.studiesweekly.com/api').replace(/\/$/, '')}/`;
// The Studies Weekly host rag scopes the user with (?host=…).
export const AI_HOST = process.env.E2E_AI_HOST ?? new URL(APP_URL).host;

// rag doors, copied from the Network tab of a signed-in session (they change per deploy):
// E2E_GW_URL   API Gateway base ending in /v3, e.g. https://<api-id>.execute-api.us-west-2.amazonaws.com/dev/v3
// E2E_CORE_URL Lambda Function URL root, e.g. https://<id>.lambda-url.us-west-2.on.aws
export const GW_URL = process.env.E2E_GW_URL?.replace(/\/$/, '');
export const CORE_URL = process.env.E2E_CORE_URL?.replace(/\/$/, '');

// Tests that send a real Scout turn spend the account's credits; they run only when asked for.
export const AI_TURNS = process.env.E2E_AI_TURNS === '1';

export type Role = 'teacher' | 'districtAdmin' | 'schoolAdmin' | 'noFlagTeacher';
export type Account = { username: string; password: string };

const PREFIX: Record<Role, string> = {
    teacher: 'E2E_TEACHER',
    districtAdmin: 'E2E_DISTRICT_ADMIN',
    schoolAdmin: 'E2E_SCHOOL_ADMIN',
    noFlagTeacher: 'E2E_NOFLAG_TEACHER',
};

export function account(role: Role): Account | null {
    const username = process.env[`${PREFIX[role]}_USERNAME`];
    const password = process.env[`${PREFIX[role]}_PASSWORD`];
    return username && password ? { username, password } : null;
}

export function missing(role: Role): string {
    return `set ${PREFIX[role]}_USERNAME and ${PREFIX[role]}_PASSWORD`;
}

// Optional inputs for the UI cases that need a specific page or thread.
export const HISTORY_ARTICLE_PATH = process.env.E2E_HISTORY_ARTICLE_PATH; // a /beta path of a history article
export const LEGACY_THREAD_TITLE = process.env.E2E_LEGACY_THREAD_TITLE;   // a chat from before the release
export const SEARCH_TERM = process.env.E2E_SEARCH_TERM;                   // a word in an old chat's title
export const CHIP_LABEL = process.env.E2E_CHIP_LABEL;                     // an action chip's button text
export const CHIP_PAGE_PATH = process.env.E2E_CHIP_PAGE_PATH ?? '';       // the /beta path where that chip shows
