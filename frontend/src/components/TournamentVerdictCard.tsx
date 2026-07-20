'use client';

import Link from 'next/link';
import { Check, X, Trophy } from 'lucide-react';
import type { DugoutEvent } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  event: DugoutEvent;
  onDismiss?: () => void;
}

// Emoji per award category, matching the Mega Picks flow (Boot/Ball/Glove).
const AWARD_EMOJI: Record<string, string> = { boot: '👟', ball: '🏆', glove: '🧤' };

export function TournamentVerdictCard({ event, onDismiss }: Props) {
  const lines = event.tv_lines ?? [];
  const semis = lines.filter((l) => l.category === 'semi');
  const awards = lines.filter((l) => l.category !== 'semi');
  const semisCorrect = event.tv_semis_correct ?? semis.filter((s) => s.correct).length;
  const semisTotal = event.tv_semis_total ?? semis.length;
  const points = event.tv_points ?? 0;
  const nailedIt = semisCorrect === semisTotal && semisTotal > 0;

  return (
    <div className="relative w-full max-w-[400px] overflow-hidden rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-[0_24px_60px_-20px_rgba(0,0,0,0.45)]">
      {/* Trophy watermark */}
      <Trophy className="pointer-events-none absolute -bottom-6 -right-5 h-32 w-32 rotate-12 text-amber-400/10" aria-hidden />

      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss"
          className="absolute right-3 top-3 z-10 grid h-6 w-6 place-items-center rounded-full text-muted-foreground/50 transition-colors hover:bg-muted hover:text-muted-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Header */}
      <div className="relative">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-amber-400">
          <Trophy className="h-3 w-3" /> Mega Picks
        </span>
        <div className="mt-1.5 flex items-end justify-between gap-3">
          <h3 className="font-heading text-[19px] font-bold leading-tight">
            {event.tournament_name ?? 'Tournament'} — how you did
          </h3>
          <div className="shrink-0 text-right">
            <div className="font-heading text-3xl font-bold leading-none tabular-nums text-amber-400">
              {points}
            </div>
            <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">pts</div>
          </div>
        </div>
      </div>

      {/* Semi-finalists */}
      <div className="relative mt-4">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Semi-finalists
          </span>
          <span className={cn('text-[11px] font-bold', nailedIt ? 'text-accent' : 'text-foreground')}>
            {semisCorrect}/{semisTotal}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {semis.map((s, i) => (
            <span
              key={i}
              className={cn(
                'inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] font-semibold',
                s.correct
                  ? 'bg-accent/15 text-accent'
                  : 'bg-muted/60 text-muted-foreground line-through decoration-muted-foreground/40',
              )}
            >
              {s.correct ? <Check className="h-3 w-3" strokeWidth={3} /> : <X className="h-3 w-3" strokeWidth={3} />}
              {s.pick ?? '—'}
            </span>
          ))}
        </div>
      </div>

      {/* Awards */}
      <div className="relative mt-4 grid gap-1.5">
        {awards.map((a, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-2 rounded-lg bg-black/20 px-2.5 py-2 text-[12.5px]"
          >
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span>{AWARD_EMOJI[a.category] ?? '🏅'}</span>
              <span className="font-medium text-foreground">{a.label}</span>
            </span>
            {a.correct ? (
              <span className="inline-flex items-center gap-1 font-semibold text-accent">
                <Check className="h-3.5 w-3.5" strokeWidth={3} /> {a.pick}
              </span>
            ) : (
              <span className="text-right leading-tight">
                <span className="text-muted-foreground line-through decoration-muted-foreground/40">
                  {a.pick ?? '—'}
                </span>
                {a.actual && (
                  <span className="ml-1.5 font-semibold text-foreground">→ {a.actual}</span>
                )}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Footer CTA */}
      <Link
        href="/leaderboard"
        className="relative mt-4 flex h-9 items-center justify-center rounded-[10px] bg-amber-400 font-heading text-[12px] font-bold uppercase tracking-[0.08em] text-slate-900"
      >
        See the table
      </Link>
    </div>
  );
}
