import { expect, type APIRequestContext, type BrowserContext } from '@playwright/test';
import { API_URL, APP_URL, account, missing, type Role } from './env';

const tokens = new Map<Role, string>();

// Sign in through the API, the way swo-3.0/e2e does (POST auth/login, then the token in localStorage).
// ⚠️ The API enforces one active session per user: this signs the same account out of any browser using it.
export async function tokenFor(request: APIRequestContext, role: Role): Promise<string> {
    const cached = tokens.get(role);
    if (cached) return cached;
    const creds = account(role);
    if (!creds) throw new Error(missing(role));
    const response = await request.post(`${API_URL}auth/login`, { data: creds });
    expect(response.status(), `auth/login for ${role}: ${(await response.text()).slice(0, 200)}`).toBe(200);
    const { access_token: token } = (await response.json()) as { access_token: string };
    tokens.set(role, token);
    return token;
}

export async function installAuthToken(context: BrowserContext, token: string): Promise<void> {
    await context.addInitScript(({ origin, value }) => {
        if (location.origin === origin) {
            localStorage.setItem('auth._token.local', `Bearer ${value}`);
        }
    }, { origin: new URL(APP_URL).origin, value: token });
}
