import { toast } from 'sonner';
import type { DugoutEvent } from '@/lib/api';

interface ShareOptions {
  text: string;
  title?: string;
  image?: Blob;
}

export async function shareWithCard({ text, title, image }: ShareOptions): Promise<void> {
  // Tier 1: Web Share API with image file
  if (navigator.share && image) {
    const file = new File([image], 'lazy-fantasy.png', { type: 'image/png' });

    // Check if sharing files is supported
    if (navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ text, title, files: [file] });
        return;
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        // Fall through to text-only share
      }
    }
  }

  // Tier 2: Web Share API text-only
  if (navigator.share) {
    try {
      await navigator.share({ text, title });
      return;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      // Fall through to clipboard
    }
  }

  // Tier 3: Clipboard copy + toast
  try {
    await navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  } catch {
    toast.error('Could not share');
  }
}

// ---- Match Verdict sharing ----

const COLD_THRESHOLD = 30;

function verdictDisplayName(event: DugoutEvent): string {
  return event.display_name || event.username;
}

function verdictUrl(event: DugoutEvent): string {
  const base = typeof window !== 'undefined'
    ? window.location.origin
    : (process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app');
  return `${base}/leagues/${event.league_id}/match/${event.match_id}`;
}

function buildVerdictText(event: DugoutEvent): string {
  const winners = event.winners ?? [];
  const topScore = event.top_score ?? 0;
  const league = event.league_name;
  const matchLabel = event.match_label ?? `M${event.match_id}`;
  const url = verdictUrl(event);

  const isYou = event.is_me && winners.length === 1;
  const isCold = !event.is_me && topScore <= COLD_THRESHOLD;
  const score = event.sport === 'football' ? `${topScore} pts` : `${topScore} of 140`;

  if (isYou) {
    return `Just ran the table at ${league}. ${score} in match ${matchLabel}.\n${url}`;
  }

  if (isCold) {
    const name = winners[0] ? (winners[0].display_name || winners[0].username) : verdictDisplayName(event);
    return `Brutal weekend at ${league}. ${name} wins it with ${topScore}.\n${url}`;
  }

  if (winners.length === 2) {
    const [a, b] = winners;
    const aName = a.display_name || a.username;
    const bName = b.display_name || b.username;
    return `Two-way tie at the top of ${league}. ${aName} & ${bName} both on ${topScore}.\n${url}`;
  }

  if (winners.length >= 3) {
    const names = winners.slice(0, 3).map(w => w.display_name || w.username).join(', ');
    return `Three on ${topScore} at ${league}. ${names} — joint top.\n${url}`;
  }

  // Solo (not you, not cold)
  const name = winners[0] ? (winners[0].display_name || winners[0].username) : verdictDisplayName(event);
  return `${name} ran the table at ${league}. ${score} in match ${matchLabel}.\n${url}`;
}

export async function shareVerdict(event: DugoutEvent): Promise<void> {
  const text = buildVerdictText(event);
  return shareWithCard({ text, title: 'Lazy Fantasy — Match Verdict' });
}
