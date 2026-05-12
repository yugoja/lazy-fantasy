import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DugoutFeed } from '../DugoutFeed';
import type { DugoutEvent } from '@/lib/api';
import { mockVerdictSolo, mockVerdictTwoWayTie } from '@/__tests__/helpers/test-data';

// Mock the MatchVerdictCard to isolate DugoutFeed logic
vi.mock('@/components/MatchVerdictCard', () => ({
  MatchVerdictCard: ({ event }: { event: DugoutEvent }) => (
    <div data-testid="match-verdict-card">{event.match_label}</div>
  ),
}));

// Mock api module for dismissDugoutEvent
vi.mock('@/lib/api', () => ({
  dismissDugoutEvent: vi.fn(),
}));

// Mock auth hook to provide currentUsername
vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    username: 'viewer',
    isLoading: false,
  }),
}));

describe('DugoutFeed — match_verdict rendering', () => {
  it('renders MatchVerdictCard for verdict events', () => {
    render(<DugoutFeed events={[mockVerdictSolo]} />);
    expect(screen.getByTestId('match-verdict-card')).toBeInTheDocument();
    expect(screen.getByText('M24')).toBeInTheDocument();
  });

  it('renders multiple verdict cards', () => {
    render(<DugoutFeed events={[mockVerdictSolo, mockVerdictTwoWayTie]} />);
    expect(screen.getAllByTestId('match-verdict-card')).toHaveLength(2);
  });

  it('renders verdict cards alongside other event types', () => {
    const contrarian: DugoutEvent = {
      type: 'contrarian',
      league_name: 'Test',
      league_id: 1,
      match_id: 10,
      username: 'bob',
      display_name: 'Bob',
      is_me: false,
      streak_count: null,
      rank: null,
      rank_delta: null,
      agreement_count: null,
      team_short_name: 'IND',
    };

    render(<DugoutFeed events={[mockVerdictSolo, contrarian]} />);

    expect(screen.getByTestId('match-verdict-card')).toBeInTheDocument();
    // Contrarian card should also render
    expect(screen.getByText(/lone wolf/i)).toBeInTheDocument();
  });

  it('does not render verdict cards when there are none', () => {
    const rankShift: DugoutEvent = {
      type: 'rank_shift',
      league_name: 'Test',
      league_id: 1,
      match_id: null,
      username: 'viewer',
      display_name: null,
      is_me: true,
      streak_count: null,
      rank: 2,
      rank_delta: 1,
      agreement_count: null,
      team_short_name: null,
    };

    render(<DugoutFeed events={[rankShift]} />);
    expect(screen.queryByTestId('match-verdict-card')).not.toBeInTheDocument();
  });
});
