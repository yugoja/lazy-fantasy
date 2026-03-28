import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter, useSearchParams } from 'next/navigation';
import LeaguesPage from '../page';
import { getMyLeagues, getLeaderboard, joinLeague, createLeague, ApiError } from '@/lib/api';
import { mockLeagues, mockLeaderboardResponse } from '@/__tests__/helpers/test-data';

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  }
  return {
    getMyLeagues: vi.fn(),
    getLeaderboard: vi.fn(),
    joinLeague: vi.fn(),
    createLeague: vi.fn(),
    ApiError,
  };
});

const mockUseAuth = vi.fn();
vi.mock('@/lib/auth', () => ({
  useAuth: (...args: unknown[]) => mockUseAuth(...args),
}));

// testuser is rank 3 with delta -1 in mockLeaderboardResponse (league 10)
// For league 20: testuser is rank 1, delta +2
const mockLeaderboardLeague20 = {
  league_id: 20,
  league_name: 'Another League',
  entries: [
    { user_id: 3, username: 'testuser', total_points: 200, rank: 1, rank_delta: 2 },
    { user_id: 2, username: 'bob', total_points: 180, rank: 2, rank_delta: null },
  ],
};

describe('LeaguesPage', () => {
  const mockPush = vi.fn();
  const mockGetMyLeagues = vi.mocked(getMyLeagues);
  const mockGetLeaderboard = vi.mocked(getLeaderboard);
  const mockJoinLeague = vi.mocked(joinLeague);
  const mockCreateLeague = vi.mocked(createLeague);

  beforeEach(() => {
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    });
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as ReturnType<typeof useSearchParams>);

    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      username: 'testuser',
      isLoading: false,
    });

    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockImplementation(async (id: number) => {
      if (id === 10) return mockLeaderboardResponse;
      if (id === 20) return mockLeaderboardLeague20;
      throw new Error('Unknown league');
    });

    // stub clipboard (read-only property requires defineProperty)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn() },
      writable: true,
      configurable: true,
    });
  });

  it('redirects to /login when not authenticated', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, username: null, isLoading: false });
    mockGetMyLeagues.mockResolvedValue([]);

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('shows empty state when user has no leagues', async () => {
    mockGetMyLeagues.mockResolvedValue([]);

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText(/haven't joined any leagues/i)).toBeInTheDocument();
    });
  });

  it('shows error when leagues fail to load', async () => {
    mockGetMyLeagues.mockRejectedValue(new Error('network error'));

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load leagues/i)).toBeInTheDocument();
    });
  });

  it('renders a card for each league linking to /leagues/[id]', async () => {
    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText('Test League')).toBeInTheDocument();
      expect(screen.getByText('Another League')).toBeInTheDocument();
    });

    const links = screen.getAllByRole('link');
    const hrefs = links.map(l => l.getAttribute('href'));
    expect(hrefs).toContain('/leagues/10');
    expect(hrefs).toContain('/leagues/20');
  });

  it('shows member count and points from leaderboard', async () => {
    render(<LeaguesPage />);

    // league 10: 4 members, testuser has 100 pts
    await waitFor(() => {
      expect(screen.getByText(/4 members · 100 pts/i)).toBeInTheDocument();
    });
    // league 20: 2 members, testuser has 200 pts
    expect(screen.getByText(/2 members · 200 pts/i)).toBeInTheDocument();
  });

  it("shows the current user's rank on each card", async () => {
    render(<LeaguesPage />);

    // testuser: rank 3 in league 10, rank 1 in league 20
    await waitFor(() => {
      expect(screen.getByText('#3')).toBeInTheDocument();
      expect(screen.getByText('#1')).toBeInTheDocument();
    });
  });

  it('shows a positive rank delta indicator', async () => {
    // league 20: testuser rank_delta = +2
    render(<LeaguesPage />);

    await waitFor(() => {
      // TrendingUp icon has no text; check for the delta value
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    // The delta 2 should be green (positive)
    const deltaEl = screen.getByText('2').closest('div');
    expect(deltaEl?.className).toMatch(/green/);
  });

  it('shows a negative rank delta indicator', async () => {
    // league 10: testuser rank_delta = -1
    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    const deltaEl = screen.getByText('1').closest('div');
    expect(deltaEl?.className).toMatch(/red/);
  });

  it('shows — for rank when leaderboard fetch fails', async () => {
    // Only league 10 is returned, and leaderboard fails for it
    mockGetMyLeagues.mockResolvedValue([mockLeagues[0]]); // just league 10
    mockGetLeaderboard.mockRejectedValue(new Error('fail'));

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText('Test League')).toBeInTheDocument();
      expect(screen.getByText('—')).toBeInTheDocument();
    });
  });

  it('still shows rank for successful leagues when one leaderboard fetch fails', async () => {
    // league 10 fails, league 20 succeeds
    mockGetLeaderboard.mockImplementation(async (id: number) => {
      if (id === 10) throw new Error('fail');
      return mockLeaderboardLeague20;
    });

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument(); // league 20 rank
      expect(screen.getByText('—')).toBeInTheDocument();  // league 10 failed
    });
  });

  it('opens join dialog and calls joinLeague on submit', async () => {
    const user = userEvent.setup();
    const newLeague = { id: 30, name: 'New League', invite_code: 'XYZ999', owner_id: 1, sport: 'cricket' };
    mockJoinLeague.mockResolvedValue(newLeague);

    render(<LeaguesPage />);
    await waitFor(() => screen.getByText('Test League'));

    await user.click(screen.getByRole('button', { name: /join/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await user.type(screen.getByLabelText(/league code/i), 'XYZ999');
    await user.click(screen.getByRole('button', { name: /join league/i }));

    await waitFor(() => {
      expect(mockJoinLeague).toHaveBeenCalledWith('XYZ999');
      expect(screen.getByText('New League')).toBeInTheDocument();
    });
  });

  it('shows error in join dialog on API failure', async () => {
    const user = userEvent.setup();
    mockJoinLeague.mockRejectedValue(new ApiError(400, 'Invalid code'));

    render(<LeaguesPage />);
    await waitFor(() => screen.getByText('Test League'));

    await user.click(screen.getByRole('button', { name: /join/i }));
    await user.type(screen.getByLabelText(/league code/i), 'BAD');
    await user.click(screen.getByRole('button', { name: /join league/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid code')).toBeInTheDocument();
    });
  });

  it('opens create dialog, submits, and shows invite code in confirmation', async () => {
    const user = userEvent.setup();
    const created = { id: 99, name: 'My Squad', invite_code: 'MYS-2026-QQ1', owner_id: 3, sport: 'cricket' };
    mockCreateLeague.mockResolvedValue(created);

    render(<LeaguesPage />);
    await waitFor(() => screen.getByText('Test League'));

    await user.click(screen.getByRole('button', { name: /^create$/i }));
    await user.type(screen.getByLabelText(/league name/i), 'My Squad');
    await user.click(screen.getByRole('button', { name: /create league/i }));

    await waitFor(() => {
      expect(mockCreateLeague).toHaveBeenCalledWith('My Squad', 'cricket');
      expect(screen.getByText('MYS-2026-QQ1')).toBeInTheDocument();
    });
  });

  it('pre-fills join code and opens dialog when ?join=CODE is in URL', async () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams('join=FRIEND123') as ReturnType<typeof useSearchParams>
    );
    mockGetMyLeagues.mockResolvedValue([]);

    render(<LeaguesPage />);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByDisplayValue('FRIEND123')).toBeInTheDocument();
    });
  });
});
