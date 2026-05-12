import { describe, it, expect, vi, beforeEach } from 'vitest';
import { shareVerdict } from '../share';
import {
  mockVerdictSolo,
  mockVerdictYouWon,
  mockVerdictCold,
  mockVerdictTwoWayTie,
  mockVerdictThreeWayTie,
} from '@/__tests__/helpers/test-data';

// Stub navigator.share and clipboard
const mockShare = vi.fn();
const mockWriteText = vi.fn();

beforeEach(() => {
  Object.defineProperty(navigator, 'share', { value: mockShare, writable: true, configurable: true });
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: mockWriteText },
    writable: true,
    configurable: true,
  });
  mockShare.mockReset();
  mockWriteText.mockReset();
});

describe('shareVerdict', () => {
  it('calls navigator.share with solo-winner text', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictSolo);

    expect(mockShare).toHaveBeenCalledOnce();
    const call = mockShare.mock.calls[0][0];
    expect(call.text).toContain('Alice');
    expect(call.text).toContain('Office Squad');
  });

  it('builds you-won text for "is_me" variant', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictYouWon);

    const call = mockShare.mock.calls[0][0];
    // You-won message starts with "Just ran the table"
    expect(call.text).toMatch(/just ran the table/i);
    expect(call.text).toContain('Office Squad');
  });

  it('builds cold text when top_score <= 30', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictCold);

    const call = mockShare.mock.calls[0][0];
    expect(call.text).toMatch(/brutal/i);
  });

  it('builds 2-way tie text', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictTwoWayTie);

    const call = mockShare.mock.calls[0][0];
    expect(call.text).toMatch(/two-way tie/i);
    expect(call.text).toContain('Alice');
    expect(call.text).toContain('Carol');
  });

  it('builds 3-way tie text', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictThreeWayTie);

    const call = mockShare.mock.calls[0][0];
    expect(call.text).toMatch(/three on/i);
    expect(call.text).toContain('Alice');
    expect(call.text).toContain('Carol');
    expect(call.text).toContain('Dave');
  });

  it('includes the league match URL in the share text', async () => {
    mockShare.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictSolo);

    const call = mockShare.mock.calls[0][0];
    expect(call.text).toContain('/leagues/5/match/24');
  });

  it('falls back to clipboard when navigator.share is unavailable', async () => {
    Object.defineProperty(navigator, 'share', { value: undefined, writable: true, configurable: true });
    mockWriteText.mockResolvedValue(undefined);

    await shareVerdict(mockVerdictSolo);

    expect(mockWriteText).toHaveBeenCalledOnce();
    expect(mockWriteText.mock.calls[0][0]).toContain('Alice');
  });
});
