'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Check, X } from 'lucide-react';
import { DugoutEvent, VerdictHits, VerdictWinner, VerdictRunner } from '@/lib/api';
import { cn } from '@/lib/utils';
import { shareVerdict } from '@/lib/share';
import { analytics } from '@/lib/analytics';

interface Props {
  event: DugoutEvent;
  currentUsername: string | null;
  onDismiss?: () => void;
}

type Variant = 'default' | 'you' | 'cold';

const COLD_SCORE_THRESHOLD = 30;
const TIGHT_MARGIN = 5;

// ---- helpers ----

function initials(name: string) {
  return name.replace(/\./g, '').split(/\s+/).filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

function shortName(w: { username: string; display_name: string | null }) {
  return w.display_name || w.username;
}

function rankShiftLabel(prev: number | null, current: number): { text: string; tone: 'up' | 'flat' | 'down' } {
  if (prev == null || prev === current) {
    return { text: `held #${current}`, tone: 'flat' };
  }
  const delta = prev - current;
  if (delta > 0) {
    return { text: `↑${delta} · was #${prev}`, tone: 'up' };
  }
  return { text: `↓${Math.abs(delta)} · was #${prev}`, tone: 'down' };
}

// ---- copy lookup ----

interface Copy { headline: React.ReactNode; sub: React.ReactNode; primaryCta: string }

function getCopy(
  variant: Variant,
  winners: VerdictWinner[],
  topScore: number,
  isFlawless: boolean,
  isTight: boolean,
  tightMargin: number | null,
  isMultiTie: boolean,
  isFootball: boolean,
): Copy {
  if (variant === 'you' && winners.length === 1) {
    return {
      headline: <><em>You</em> ran the table.</>,
      sub: <>{topScore}{isFootball ? ' pts' : '/140'}. <i>Best card on the board.</i></>,
      primaryCta: 'Brag now →',
    };
  }
  if (variant === 'cold') {
    const w = winners[0];
    return {
      headline: <><em>{topScore}</em> wins it. Yes really.</>,
      sub: <>Brutal weekend. <i>{shortName(w)} takes it with {topScore}.</i></>,
      primaryCta: 'Apologise in group →',
    };
  }
  if (winners.length === 2) {
    const [a, b] = winners;
    return {
      headline: <><em>Tie</em> at the top.</>,
      sub: <>{shortName(a)} & {shortName(b)} both on {topScore}. <i>No outright winner.</i></>,
      primaryCta: 'Drop in group →',
    };
  }
  if (winners.length >= 3) {
    return {
      headline: <><em>{winners.length}</em> on {topScore}.</>,
      sub: <>{winners.map(shortName).slice(0, 3).join(', ')} — <i>joint top.</i></>,
      primaryCta: 'Drop in group →',
    };
  }
  // Solo winner
  const w = winners[0];
  if (isFlawless) {
    return {
      headline: <><em>{shortName(w)}</em> ran the table.</>,
      sub: <>Called all four. <i>Flawless card.</i></>,
      primaryCta: 'Drop in group →',
    };
  }
  if (isTight) {
    return {
      headline: <><em>{shortName(w)}</em>, by {tightMargin}.</>,
      sub: <>{topScore} pts. <i>Photo finish.</i></>,
      primaryCta: 'Drop in group →',
    };
  }
  return {
    headline: <><em>{shortName(w)}</em> takes {/* match label appended via header */}it.</>,
    sub: <>{topScore} pts. <i>Comfortable cushion.</i></>,
    primaryCta: 'Drop in group →',
  };
  // (lint: unused isMultiTie kept for symmetry / future use)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  isMultiTie;
}

// ---- subviews ----

function hitCells(hits: VerdictHits, sport: string): Array<{ label: string; ok: boolean }> {
  if (sport === 'football') {
    return [
      { label: 'Result', ok: !!hits.outcome },
      { label: 'Score', ok: !!hits.exact_score },
      { label: 'Pick 1', ok: !!hits.pick_1 },
      { label: 'Pick 2', ok: !!hits.pick_2 },
      { label: 'Pick 3', ok: !!hits.pick_3 },
    ];
  }
  return [
    { label: 'Winner', ok: hits.winner },
    { label: 'Runs', ok: hits.runs_t1 || hits.runs_t2 },
    { label: 'Wkts', ok: hits.wkts_t1 || hits.wkts_t2 },
    { label: 'POM', ok: hits.pom },
  ];
}

function HitsGrid({ hits, variant, sport }: { hits: VerdictHits; variant: Variant; sport: string }) {
  const cells = hitCells(hits, sport);
  const hitBg =
    variant === 'you' ? 'bg-accent text-accent-foreground'
    : variant === 'cold' ? 'bg-sky-400 text-slate-900'
    : 'bg-primary text-primary-foreground';
  return (
    <div className={cn('mt-3 grid gap-1.5', cells.length === 5 ? 'grid-cols-5' : 'grid-cols-4')}>
      {cells.map((c) => (
        <div key={c.label} className="flex flex-col items-center gap-1 rounded-md bg-black/30 py-2">
          <span className={cn(
            'h-[18px] w-[18px] rounded-full grid place-items-center text-[11px]',
            c.ok ? hitBg : 'border border-border text-muted-foreground/60',
          )}>
            {c.ok ? <Check className="h-3 w-3" strokeWidth={3} /> : '−'}
          </span>
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {c.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function CompactHitRow({ winner, sport }: { winner: VerdictWinner; sport: string }) {
  const cells = hitCells(winner.hits, sport).map(c => c.ok);
  return (
    <div className="flex items-center gap-1.5 rounded-md bg-black/30 px-2 py-1.5">
      <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent mr-0.5">
        {initials(shortName(winner))}
      </span>
      {cells.map((ok, i) => (
        <span key={i} className={cn(
          'h-3.5 w-3.5 rounded-full grid place-items-center text-[9px]',
          ok ? 'bg-primary text-primary-foreground' : 'border border-border text-muted-foreground/60',
        )}>
          {ok ? <Check className="h-2.5 w-2.5" strokeWidth={3.5} /> : '·'}
        </span>
      ))}
    </div>
  );
}

function SoloWinnerPanel({ winner, topScore, variant, sport }: { winner: VerdictWinner; topScore: number; variant: Variant; sport: string }) {
  const rank = rankShiftLabel(winner.prev_rank, winner.new_rank);
  const bigScore =
    variant === 'you' ? 'text-accent'
    : variant === 'cold' ? 'text-sky-300'
    : 'text-primary';
  const borderColor =
    variant === 'you' ? 'border-accent/40 bg-accent/10'
    : variant === 'cold' ? 'border-sky-400/40 bg-sky-500/5'
    : 'border-primary/40 bg-primary/10';
  const avBg =
    variant === 'you' ? 'bg-gradient-to-br from-amber-300 to-amber-600'
    : variant === 'cold' ? 'bg-gradient-to-br from-sky-300 to-sky-600'
    : 'bg-gradient-to-br from-emerald-300 to-emerald-600';
  const rankColor = rank.tone === 'up' ? 'text-accent' : rank.tone === 'down' ? 'text-sky-300' : 'text-muted-foreground';
  return (
    <div className={cn('mt-4 grid grid-cols-[44px_1fr_auto] items-center gap-3 rounded-xl border-[1.5px] p-3.5', borderColor)}>
      <div className={cn('h-11 w-11 rounded-full grid place-items-center font-bold text-[15px] tracking-wider text-slate-900', avBg)}>
        {initials(shortName(winner))}
      </div>
      <div className="min-w-0">
        <div className="text-[15px] font-bold leading-tight font-heading truncate">
          {variant === 'you' ? `You · @${winner.username}` : shortName(winner)}
        </div>
        <div className={cn('mt-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] font-heading', rankColor)}>
          {rank.text}
        </div>
      </div>
      <div className={cn('font-heading font-bold text-3xl leading-none tabular-nums tracking-tight', bigScore)}>
        {topScore}<span className="ml-0.5 align-[5px] text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{sport === 'football' ? 'pts' : '/140'}</span>
      </div>
    </div>
  );
}

function TwoWayTiePanel({ winners, topScore }: { winners: VerdictWinner[]; topScore: number }) {
  return (
    <div className="mt-4 relative grid grid-cols-2 rounded-xl border-[1.5px] border-accent/40 bg-accent/10 overflow-hidden">
      <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-90deg] bg-card text-accent text-[9px] font-bold uppercase tracking-[0.3em] px-2 py-1 rounded border border-accent/50 z-10">
        Tied
      </span>
      {winners.map((w, i) => (
        <div key={w.user_id} className={cn(
          'grid grid-cols-[36px_1fr] items-center gap-2.5 p-3.5',
          i > 0 && 'border-l border-dashed border-accent/40',
        )}>
          <div className="h-9 w-9 rounded-full grid place-items-center bg-gradient-to-br from-emerald-300 to-emerald-600 text-slate-900 font-bold text-[12px]">
            {initials(shortName(w))}
          </div>
          <div className="min-w-0">
            <div className="font-heading font-bold text-[13px] leading-tight truncate">{shortName(w)}</div>
            <div className="font-heading font-bold text-[22px] leading-none tabular-nums tracking-tight text-accent mt-1">
              {topScore}<span className="ml-0.5 align-[4px] text-[9px] font-medium uppercase tracking-[0.16em] text-muted-foreground">pts</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ThreeWayTiePanel({ winners, topScore }: { winners: VerdictWinner[]; topScore: number }) {
  return (
    <div className="mt-4 rounded-xl border-[1.5px] border-accent/40 bg-accent/10 p-3.5">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] font-bold uppercase tracking-[0.22em] font-heading text-accent">
          Joint top · {topScore} pts
        </span>
        <span className="font-heading font-bold text-2xl leading-none tracking-tight tabular-nums text-accent">
          {winners.length}<span className="ml-0.5 align-[3px] text-[9px] font-medium uppercase tracking-[0.16em] text-muted-foreground">tied</span>
        </span>
      </div>
      {winners.map((w, i) => {
        const rank = rankShiftLabel(w.prev_rank, w.new_rank);
        const toneClass = rank.tone === 'up' ? 'text-accent' : rank.tone === 'down' ? 'text-sky-300' : 'text-muted-foreground';
        return (
          <div key={w.user_id} className={cn(
            'grid grid-cols-[32px_1fr_auto] items-center gap-2.5 py-1.5',
            i > 0 && 'border-t border-dashed border-accent/30',
          )}>
            <div className="h-8 w-8 rounded-full grid place-items-center bg-gradient-to-br from-emerald-300 to-emerald-600 text-slate-900 font-bold text-[11px]">
              {initials(shortName(w))}
            </div>
            <span className="font-heading font-semibold text-[13px] truncate">{shortName(w)}</span>
            <span className={cn('font-heading text-[10px] font-semibold uppercase tracking-[0.14em] tabular-nums whitespace-nowrap', toneClass)}>
              {rank.text}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function RunnerUpRow({ runner, rank }: { runner: VerdictRunner; rank: number }) {
  const shift = rankShiftLabel(runner.prev_rank, runner.new_rank);
  return (
    <div className="grid grid-cols-[18px_26px_1fr_auto] items-center gap-2.5 rounded-lg bg-secondary px-3 py-1.5">
      <span className="font-heading font-bold text-[11px] text-muted-foreground">{rank}</span>
      <span className="h-6 w-6 rounded-full grid place-items-center bg-gradient-to-br from-emerald-300/70 to-emerald-600/70 text-slate-900 font-bold text-[10px]">
        {initials(shortName(runner))}
      </span>
      <span className="text-[12.5px] truncate">
        {shortName(runner)}{' '}
        <small className="text-muted-foreground text-[10px] ml-1">{shift.text}</small>
      </span>
      <span className="font-heading font-bold text-[13px] tabular-nums">
        {runner.points_earned}<small className="text-[9.5px] font-medium text-muted-foreground ml-0.5 tracking-wide">pts</small>
      </span>
    </div>
  );
}

// ---- main ----

export function MatchVerdictCard({ event, currentUsername, onDismiss }: Props) {
  const winners = event.winners ?? [];
  const runnersUp = event.runners_up ?? [];
  const topScore = event.top_score ?? 0;
  const runnerScore = event.runner_up_score;

  const hasVerdict = winners.length > 0;
  // Fire result_revealed once when a real verdict card first renders for the user.
  useEffect(() => {
    if (!hasVerdict) return;
    analytics.resultRevealed({
      match_id: String(event.match_id),
      league_id: event.league_id != null ? String(event.league_id) : undefined,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.match_id, event.league_id, hasVerdict]);

  if (winners.length === 0) return null;

  const isYou = !!currentUsername && winners.some(w => w.username === currentUsername);
  const isCold = !isYou && topScore <= COLD_SCORE_THRESHOLD;
  const variant: Variant = isYou ? 'you' : isCold ? 'cold' : 'default';

  const isFootball = event.sport === 'football';
  const isMultiTie = winners.length >= 2;
  const isFlawless = !isFootball && winners.length === 1 && topScore === 140;
  const tightMargin = (!isMultiTie && runnerScore != null) ? topScore - runnerScore : null;
  const isTight = tightMargin != null && tightMargin > 0 && tightMargin <= TIGHT_MARGIN;

  const copy = getCopy(variant, winners, topScore, isFlawless, isTight, tightMargin, isMultiTie, isFootball);

  const headlineEmClass =
    variant === 'you' ? 'not-italic font-normal text-accent'
    : variant === 'cold' ? 'not-italic font-normal text-sky-300'
    : 'not-italic font-normal text-accent';

  // Header POM colors
  const pomColor = variant === 'cold' ? 'text-sky-300' : 'text-accent';

  return (
    <div className="relative w-full max-w-[400px] rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-[0_24px_60px_-20px_rgba(0,0,0,0.45)] overflow-hidden">
      {/* subtle top glow */}
      <div
        className="absolute inset-x-0 top-0 h-32 pointer-events-none"
        style={{
          background: variant === 'cold'
            ? 'radial-gradient(60% 80% at 50% 0%, hsl(200 80% 60% / 0.10), transparent 65%)'
            : variant === 'you'
              ? 'radial-gradient(60% 80% at 50% 0%, hsl(var(--accent) / 0.18), transparent 65%)'
              : 'radial-gradient(60% 80% at 50% 0%, hsl(var(--primary) / 0.15), transparent 65%)',
        }}
      />
      <div className="relative">
        {/* Kicker */}
        <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground font-heading">
          <span className="truncate">{event.league_name} · {event.match_label ?? `M${event.match_id}`}</span>
          <span className="flex items-center gap-1.5">
            <span className={cn('inline-block h-1.5 w-1.5 rotate-45', pomColor === 'text-accent' ? 'bg-accent' : 'bg-sky-300')}></span>
            <span className={pomColor}>Verdict</span>
            {onDismiss && (
              <button
                onClick={onDismiss}
                aria-label="Dismiss"
                className="ml-1 h-5 w-5 rounded-full grid place-items-center text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        </div>

        {/* Fixture row */}
        {isFootball ? (
          <div className="mt-3 flex items-center justify-center gap-2.5 pb-3 border-b border-dashed border-border">
            <span className={cn(
              'inline-grid place-items-center h-[22px] min-w-[34px] px-1.5 rounded-full text-[9px] font-bold tracking-wider font-heading',
              event.is_draw ? 'bg-muted' : event.winning_team_short === event.team1_short
                ? 'bg-muted shadow-[0_0_0_1.5px_hsl(var(--accent)/0.55)]' : 'bg-muted opacity-50',
            )}>
              {event.team1_short ?? '—'}
            </span>
            <span className="font-heading font-bold text-[18px] leading-none tabular-nums tracking-tight">
              {event.team1_goals ?? 0}<span className="text-muted-foreground mx-1.5">–</span>{event.team2_goals ?? 0}
            </span>
            <span className={cn(
              'inline-grid place-items-center h-[22px] min-w-[34px] px-1.5 rounded-full text-[9px] font-bold tracking-wider font-heading',
              event.is_draw ? 'bg-muted' : event.winning_team_short === event.team2_short
                ? 'bg-muted shadow-[0_0_0_1.5px_hsl(var(--accent)/0.55)]' : 'bg-muted opacity-50',
            )}>
              {event.team2_short ?? '—'}
            </span>
            {event.is_draw && (
              <span className="ml-1 font-heading text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Draw</span>
            )}
          </div>
        ) : (
          <div className="mt-3 flex items-center gap-2 pb-3 border-b border-dashed border-border">
            <span className="inline-grid place-items-center h-[22px] w-[22px] rounded-full bg-muted text-[9px] font-bold tracking-wider font-heading opacity-50">
              {event.losing_team_short ?? '—'}
            </span>
            <span className="italic font-normal text-[13.5px] text-muted-foreground mx-0.5">vs</span>
            <span
              className={cn(
                'inline-grid place-items-center h-[22px] w-[22px] rounded-full text-[9px] font-bold tracking-wider font-heading',
                variant === 'cold'
                  ? 'bg-muted shadow-[0_0_0_1.5px_hsl(200_80%_60%/0.55)]'
                  : 'bg-muted shadow-[0_0_0_1.5px_hsl(var(--accent)/0.55)]',
              )}
            >
              {event.winning_team_short ?? '—'}
            </span>
            {event.pom_player_name && (
              <span className={cn('ml-auto inline-flex items-center gap-1.5 font-heading text-[10px] font-semibold uppercase tracking-[0.16em]', pomColor)}>
                <span className="text-[11px]">★</span>
                {event.pom_player_name} · POM
              </span>
            )}
          </div>
        )}

        {/* Headline + sub */}
        <h3 className="mt-4 font-heading text-[26px] font-bold leading-none tracking-[-0.022em]">
          <span className={headlineEmClass}>
            {copy.headline}
          </span>
        </h3>
        <p className="mt-2 text-[13px] leading-snug text-muted-foreground">
          {copy.sub}
        </p>

        {/* Winner panel(s) */}
        {winners.length === 1 && <SoloWinnerPanel winner={winners[0]} topScore={topScore} variant={variant} sport={event.sport ?? 'cricket'} />}
        {winners.length === 2 && <TwoWayTiePanel winners={winners} topScore={topScore} />}
        {winners.length >= 3 && <ThreeWayTiePanel winners={winners} topScore={topScore} />}

        {/* Hits */}
        {winners.length === 1 && <HitsGrid hits={winners[0].hits} variant={variant} sport={event.sport ?? 'cricket'} />}
        {winners.length === 2 && (
          <div className="mt-2.5 grid grid-cols-2 gap-1.5">
            {winners.map(w => <CompactHitRow key={w.user_id} winner={w} sport={event.sport ?? 'cricket'} />)}
          </div>
        )}
        {/* 3-way tie deliberately omits hits — per-category outcomes per-row would mislead */}

        {/* Runners-up */}
        {runnersUp.length > 0 && (
          <div className="mt-3 grid gap-1.5">
            {runnersUp.map((r, i) => (
              <RunnerUpRow key={r.user_id} runner={r} rank={winners.length + i + 1} />
            ))}
          </div>
        )}

        {/* CTAs */}
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => shareVerdict(event)}
            className={cn(
              'flex-1 h-10 rounded-[10px] font-heading text-[12.5px] font-bold uppercase tracking-[0.08em] inline-flex items-center justify-center gap-1.5',
              variant === 'you' ? 'bg-accent text-accent-foreground'
              : variant === 'cold' ? 'bg-sky-300 text-slate-900'
              : 'bg-primary text-primary-foreground',
            )}
          >
            {copy.primaryCta}
          </button>
          <Link
            href={`/leagues/${event.league_id}/match/${event.match_id}`}
            className="h-10 px-4 rounded-[10px] border-[1.5px] border-border text-muted-foreground font-heading text-[12.5px] font-bold uppercase tracking-[0.08em] inline-flex items-center justify-center"
          >
            Table
          </Link>
        </div>
      </div>
    </div>
  );
}
