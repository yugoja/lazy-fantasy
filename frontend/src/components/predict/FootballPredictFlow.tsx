'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ApiError,
  getMyFootballPredictionDetail,
  submitFootballPrediction,
  type MatchPlayersResponse,
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronLeft,
  Clock,
  Minus,
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type Player = MatchPlayersResponse['team_1_players'][number];
type ResultPick = 'team1' | 'draw' | 'team2';

const MAX_GOALS = 9;
const KNOCKOUT_STAGES = new Set(['R32', 'R16', 'QF', 'SF', 'THIRD', 'FINAL']);
const STAGE_LABELS: Record<string, string> = {
  GROUP: 'Group Stage',
  R32: 'Round of 32',
  R16: 'Round of 16',
  QF: 'Quarter-final',
  SF: 'Semi-final',
  THIRD: 'Third-place Playoff',
  FINAL: 'Final',
};
const QUICK_SCORES: Array<[number, number]> = [
  [1, 0],
  [2, 1],
  [1, 1],
  [0, 0],
  [2, 0],
];

function getInitials(name: string) {
  return name.replace(/\./g, '').split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase();
}
function getLastName(name: string) {
  return name.split(' ').pop() ?? name;
}
function positionLabel(role: string) {
  const map: Record<string, string> = {
    goalkeeper: 'GK', defender: 'DEF', midfielder: 'MID', forward: 'FWD',
  };
  return map[role.toLowerCase()] ?? role.slice(0, 3).toUpperCase();
}
function deriveResult(a: number, b: number): ResultPick {
  if (a > b) return 'team1';
  if (b > a) return 'team2';
  return 'draw';
}
function formatCountdown(startTime: string, now: number): string {
  const diff = new Date(startTime).getTime() - now;
  if (diff <= 0) return 'closing';
  const totalSecs = Math.floor(diff / 1000);
  const h = Math.floor(totalSecs / 3600);
  const m = Math.floor((totalSecs % 3600) / 60);
  const s = totalSecs % 60;
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

const STEP_META = [
  { title: 'Who wins it?', sub: 'Pick the result. Going for the draw is bold — bold pays.' },
  { title: 'Who shows up?', sub: 'Pick three players. Goals, assists, clean sheets — they all score.' },
  { title: 'Call the score.', sub: 'Exact final score. Nail it on the nose for the big points.' },
];

function TeamCrest({ team, size = 'md', selected }: { team: { short_name: string }; size?: 'sm' | 'md' | 'lg'; selected?: boolean }) {
  const dim = size === 'lg' ? 'h-14 w-14 text-lg' : size === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-11 w-11 text-sm';
  return (
    <div
      className={cn(
        'grid place-items-center rounded-full font-heading font-bold tracking-wide shrink-0 transition-colors',
        dim,
        selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
      )}
    >
      {team.short_name.slice(0, 3).toUpperCase()}
    </div>
  );
}

export function FootballPredictFlow({ matchId, matchData }: { matchId: number; matchData: MatchPlayersResponse }) {
  const router = useRouter();
  const { team_1, team_2, stage } = matchData;
  const isKnockout = !!stage && KNOCKOUT_STAGES.has(stage);
  const stageLabel = (stage && STAGE_LABELS[stage]) || 'World Cup';

  const [step, setStep] = useState(0); // 0 result, 1 players, 2 scoreline, 3 = (done, dialog)
  const [resultPick, setResultPick] = useState<ResultPick | null>(null);
  const [scorers, setScorers] = useState<number[]>([]);
  const [score, setScore] = useState<{ a: number; b: number }>({ a: 1, b: 0 });
  const [scoreTouched, setScoreTouched] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  // Prefill from an existing prediction.
  useEffect(() => {
    let active = true;
    getMyFootballPredictionDetail(matchId)
      .then(existing => {
        if (!active || !existing) return;
        setScore({ a: existing.team1_goals, b: existing.team2_goals });
        setScoreTouched(true);
        setScorers(existing.player_picks.map(p => p.player.id));
        if (existing.advance_winner) {
          setResultPick(existing.advance_winner.id === team_1.id ? 'team1' : 'team2');
        } else {
          setResultPick(deriveResult(existing.team1_goals, existing.team2_goals));
        }
        setIsEditing(true);
      })
      .catch(() => {/* no existing prediction is fine */});
    return () => { active = false; };
  }, [matchId, team_1.id]);

  const allPlayers = useMemo(
    () => [...matchData.team_1_players, ...matchData.team_2_players],
    [matchData.team_1_players, matchData.team_2_players],
  );
  const playerById = useMemo(() => {
    const m = new Map<number, Player>();
    allPlayers.forEach(p => m.set(p.id, p));
    return m;
  }, [allPlayers]);

  const pickResult = (pick: ResultPick) => {
    setResultPick(pick);
    if (!scoreTouched) {
      if (pick === 'team1') setScore({ a: 1, b: 0 });
      else if (pick === 'team2') setScore({ a: 0, b: 1 });
      else setScore({ a: 1, b: 1 });
    }
  };

  const changeScore = (side: 'a' | 'b', delta: number) => {
    setScore(prev => {
      const next = { ...prev, [side]: Math.max(0, Math.min(MAX_GOALS, prev[side] + delta)) };
      setScoreTouched(true);
      // Keep the result/advance pick coherent with the scoreline.
      const derived = deriveResult(next.a, next.b);
      if (derived !== 'draw') setResultPick(derived);
      return next;
    });
  };
  const setQuickScore = (a: number, b: number) => {
    setScore({ a, b });
    setScoreTouched(true);
    const derived = deriveResult(a, b);
    if (derived !== 'draw') setResultPick(derived);
  };

  const toggleScorer = (id: number) => {
    setScorers(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const canProceed = step === 0 ? resultPick !== null : step === 1 ? scorers.length === 3 : true;

  const handleSubmit = useCallback(async () => {
    setError('');
    if (scorers.length !== 3) {
      setError('Pick three players first.');
      setStep(1);
      return;
    }
    const isDraw = score.a === score.b;
    const advanceWinnerId = isKnockout && isDraw
      ? (resultPick === 'team2' ? team_2.id : team_1.id)
      : null;
    setIsSubmitting(true);
    try {
      await submitFootballPrediction({
        match_id: matchId,
        team1_goals: score.a,
        team2_goals: score.b,
        advance_winner_id: advanceWinnerId,
        player_pick_1_id: scorers[0],
        player_pick_2_id: scorers[1],
        player_pick_3_id: scorers[2],
      });
      setShowSuccess(true);
      window.dispatchEvent(new Event('prediction-submitted'));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to submit prediction');
    } finally {
      setIsSubmitting(false);
    }
  }, [scorers, score, isKnockout, resultPick, team_1.id, team_2.id, matchId]);

  const onNext = () => {
    if (step < 2) { setStep(step + 1); return; }
    handleSubmit();
  };
  const onBack = () => {
    if (step > 0) setStep(step - 1);
    else router.push('/predictions');
  };

  const derivedResult = deriveResult(score.a, score.b);
  const resultText = (() => {
    if (derivedResult === 'team1') return `${team_1.short_name} win`;
    if (derivedResult === 'team2') return `${team_2.short_name} win`;
    if (isKnockout) {
      const adv = resultPick === 'team2' ? team_2 : team_1;
      return `Draw · ${adv.short_name} on pens`;
    }
    return 'Draw';
  })();

  const nextLabel = step === 0
    ? (resultPick ? 'Next: pick players' : 'Pick a result')
    : step === 1
      ? (scorers.length === 3 ? 'Next: call the score' : `Pick ${3 - scorers.length} more`)
      : (isEditing ? 'Update picks' : 'Lock in picks');

  const countdown = formatCountdown(matchData.start_time, now);

  return (
    <div className="flex flex-col mx-auto max-w-[430px]" style={{ height: 'calc(100dvh - 56px - 64px)' }}>
      {/* ── Match stub ── */}
      <div className="flex-shrink-0 px-5 pt-3 pb-4 border-b border-border bg-gradient-to-b from-primary/5 to-background">
        <div className="flex items-center justify-between text-[10px] font-heading font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          <span className="flex items-center gap-2">
            <button type="button" onClick={() => router.push('/predictions')} className="hover:text-foreground">
              <ArrowLeft className="h-3.5 w-3.5" />
            </button>
            World Cup · {stageLabel}
          </span>
          {isKnockout && (
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-bold text-amber-500">2× POINTS</span>
          )}
        </div>

        <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <div className="flex flex-col items-center gap-2">
            <TeamCrest team={team_1} size="lg" />
            <span className="font-heading text-xs font-bold uppercase tracking-wider">{team_1.short_name}</span>
          </div>
          <span className="font-heading text-2xl italic text-muted-foreground">vs</span>
          <div className="flex flex-col items-center gap-2">
            <TeamCrest team={team_2} size="lg" />
            <span className="font-heading text-xs font-bold uppercase tracking-wider">{team_2.short_name}</span>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-center gap-1.5 text-primary">
          <Clock className="h-3.5 w-3.5" />
          <span className="font-heading text-sm font-bold tabular-nums">{countdown}</span>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">until kickoff</span>
        </div>
      </div>

      {/* ── Step pills + meta ── */}
      <div className="flex-shrink-0 px-5 pt-4">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className={cn(
                'h-1 flex-1 rounded-full transition-all duration-300',
                i <= step ? 'bg-primary' : 'bg-muted',
              )}
            />
          ))}
        </div>
        <div className="mt-3 flex items-baseline justify-between font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          <span>Pick {String(step + 1).padStart(2, '0')} / 03</span>
        </div>
        <h2 className="mt-1 font-heading text-2xl font-bold tracking-tight">{STEP_META[step].title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{STEP_META[step].sub}</p>
      </div>

      {/* ── Panels ── */}
      <div className="flex-1 overflow-y-auto px-5 pb-5 pt-4">
        {step === 0 && (
          <div className="grid gap-2.5">
            <ResultTile
              label={`${team_1.name} to win`}
              badge={team_1.short_name}
              selected={resultPick === 'team1'}
              onClick={() => pickResult('team1')}
            />
            {!isKnockout && (
              <ResultTile
                label="Draw"
                badge="X"
                contrarian
                selected={resultPick === 'draw'}
                onClick={() => pickResult('draw')}
              />
            )}
            <ResultTile
              label={`${team_2.name} to win`}
              badge={team_2.short_name}
              selected={resultPick === 'team2'}
              onClick={() => pickResult('team2')}
            />
            {isKnockout && (
              <p className="px-1 pt-1 text-xs text-muted-foreground">
                Knockout — pick who goes through. You can still call a draw on the next-but-one step (it goes to pens).
              </p>
            )}
          </div>
        )}

        {step === 1 && (
          <div>
            {/* Tray */}
            <div className="grid grid-cols-3 gap-2 rounded-2xl border border-dashed border-border bg-card/40 p-3">
              {[0, 1, 2].map(i => {
                const p = scorers[i] != null ? playerById.get(scorers[i]) : undefined;
                return (
                  <div
                    key={i}
                    className={cn(
                      'relative flex aspect-[1/1.15] flex-col items-center justify-center gap-1.5 rounded-xl border p-2 text-center transition-all',
                      p ? 'border-primary bg-primary/10' : 'border-dashed border-border bg-background/40',
                    )}
                  >
                    <span className="absolute left-1.5 top-1.5 grid h-4 w-4 place-items-center rounded text-[9px] font-bold text-muted-foreground">
                      {i + 1}
                    </span>
                    {p ? (
                      <>
                        <div className="grid h-9 w-9 place-items-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                          {getInitials(p.name)}
                        </div>
                        <span className="font-heading text-xs font-bold leading-tight">{getLastName(p.name)}</span>
                      </>
                    ) : (
                      <span className="text-[11px] text-muted-foreground">{i === 0 ? 'Tap a player' : `${i + 1}${i === 1 ? 'nd' : 'rd'} pick`}</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Pooled player list, grouped by team */}
            <div className="mt-4 space-y-4">
              {[
                { team: team_1, players: matchData.team_1_players },
                { team: team_2, players: matchData.team_2_players },
              ].map(({ team, players }) => (
                <div key={team.id}>
                  <h4 className="mb-2 flex items-center gap-2 font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                    {team.name}
                    <span className="h-px flex-1 bg-gradient-to-r from-border to-transparent" />
                  </h4>
                  <div className="grid gap-1.5">
                    {players.map(p => {
                      const selected = scorers.includes(p.id);
                      const full = scorers.length >= 3 && !selected;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          disabled={full}
                          onClick={() => toggleScorer(p.id)}
                          className={cn(
                            'flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all',
                            selected
                              ? 'border-primary bg-primary/10'
                              : 'border-border bg-card/60 active:scale-[0.99]',
                            full && 'opacity-45',
                          )}
                        >
                          <div className={cn(
                            'grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold',
                            selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
                          )}>
                            {getInitials(p.name)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-heading text-sm font-bold">{p.name}</div>
                            <div className="text-[11px] text-muted-foreground">{positionLabel(p.role)} · {team.short_name}</div>
                          </div>
                          <div className={cn(
                            'grid h-6 w-6 shrink-0 place-items-center rounded-md border transition-colors',
                            selected ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-transparent',
                          )}>
                            <Check className="h-3.5 w-3.5" />
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <div className="rounded-2xl border border-border bg-card/60 px-4 py-7">
              <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-2">
                <ScoreColumn label={team_1.short_name} value={score.a} onStep={d => changeScore('a', d)} />
                <span className="mt-6 font-heading text-4xl font-medium text-muted-foreground/40">–</span>
                <ScoreColumn label={team_2.short_name} value={score.b} onStep={d => changeScore('b', d)} />
              </div>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center gap-2 font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Common scorelines
                <span className="h-px flex-1 bg-gradient-to-r from-border to-transparent" />
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {QUICK_SCORES.map(([a, b]) => {
                  const matched = score.a === a && score.b === b;
                  return (
                    <button
                      key={`${a}-${b}`}
                      type="button"
                      onClick={() => setQuickScore(a, b)}
                      className={cn(
                        'rounded-lg border py-2 text-center font-heading text-sm font-bold tabular-nums transition-all',
                        matched ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground active:scale-95',
                      )}
                    >
                      {a}-{b}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-5 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm">
              <span className="text-muted-foreground">Your call: </span>
              <span className="font-semibold">{resultText} · {score.a}–{score.b}</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Action bar ── */}
      <div className="flex-shrink-0 flex items-center gap-2.5 border-t border-border bg-background px-5 py-3.5">
        <button
          type="button"
          onClick={onBack}
          className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-border text-muted-foreground hover:text-foreground"
          aria-label="Back"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <Button
          onClick={onNext}
          disabled={!canProceed || isSubmitting}
          size="lg"
          className="h-12 flex-1 gap-2"
        >
          {isSubmitting ? 'Saving…' : nextLabel}
          {step < 2 && !isSubmitting && <ArrowRight className="h-4 w-4" />}
        </Button>
      </div>

      {error && step === 2 && (
        <p className="px-5 pb-2 text-center text-sm text-destructive">{error}</p>
      )}

      {/* ── Success dialog ── */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent className="sm:max-w-md">
          <div className="mt-2 mb-1 flex justify-center">
            <div className="relative">
              <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
              <div className="relative grid h-16 w-16 place-items-center rounded-full border border-primary/20 bg-primary/10">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
            </div>
          </div>
          <DialogHeader className="items-center pb-0 text-center">
            <DialogTitle className="text-xl">{isEditing ? 'Picks updated!' : 'Picks locked.'}</DialogTitle>
            <DialogDescription>{team_1.short_name} vs {team_2.short_name} · {stageLabel}</DialogDescription>
          </DialogHeader>
          <div className="divide-y divide-border rounded-lg border border-border bg-muted/30 text-sm">
            <SummaryRow label="Result" value={resultText} />
            <SummaryRow
              label="Players"
              value={scorers.map(id => getLastName(playerById.get(id)?.name ?? '')).filter(Boolean).join(' · ') || '—'}
            />
            <SummaryRow label="Final score" value={`${score.a} – ${score.b}`} />
          </div>
          <div className="flex flex-col gap-3">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(
                `⚽ ${team_1.short_name} vs ${team_2.short_name} — I've locked my picks!\nThink you can do better? ${process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app'}/predictions`,
              )}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#25D366]/30 bg-[#25D366]/5 py-2.5 text-sm font-medium text-[#25D366]"
            >
              Nudge your group
            </a>
            <Link href="/predictions" className="w-full">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="mr-2 h-4 w-4" />Back to Matches
              </Button>
            </Link>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ResultTile({ label, badge, selected, contrarian, onClick }: {
  label: string; badge: string; selected?: boolean; contrarian?: boolean; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-3.5 rounded-2xl border-2 px-4 py-4 text-left transition-all',
        selected ? 'border-primary bg-primary/10 shadow-[0_18px_40px_-26px_hsl(var(--primary))]' : 'border-border bg-card/60 active:scale-[0.99]',
      )}
    >
      <div className={cn(
        'grid h-11 w-11 shrink-0 place-items-center rounded-full font-heading text-sm font-bold',
        selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
      )}>
        {badge}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 font-heading text-base font-bold">
          {label}
          {contrarian && <span className="text-[10px] font-bold uppercase tracking-widest text-amber-500">Contrarian</span>}
        </div>
      </div>
      {selected && <CheckCircle2 className="h-5 w-5 text-primary" />}
    </button>
  );
}

function ScoreColumn({ label, value, onStep }: { label: string; value: number; onStep: (delta: number) => void }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <span className="rounded bg-muted px-2.5 py-1 font-heading text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="font-heading text-7xl font-bold leading-none tabular-nums">{value}</span>
      <div className="flex gap-2">
        <button type="button" onClick={() => onStep(-1)} aria-label={`Decrease ${label}`} className="grid h-8 w-9 place-items-center rounded-lg border border-border text-muted-foreground hover:text-foreground active:scale-95">
          <Minus className="h-4 w-4" />
        </button>
        <button type="button" onClick={() => onStep(1)} aria-label={`Increase ${label}`} className="grid h-8 w-9 place-items-center rounded-lg border border-border text-muted-foreground hover:text-foreground active:scale-95">
          <Plus className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <span className="font-heading text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <span className="truncate text-right font-heading text-sm font-bold">{value}</span>
    </div>
  );
}
