import { describe, it, expect, vi } from 'vitest';
import { redirect } from 'next/navigation';
import LeaderboardPage from '../page';

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}));

describe('LeaderboardPage', () => {
  it('redirects to /leagues', () => {
    LeaderboardPage();
    expect(redirect).toHaveBeenCalledWith('/leagues');
  });
});
