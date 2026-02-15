import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MatchCard } from '../MatchCard';

const baseProps = {
  id: 42,
  team1: { name: 'India', short_name: 'IND' },
  team2: { name: 'Australia', short_name: 'AUS' },
  startTime: '2099-06-15T10:00:00Z',
  status: 'SCHEDULED' as const,
};

describe('MatchCard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2099-06-14T10:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders team short_names and "vs"', () => {
    render(<MatchCard {...baseProps} />);
    expect(screen.getByText('IND')).toBeInTheDocument();
    expect(screen.getByText('AUS')).toBeInTheDocument();
    expect(screen.getByText('vs')).toBeInTheDocument();
  });

  it('shows UPCOMING badge for SCHEDULED status', () => {
    render(<MatchCard {...baseProps} status="SCHEDULED" />);
    expect(screen.getByText('UPCOMING')).toBeInTheDocument();
  });

  it('shows UPCOMING badge for UPCOMING status', () => {
    render(<MatchCard {...baseProps} status="UPCOMING" />);
    expect(screen.getByText('UPCOMING')).toBeInTheDocument();
  });

  it('shows LIVE badge', () => {
    render(<MatchCard {...baseProps} status="LIVE" />);
    expect(screen.getByText('LIVE')).toBeInTheDocument();
  });

  it('shows COMPLETED badge', () => {
    render(<MatchCard {...baseProps} status="COMPLETED" />);
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
  });

  it('shows "Make Prediction" when hasPredicted=false', () => {
    render(<MatchCard {...baseProps} hasPredicted={false} />);
    const btn = screen.getByRole('button', { name: /Make Prediction/i });
    expect(btn).toBeInTheDocument();
    expect(btn.closest('a')).toHaveAttribute('href', '/matches/42/predict');
  });

  it('shows "Update Prediction" when hasPredicted=true', () => {
    render(<MatchCard {...baseProps} hasPredicted={true} />);
    const btn = screen.getByRole('button', { name: /Update Prediction/i });
    expect(btn).toBeInTheDocument();
  });

  it('shows "View Live" button for LIVE status', () => {
    render(<MatchCard {...baseProps} status="LIVE" />);
    const btn = screen.getByRole('button', { name: /View Live/i });
    expect(btn).toBeInTheDocument();
    expect(btn.closest('a')).toHaveAttribute('href', '/matches/42');
  });

  it('shows "View Results" button for COMPLETED status', () => {
    render(<MatchCard {...baseProps} status="COMPLETED" />);
    const btn = screen.getByRole('button', { name: /View Results/i });
    expect(btn).toBeInTheDocument();
    expect(btn.closest('a')).toHaveAttribute('href', '/matches/42');
  });

  it('renders venue when provided', () => {
    render(<MatchCard {...baseProps} venue="Melbourne Cricket Ground" />);
    expect(screen.getByText('Melbourne Cricket Ground')).toBeInTheDocument();
  });

  it('shows countdown pill for UPCOMING match', () => {
    render(<MatchCard {...baseProps} status="SCHEDULED" />);
    // 1 day away from the set system time
    expect(screen.getByText('1d 0h')).toBeInTheDocument();
  });
});
