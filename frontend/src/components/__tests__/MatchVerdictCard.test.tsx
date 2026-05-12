import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MatchVerdictCard } from '../MatchVerdictCard';
import {
  mockVerdictSolo,
  mockVerdictYouWon,
  mockVerdictCold,
  mockVerdictTwoWayTie,
  mockVerdictThreeWayTie,
  mockVerdictTightMargin,
} from '@/__tests__/helpers/test-data';

// Mock share utility — shareVerdict is what the component calls
vi.mock('@/lib/share', () => ({
  shareVerdict: vi.fn(),
  shareWithCard: vi.fn(),
}));

describe('MatchVerdictCard', () => {
  // ---------- Solo winner ----------
  it('renders solo-winner headline with the winner name', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    // Solo flawless: "Alice ran the table." — Alice appears in avatar + panel + headline
    expect(screen.getAllByText(/alice/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/ran the table/i)).toBeInTheDocument();
  });

  it('renders the 4-cell hits grid for solo winner', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    expect(screen.getByText('Winner')).toBeInTheDocument();
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('Wkts')).toBeInTheDocument();
    expect(screen.getByText('POM')).toBeInTheDocument();
  });

  it('renders runner-up rows', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    // Runner-up: Bob with 30 pts
    expect(screen.getByText(/bob/i)).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('renders league name and match label in kicker', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    expect(screen.getByText(/Office Squad/)).toBeInTheDocument();
    expect(screen.getByText(/M24/)).toBeInTheDocument();
  });

  it('renders POM player name', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    expect(screen.getByText(/Virat Kohli/)).toBeInTheDocument();
  });

  it('renders winning and losing team short names', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    expect(screen.getByText('IND')).toBeInTheDocument();
    expect(screen.getByText('AUS')).toBeInTheDocument();
  });

  // ---------- 2-way tie ----------
  it('renders 2-way tie panel when two winners', () => {
    render(<MatchVerdictCard event={mockVerdictTwoWayTie} currentUsername="viewer" />);
    // "Tie" appears in headline + badge
    expect(screen.getAllByText(/tie/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/alice/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/carol/i).length).toBeGreaterThanOrEqual(1);
  });

  // ---------- 3-way tie ----------
  it('renders 3-way tie with rank-shift pills (no hits grid)', () => {
    render(<MatchVerdictCard event={mockVerdictThreeWayTie} currentUsername="viewer" />);
    // The "tied" badge is unique to 3-way tie panel
    expect(screen.getByText('tied')).toBeInTheDocument();
    // "Joint top" appears in both panel header and sub copy — check at least one exists
    expect(screen.getAllByText(/joint top/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/alice/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/carol/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/dave/i).length).toBeGreaterThanOrEqual(1);
    // Should NOT show the 4-cell hits grid
    expect(screen.queryByText('Winner')).not.toBeInTheDocument();
  });

  // ---------- You-won variant ----------
  it('switches to "is-you" variant when viewer matches a winner', () => {
    render(<MatchVerdictCard event={mockVerdictYouWon} currentUsername="testuser" />);
    // You-won solo copy should show "Brag now" CTA (unique to this variant)
    expect(screen.getByText(/brag now/i)).toBeInTheDocument();
    // Headline includes "ran the table"
    expect(screen.getByText(/ran the table/i)).toBeInTheDocument();
  });

  // ---------- Cold variant ----------
  it('switches to "is-cold" variant when top_score <= 30', () => {
    render(<MatchVerdictCard event={mockVerdictCold} currentUsername="viewer" />);
    // Cold copy includes "wins it" or "Yes really"
    expect(screen.getByText(/yes really/i)).toBeInTheDocument();
    // CTA should say "Apologise in group"
    expect(screen.getByText(/apologise in group/i)).toBeInTheDocument();
  });

  // ---------- Tight margin ----------
  it('renders tight-margin headline when gap <= 5', () => {
    render(<MatchVerdictCard event={mockVerdictTightMargin} currentUsername="viewer" />);
    // "Alice, by 3."
    expect(screen.getByText(/by 3/i)).toBeInTheDocument();
    expect(screen.getByText(/photo finish/i)).toBeInTheDocument();
  });

  // ---------- Share CTA ----------
  it('calls shareVerdict on primary CTA click', async () => {
    const { shareVerdict } = await import('@/lib/share');
    const user = userEvent.setup();

    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);

    // The primary CTA text is "Drop in group →" for a default solo winner
    const cta = screen.getByText(/drop in group/i);
    await user.click(cta);

    expect(shareVerdict).toHaveBeenCalledWith(mockVerdictSolo);
  });

  // ---------- Dismiss ----------
  it('calls onDismiss when dismiss button is clicked', async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();

    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" onDismiss={onDismiss} />);

    const dismissBtn = screen.getByLabelText('Dismiss');
    await user.click(dismissBtn);

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  // ---------- Empty winners ----------
  it('returns null when winners array is empty', () => {
    const event = { ...mockVerdictSolo, winners: [] };
    const { container } = render(<MatchVerdictCard event={event} currentUsername="viewer" />);
    expect(container.innerHTML).toBe('');
  });

  // ---------- Table link ----------
  it('renders a Table link to the league match page', () => {
    render(<MatchVerdictCard event={mockVerdictSolo} currentUsername="viewer" />);
    const tableLink = screen.getByText('Table');
    expect(tableLink.closest('a')).toHaveAttribute('href', '/leagues/5/match/24');
  });
});
