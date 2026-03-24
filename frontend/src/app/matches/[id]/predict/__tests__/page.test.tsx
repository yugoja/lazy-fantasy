import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter, useParams } from 'next/navigation';
import PredictPage from '../page';
import { getMatchPlayers, getMyPredictions, submitPrediction, ApiError } from '@/lib/api';
import { mockMatchPlayersResponse, mockExistingPrediction } from '@/__tests__/helpers/test-data';

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
    getMatchPlayers: vi.fn(),
    getMyPredictions: vi.fn(),
    submitPrediction: vi.fn(),
    ApiError,
  };
});

const mockUseAuth = vi.fn();

vi.mock('@/lib/auth', () => ({
  useAuth: (...args: unknown[]) => mockUseAuth(...args),
}));

describe('PredictPage', () => {
  const mockPush = vi.fn();
  const mockGetMatchPlayers = vi.mocked(getMatchPlayers);
  const mockGetMyPredictions = vi.mocked(getMyPredictions);
  const mockSubmitPrediction = vi.mocked(submitPrediction);

  beforeEach(() => {
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    });
    vi.mocked(useParams).mockReturnValue({ id: '42' });
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      username: 'testuser',
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });
    mockGetMatchPlayers.mockResolvedValue(mockMatchPlayersResponse);
    mockGetMyPredictions.mockResolvedValue([]);
  });

  it('redirects to login when unauthenticated', async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      username: null,
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });

    render(<PredictPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('loads and renders team names and players', async () => {
    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });
    // Players appear in multiple prediction sections
    expect(screen.getAllByText('Kohli').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Smith').length).toBeGreaterThan(0);
  });

  it('pre-fills from existing prediction and shows Update label', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });

    expect(screen.getByText(/All predictions made/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /update prediction/i })).toBeInTheDocument();
  });

  it('shows submit disabled until all 6 filled', async () => {
    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });

    expect(screen.getByText('0 of 6 predictions made')).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: /submit/i });
    expect(submitBtn).toBeDisabled();
  });

  it('shows success dialog after submit', async () => {
    mockSubmitPrediction.mockResolvedValue({
      id: 1, user_id: 1, match_id: 42, points_earned: 0, is_processed: false,
    });
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);
    const user = userEvent.setup();

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });

    // All picks already pre-filled via mockExistingPrediction
    const updateBtn = screen.getByRole('button', { name: /update prediction/i });
    await user.click(updateBtn);

    await waitFor(() => {
      expect(screen.getByText('Prediction Updated!')).toBeInTheDocument();
    });
  });

  it('shows "Prediction Updated!" dialog when editing', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);
    mockSubmitPrediction.mockResolvedValue({
      id: 99, user_id: 1, match_id: 42, points_earned: 0, is_processed: false,
    });
    const user = userEvent.setup();

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });

    const updateBtn = screen.getByRole('button', { name: /update prediction/i });
    await user.click(updateBtn);

    await waitFor(() => {
      expect(screen.getByText('Prediction Updated!')).toBeInTheDocument();
    });
  });

  it('shows API error on submit failure', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);
    mockSubmitPrediction.mockRejectedValue(new ApiError(400, 'Match has started'));
    const user = userEvent.setup();

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('India vs Australia')).toBeInTheDocument();
    });

    const updateBtn = screen.getByRole('button', { name: /update prediction/i });
    await user.click(updateBtn);

    await waitFor(() => {
      expect(screen.getByText('Match has started')).toBeInTheDocument();
    });
  });

  it('shows error state when match data fails to load', async () => {
    mockGetMatchPlayers.mockRejectedValue(new Error('Network error'));

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load match data')).toBeInTheDocument();
    });
    expect(screen.getByText('Back to Matches')).toBeInTheDocument();
  });
});
