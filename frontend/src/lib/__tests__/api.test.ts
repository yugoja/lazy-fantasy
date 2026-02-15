import { describe, it, expect, vi, beforeEach } from 'vitest';
import { login, signup, ApiError, getMyLeagues } from '../api';

const API_BASE = 'http://localhost:8000';

function mockFetchResponse(status: number, body: unknown, ok?: boolean) {
  return vi.fn().mockResolvedValue({
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: vi.fn().mockResolvedValue(body),
  });
}

describe('login()', () => {
  it('sends form-urlencoded content type', async () => {
    const fetchSpy = mockFetchResponse(200, { access_token: 'tok', token_type: 'bearer' });
    global.fetch = fetchSpy;

    await login('user1', 'pass1');

    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE}/auth/login`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      }),
    );
    const body = fetchSpy.mock.calls[0][1].body as URLSearchParams;
    expect(body.get('username')).toBe('user1');
    expect(body.get('password')).toBe('pass1');
  });

  it('throws ApiError on failure', async () => {
    global.fetch = mockFetchResponse(401, { detail: 'Invalid credentials' }, false);

    await expect(login('bad', 'creds')).rejects.toThrow(ApiError);
    try {
      await login('bad', 'creds');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as InstanceType<typeof ApiError>).status).toBe(401);
      expect((err as InstanceType<typeof ApiError>).message).toBe('Invalid credentials');
    }
  });
});

describe('signup()', () => {
  it('sends JSON body with correct content-type', async () => {
    const fetchSpy = mockFetchResponse(200, { id: 1, username: 'user1', email: 'a@b.com' });
    global.fetch = fetchSpy;
    localStorage.removeItem('token');

    await signup('user1', 'a@b.com', 'password123');

    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE}/auth/signup`,
      expect.objectContaining({
        method: 'POST',
      }),
    );
    const headers = fetchSpy.mock.calls[0][1].headers;
    expect(headers['Content-Type']).toBe('application/json');
    const body = JSON.parse(fetchSpy.mock.calls[0][1].body);
    expect(body).toEqual({ username: 'user1', email: 'a@b.com', password: 'password123' });
  });
});

describe('request() — via getMyLeagues()', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('attaches Bearer token when present', async () => {
    const fetchSpy = mockFetchResponse(200, []);
    global.fetch = fetchSpy;
    localStorage.setItem('token', 'my-jwt-token');

    await getMyLeagues();

    const headers = fetchSpy.mock.calls[0][1].headers;
    expect(headers['Authorization']).toBe('Bearer my-jwt-token');
  });

  it('skips auth header when no token', async () => {
    const fetchSpy = mockFetchResponse(200, []);
    global.fetch = fetchSpy;

    await getMyLeagues();

    const headers = fetchSpy.mock.calls[0][1].headers;
    expect(headers['Authorization']).toBeUndefined();
  });

  it('clears localStorage and redirects on 401', async () => {
    global.fetch = mockFetchResponse(401, { detail: 'Unauthorized' }, false);
    localStorage.setItem('token', 'expired-token');
    localStorage.setItem('username', 'testuser');

    // Mock window.location
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...originalLocation, href: '' },
    });

    // Call the function — it returns a never-resolving promise
    const promise = getMyLeagues();

    // Wait a tick for the async fetch to resolve and the 401 handler to run
    await new Promise((r) => setTimeout(r, 50));

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('username')).toBeNull();
    expect(window.location.href).toBe('/login');

    // Verify the promise never settles
    let settled = false;
    promise.then(
      () => { settled = true; },
      () => { settled = true; },
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(settled).toBe(false);

    // Restore
    Object.defineProperty(window, 'location', { writable: true, value: originalLocation });
  });

  it('throws ApiError on non-401 error', async () => {
    global.fetch = mockFetchResponse(500, { detail: 'Server error' }, false);

    await expect(getMyLeagues()).rejects.toThrow(ApiError);
    try {
      await getMyLeagues();
    } catch (err) {
      expect((err as InstanceType<typeof ApiError>).status).toBe(500);
      expect((err as InstanceType<typeof ApiError>).message).toBe('Server error');
    }
  });
});
