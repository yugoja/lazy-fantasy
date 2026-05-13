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
    vi.clearAllMocks();

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

  it('shows current form for both teams on winner step', async () => {
    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('IND vs AUS')).toBeInTheDocument();
    });

    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Recent form')).toHaveLength(2);
    expect(screen.queryByText('Current form')).not.toBeInTheDocument();
    expect(screen.queryByText('3W 1L 1NR')).not.toBeInTheDocument();
    expect(screen.getAllByText('W').length).toBeGreaterThan(0);
    expect(screen.getAllByText('L').length).toBeGreaterThan(0);
  });

  it('jumps to the summary state when an existing prediction is found', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByText('Your Picks')).toBeInTheDocument();
    });

    expect(screen.getByText('All done — ready to lock in.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /update picks/i })).toBeInTheDocument();
  });

  it('shows success dialog after updating an existing prediction', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);
    mockSubmitPrediction.mockResolvedValue({
      id: 1,
      user_id: 1,
      match_id: 42,
      points_earned: 0,
      is_processed: false,
    });
    const user = userEvent.setup();

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /update picks/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /update picks/i }));

    await waitFor(() => {
      expect(screen.getByText('Picks Updated!')).toBeInTheDocument();
    });
  });

  it('shows API error on submit failure', async () => {
    mockGetMyPredictions.mockResolvedValue([mockExistingPrediction]);
    mockSubmitPrediction.mockRejectedValue(new ApiError(400, 'Match has started'));
    const user = userEvent.setup();

    render(<PredictPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /update picks/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /update picks/i }));

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

    expect(screen.getByText('Back')).toBeInTheDocument();
  });
});
