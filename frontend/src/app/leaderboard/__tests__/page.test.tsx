import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import LeaderboardPage from '../page';
import { getMyLeagues, getLeaderboard } from '@/lib/api';
import { mockLeagues, mockLeaderboardResponse } from '@/__tests__/helpers/test-data';

vi.mock('@/lib/api', () => ({
  getMyLeagues: vi.fn(),
  getLeaderboard: vi.fn(),
}));

const mockUseAuth = vi.fn();

vi.mock('@/lib/auth', () => ({
  useAuth: (...args: unknown[]) => mockUseAuth(...args),
}));

describe('LeaderboardPage', () => {
  const mockPush = vi.fn();
  const mockGetMyLeagues = vi.mocked(getMyLeagues);
  const mockGetLeaderboard = vi.mocked(getLeaderboard);

  beforeEach(() => {
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    });
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      username: 'testuser',
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });
  });

  it('redirects to login when unauthenticated', async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      username: null,
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });

    render(<LeaderboardPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('shows empty state when no leagues', async () => {
    mockGetMyLeagues.mockResolvedValue([]);

    render(<LeaderboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Join a league to see leaderboards')).toBeInTheDocument();
    });
  });

  it('loads first league and fetches leaderboard', async () => {
    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    render(<LeaderboardPage />);

    await waitFor(() => {
      expect(mockGetLeaderboard).toHaveBeenCalledWith(10);
    });
  });

  it('renders leaderboard entries with usernames and points', async () => {
    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    render(<LeaderboardPage />);

    await waitFor(() => {
      // Use getAllByText since names appear in both podium and table
      expect(screen.getAllByText('alice').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText('bob').length).toBeGreaterThan(0);
    expect(screen.getAllByText('150').length).toBeGreaterThan(0);
    expect(screen.getAllByText('120').length).toBeGreaterThan(0);
  });

  it('highlights current user with "You" badge', async () => {
    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    render(<LeaderboardPage />);

    await waitFor(() => {
      // "You" appears both in the current user card and as a badge in the table
      expect(screen.getAllByText('You').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders top 3 podium', async () => {
    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    render(<LeaderboardPage />);

    await waitFor(() => {
      // Podium shows all three top usernames
      expect(screen.getAllByText('alice').length).toBeGreaterThan(0);
      expect(screen.getAllByText('bob').length).toBeGreaterThan(0);
      expect(screen.getAllByText('testuser').length).toBeGreaterThan(0);
    });
  });

  it('shows empty entries state', async () => {
    mockGetMyLeagues.mockResolvedValue(mockLeagues);
    mockGetLeaderboard.mockResolvedValue({
      league_id: 10,
      league_name: 'Test League',
      entries: [],
    });

    render(<LeaderboardPage />);

    await waitFor(() => {
      expect(screen.getByText('No entries yet. Start predicting!')).toBeInTheDocument();
    });
  });
});
