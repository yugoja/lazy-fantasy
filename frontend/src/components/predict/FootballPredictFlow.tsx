'use client';

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  Info,
  Minus,
  Plus,
} from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';

type Player = MatchPlayersResponse['team_1_players'][number];

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

const ROLE_ORDER = ['goalkeeper', 'defender', 'midfielder', 'forward'];
const ROLE_LIMITS: Record<string, number> = { goalkeeper: 1, defender: 4, midfielder: 3, forward: 3 };
const ROLE_Y: Record<string, { top: number; bottom: number }> = {
  goalkeeper: { top: 5, bottom: 95 },
  defender:   { top: 18, bottom: 82 },
  midfielder: { top: 30, bottom: 70 },
  forward:    { top: 41, bottom: 59 },
};

function getInitials(name: string) {
  return name.replace(/\./g, '').split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase();
}
// Player names are stored as "SURNAME Firstname" (surname in caps), e.g.
// "MESSI Lionel" or "HADJ MOUSSA Anis". Render as first-initial + surname → "L Messi".
function shortName(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const title = (s: string) =>
    s.split(/\s+/).map(w => (w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w)).join(' ');
  if (words.length <= 1) return title(name);

  const isUpper = (w: string) => w === w.toUpperCase() && w !== w.toLowerCase();
  let i = 0;
  while (i < words.length && isUpper(words[i])) i++;
  const surnameWords = words.slice(0, i);
  const givenWords = words.slice(i);

  // Mixed case "SURNAME Firstname": leading caps = surname, rest = given name.
  // All-caps fallback: treat as "First ... Last" order.
  const initial = (givenWords[0] ?? words[0])[0];
  const surname = surnameWords.length && givenWords.length ? surnameWords.join(' ') : words[words.length - 1];
  return `${initial.toUpperCase()} ${title(surname)}`;
}
function positionName(role: string) {
  const map: Record<string, string> = {
    goalkeeper: 'Keeper', defender: 'Defender', midfielder: 'Midfielder', forward: 'Attacker',
  };
  return map[role.toLowerCase()] ?? role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
}
// Team accent classes — green for team 1 (matches brand), amber for team 2.
// Selection is shown with a ring + check, so colour always reads as "which team".
function teamColors(isTeam1: boolean) {
  return isTeam1
    ? { fill: 'bg-primary text-primary-foreground', border: 'border-primary bg-primary/10', check: 'border-primary bg-primary text-primary-foreground' }
    : { fill: 'bg-amber-500 text-black', border: 'border-amber-500 bg-amber-500/10', check: 'border-amber-500 bg-amber-500 text-black' };
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

function layoutPlayers(players: Player[]): { starters: Player[]; subs: Player[] } {
  // Confirmed lineup: trust the real XI (is_starter) so we show the actual
  // starters and bench instead of a role-quota guess.
  if (players.some(p => p.is_starter)) {
    return {
      starters: players.filter(p => p.is_starter),
      subs: players.filter(p => !p.is_starter),
    };
  }
  const byRole: Record<string, Player[]> = {};
  for (const p of players) {
    const r = p.role.toLowerCase();
    if (!byRole[r]) byRole[r] = [];
    byRole[r].push(p);
  }
  const starters: Player[] = [];
  const subs: Player[] = [];
  for (const role of ROLE_ORDER) {
    const group = byRole[role] ?? [];
    const limit = ROLE_LIMITS[role] ?? 0;
    starters.push(...group.slice(0, limit));
    subs.push(...group.slice(limit));
  }
  for (const role of Object.keys(byRole)) {
    if (!ROLE_ORDER.includes(role)) subs.push(...byRole[role]);
  }
  return { starters, subs };
}

function getPitchPosition(role: string, idx: number, total: number, side: 'top' | 'bottom'): { x: number; y: number } {
  const ry = ROLE_Y[role.toLowerCase()];
  const y = ry ? (side === 'top' ? ry.top : ry.bottom) : 50;
  if (total <= 1) return { x: 50, y };
  // Lines with fewer players sit closer together (inset from the touchline),
  // giving the classic 4-3-3 shape: wide back four, narrower midfield & front three.
  const margin = total >= 4 ? 12 : total === 3 ? 23 : 32;
  const x = margin + (idx / (total - 1)) * (100 - 2 * margin);
  return { x, y };
}

// Place starters from the API's real formation grid (row = line from keeper to
// attack, col = slot across the line), reproducing the exact shape (4-2-3-1 etc).
function buildGridPositions(players: Player[], side: 'top' | 'bottom'): Array<{ player: Player; x: number; y: number }> {
  const starters = players.filter(p => p.grid_row != null && p.grid_col != null);
  const maxRow = Math.max(...starters.map(p => p.grid_row as number));
  const colsByRow: Record<number, number[]> = {};
  starters.forEach(p => { (colsByRow[p.grid_row as number] ??= []).push(p.grid_col as number); });
  const margin = 12;
  return starters.map(p => {
    const row = p.grid_row as number, col = p.grid_col as number;
    const rowFrac = maxRow > 1 ? (row - 1) / (maxRow - 1) : 0;
    const y = side === 'bottom' ? 92 - rowFrac * 40 : 8 + rowFrac * 40;
    const maxCol = Math.max(...colsByRow[row]);
    const colFrac = maxCol > 1 ? (col - 1) / (maxCol - 1) : 0.5;
    let x = margin + colFrac * (100 - 2 * margin);
    if (side === 'top') x = 100 - x;  // mirror so both shapes face the centre line
    return { player: p, x, y };
  });
}

function buildTokenPositions(players: Player[], side: 'top' | 'bottom'): Array<{ player: Player; x: number; y: number }> {
  if (players.some(p => p.grid_row != null && p.grid_col != null)) {
    return buildGridPositions(players, side);
  }
  const byRole: Record<string, Player[]> = {};
  for (const p of players) {
    const r = p.role.toLowerCase();
    if (!byRole[r]) byRole[r] = [];
    byRole[r].push(p);
  }
  const result: Array<{ player: Player; x: number; y: number }> = [];
  for (const role of ROLE_ORDER) {
    const group = byRole[role] ?? [];
    group.forEach((p, i) => {
      result.push({ player: p, ...getPitchPosition(role, i, group.length, side) });
    });
  }
  return result;
}

const STEP_META = [
  { title: 'Call the score.' },
  { title: 'Who shows up?' },
];

function TeamCrest({ team, size = 'md' }: { team: { short_name: string; name: string }; size?: 'sm' | 'md' | 'lg' }) {
  const dim = size === 'lg' ? 'h-14 w-14 text-lg' : size === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-11 w-11 text-sm';
  const flagUrl = getTeamLogoUrl(team.short_name);
  return (
    <div className={cn('grid place-items-center rounded-full shrink-0 bg-muted overflow-hidden', dim)}>
      {flagUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={flagUrl} alt={team.name} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
      ) : (
        <span className={cn('font-heading font-bold tracking-wide text-muted-foreground', size === 'lg' ? 'text-lg' : size === 'sm' ? 'text-[11px]' : 'text-sm')}>
          {team.short_name.slice(0, 3).toUpperCase()}
        </span>
      )}
    </div>
  );
}

function PitchSVG() {
  return (
    <svg viewBox="0 0 360 560" className="absolute inset-0 w-full h-full" aria-hidden>
      {/* Base */}
      <rect width="360" height="560" fill="#1a3a24" rx="8" />
      {/* Alternating grass stripes */}
      {[0, 1, 2, 3, 4, 5].map(i => (
        <rect key={i} x="0" y={i * 94} width="360" height="47" fill="rgba(255,255,255,0.02)" />
      ))}
      {/* Boundary */}
      <rect x="10" y="10" width="340" height="540" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.5" rx="3" />
      {/* Halfway separator — subtle shaded band + brighter line to divide the two teams */}
      <rect x="10" y="270" width="340" height="20" fill="rgba(0,0,0,0.18)" />
      <line x1="10" y1="280" x2="350" y2="280" stroke="rgba(255,255,255,0.32)" strokeWidth="1.8" />
      {/* Center circle */}
      <circle cx="180" cy="280" r="46" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      <circle cx="180" cy="280" r="2.5" fill="rgba(255,255,255,0.25)" />
      {/* Top penalty area */}
      <rect x="87" y="10" width="186" height="64" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      {/* Top 6-yard box */}
      <rect x="127" y="10" width="106" height="25" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      {/* Bottom penalty area */}
      <rect x="87" y="486" width="186" height="64" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      {/* Bottom 6-yard box */}
      <rect x="127" y="525" width="106" height="25" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      {/* Goal nets — top (team2 amber tint), bottom (team1 primary tint) */}
      <rect x="127" y="5" width="106" height="8" fill="rgba(251,191,36,0.3)" rx="2" />
      <rect x="127" y="547" width="106" height="8" fill="rgba(99,102,241,0.35)" rx="2" />
      {/* Corner arcs */}
      <path d="M10,10 A8,8 0 0,1 18,18" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      <path d="M350,10 A8,8 0 0,0 342,18" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      <path d="M10,550 A8,8 0 0,0 18,542" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      <path d="M350,550 A8,8 0 0,1 342,542" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
    </svg>
  );
}

function TeamFlag({ shortName, name, className }: { shortName: string; name: string; className?: string }) {
  const flagUrl = getTeamLogoUrl(shortName);
  if (!flagUrl) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={flagUrl} alt={name} className={cn('inline-block rounded-sm object-cover', className)} onError={(e) => { e.currentTarget.style.display = 'none'; }} />;
}

function WinnerChip({
  score, team1, team2, isKnockout, advanceWinner,
}: {
  score: { a: number; b: number };
  team1: { short_name: string; name: string };
  team2: { short_name: string; name: string };
  isKnockout: boolean;
  advanceWinner: 'team1' | 'team2' | null;
}) {
  let content: React.ReactNode;
  let cls: string;
  if (score.a > score.b) {
    content = <><TeamFlag shortName={team1.short_name} name={team1.name} className="h-3.5 w-5 mr-1" />{team1.name} win</>;
    cls = 'bg-primary/15 text-primary';
  } else if (score.b > score.a) {
    content = <><TeamFlag shortName={team2.short_name} name={team2.name} className="h-3.5 w-5 mr-1" />{team2.name} win</>;
    cls = 'bg-amber-500/15 text-amber-500';
  } else if (isKnockout && advanceWinner) {
    const adv = advanceWinner === 'team2' ? team2 : team1;
    content = <>Draw · <TeamFlag shortName={adv.short_name} name={adv.name} className="h-3.5 w-5 mx-1" />{adv.name} on pens</>;
    cls = 'bg-muted text-muted-foreground';
  } else {
    content = isKnockout ? 'Draw · goes to ET' : 'Draw';
    cls = 'bg-muted text-muted-foreground';
  }
  return (
    <div className={cn('flex items-center justify-center rounded-full px-4 py-1.5 font-heading text-xs font-bold transition-all', cls)}>
      {content}
    </div>
  );
}

function ScoreColumn({ label, flagUrl, value, onStep }: { label: string; flagUrl?: string; value: number; onStep: (delta: number) => void }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex items-center gap-1.5 rounded bg-muted/60 px-2 py-1">
        {flagUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={flagUrl} alt={label} className="h-3.5 w-5 shrink-0 rounded-[2px] object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
        )}
        <span className="font-heading text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>
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

function ScorePointsHint({ isKnockout }: { isKnockout: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
      <span className="rounded bg-primary/10 px-2 py-0.5 font-heading text-[10px] font-semibold text-primary">Result +5</span>
      <span className="text-[9px] text-muted-foreground/40">·</span>
      <span className="rounded bg-primary/10 px-2 py-0.5 font-heading text-[10px] font-semibold text-primary">One score +5</span>
      <span className="text-[9px] text-muted-foreground/40">·</span>
      <span className="rounded bg-primary/10 px-2 py-0.5 font-heading text-[10px] font-semibold text-primary">Both +10</span>
      {isKnockout && (
        <>
          <span className="text-[9px] text-muted-foreground/40">·</span>
          <span className="rounded bg-amber-500/15 px-2 py-0.5 font-heading text-[10px] font-bold text-amber-500">⚡ 2× knockout</span>
        </>
      )}
    </div>
  );
}

const PLAYER_POINTS_ROWS = [
  { pos: 'FWD', goal: '+10', assist: '+5',  cs: '—' },
  { pos: 'MID', goal: '+15', assist: '+10', cs: '+3' },
  { pos: 'DEF', goal: '+25', assist: '+12', cs: '+6' },
  { pos: 'GK',  goal: '+25', assist: '+12', cs: '+6' },
];

function PlayerPointsHint({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
        aria-expanded={open}
      >
        <Info className="h-3.5 w-3.5 shrink-0" />
        <span className="font-heading text-[10px] font-semibold uppercase tracking-[0.15em]">
          {open ? 'Hide scoring' : 'How picks score'}
        </span>
      </button>
      {open && (
        <div className="mt-2 rounded-xl border border-border bg-card/60 px-3 py-2.5 space-y-2">
          <div className="grid grid-cols-4 gap-x-2 gap-y-1">
            <span className="font-heading text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60">Pos</span>
            <span className="font-heading text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60 text-right">Goal</span>
            <span className="font-heading text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60 text-right">Assist</span>
            <span className="font-heading text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60 text-right">CS</span>
            {PLAYER_POINTS_ROWS.map(row => (
              <>
                <span key={`${row.pos}-pos`} className="font-heading text-[11px] font-bold text-foreground">{row.pos}</span>
                <span key={`${row.pos}-goal`} className="font-heading text-[11px] tabular-nums text-primary text-right">{row.goal}</span>
                <span key={`${row.pos}-assist`} className="font-heading text-[11px] tabular-nums text-primary text-right">{row.assist}</span>
                <span key={`${row.pos}-cs`} className={cn('font-heading text-[11px] tabular-nums text-right', row.cs === '—' ? 'text-muted-foreground/40' : 'text-primary')}>{row.cs}</span>
              </>
            ))}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 pt-1 border-t border-border">
            <span className="font-heading text-[9px] text-muted-foreground">+3 appearance (30+ min)</span>
            <span className="font-heading text-[9px] text-muted-foreground">−3 red card / own goal</span>
            <span className="font-heading text-[9px] text-muted-foreground">GK: +5 pen save</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function FootballPredictFlow({ matchId, matchData }: { matchId: number; matchData: MatchPlayersResponse }) {
  const router = useRouter();
  const { team_1, team_2, stage } = matchData;
  const isKnockout = !!stage && KNOCKOUT_STAGES.has(stage);
  const stageLabel = (stage && STAGE_LABELS[stage]) || 'World Cup';

  const [step, setStep] = useState(0); // 0 = scoreline, 1 = pitch/players
  const [slideDir, setSlideDir] = useState<'left' | 'right' | null>(null);
  const [advanceWinner, setAdvanceWinner] = useState<'team1' | 'team2' | null>(null);
  const [scorers, setScorers] = useState<number[]>([]);
  const [score, setScore] = useState<{ a: number; b: number }>({ a: 1, b: 0 });
  const [isEditing, setIsEditing] = useState(false);
  const [isLoadingPick, setIsLoadingPick] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [showPointsHint, setShowPointsHint] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const touchStartX = useRef(0);
  const touchStartY = useRef(0);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let active = true;
    getMyFootballPredictionDetail(matchId)
      .then(existing => {
        if (!active || !existing) return;
        setScore({ a: existing.team1_goals, b: existing.team2_goals });
        setScorers(existing.player_picks.map(p => p.player.id));
        if (existing.advance_winner) {
          setAdvanceWinner(existing.advance_winner.id === team_1.id ? 'team1' : 'team2');
        }
        setIsEditing(true);
      })
      .catch(() => {/* no existing prediction is fine */})
      .finally(() => { if (active) setIsLoadingPick(false); });
    return () => { active = false; };
  }, [matchId, team_1.id]);

  const isTeam1Player = useCallback((p: Player) => p.team_id === team_1.id, [team_1.id]);

  const playerById = useMemo(() => {
    const m = new Map<number, Player>();
    [...matchData.team_1_players, ...matchData.team_2_players].forEach(p => m.set(p.id, p));
    return m;
  }, [matchData.team_1_players, matchData.team_2_players]);

  const { starters: starters1, subs: subs1 } = useMemo(() => layoutPlayers(matchData.team_1_players), [matchData.team_1_players]);
  const { starters: starters2, subs: subs2 } = useMemo(() => layoutPlayers(matchData.team_2_players), [matchData.team_2_players]);
  const team1Tokens = useMemo(() => buildTokenPositions(starters1, 'bottom'), [starters1]);
  const team2Tokens = useMemo(() => buildTokenPositions(starters2, 'top'), [starters2]);

  const changeScore = (side: 'a' | 'b', delta: number) => {
    setScore(prev => ({ ...prev, [side]: Math.max(0, Math.min(MAX_GOALS, prev[side] + delta)) }));
  };
  const setQuickScore = (a: number, b: number) => setScore({ a, b });

  const toggleScorer = (id: number) => {
    setScorers(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  };

  const isDraw = score.a === score.b;
  const canProceed = step === 0
    ? (!isKnockout || !isDraw || !!advanceWinner)
    : scorers.length === 3;

  const handleSubmit = useCallback(async () => {
    setError('');
    if (scorers.length !== 3) {
      setError('Pick three players first.');
      setStep(1);
      return;
    }
    const advanceWinnerId = isKnockout && isDraw
      ? (advanceWinner === 'team2' ? team_2.id : team_1.id)
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
  }, [scorers, score, isKnockout, isDraw, advanceWinner, team_1.id, team_2.id, matchId]);

  const onNext = () => {
    if (step < 1) { setSlideDir('left'); setStep(1); return; }
    handleSubmit();
  };
  const onBack = () => {
    if (step > 0) { setSlideDir('right'); setStep(step - 1); }
    else router.push('/predictions');
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  };
  const handleTouchEnd = (e: React.TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    const dy = e.changedTouches[0].clientY - touchStartY.current;
    // Only fire on clearly horizontal swipes (horizontal > vertical * 1.5, at least 48px)
    if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    if (dx < 0 && canProceed) onNext();
    else if (dx > 0) onBack();
  };

  const resultText = (() => {
    if (score.a > score.b) return `${team_1.name} win`;
    if (score.b > score.a) return `${team_2.name} win`;
    if (isKnockout) {
      const adv = advanceWinner === 'team2' ? team_2 : team_1;
      return `Draw · ${adv.name} on pens`;
    }
    return 'Draw';
  })();

  const nextLabel = step === 0
    ? 'Next: pick scorers →'
    : (scorers.length === 3
        ? (isEditing ? 'Update picks' : 'Lock in picks')
        : `Pick ${3 - scorers.length} more`);

  const countdown = formatCountdown(matchData.start_time, now);

  const renderSub = (p: Player) => {
    const selected = scorers.includes(p.id);
    const full = scorers.length >= 3 && !selected;
    const tc = teamColors(isTeam1Player(p));
    return (
      <button
        type="button"
        disabled={full}
        onClick={() => toggleScorer(p.id)}
        className={cn(
          'flex flex-col items-center gap-1.5 rounded-xl border px-2 py-3 transition-all',
          selected ? tc.border : 'border-transparent active:scale-[0.98]',
          full && 'opacity-45',
        )}
        aria-label={p.name}
      >
        <div className="relative">
          <div className={cn(
            'grid h-12 w-12 place-items-center rounded-full text-sm font-bold transition-all',
            selected ? tc.fill : 'bg-muted text-muted-foreground',
            selected && 'ring-2 ring-white',
          )}>
            {getInitials(p.name)}
          </div>
          {selected && (
            <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-white text-black shadow">
              <Check className="h-2.5 w-2.5" strokeWidth={3} />
            </span>
          )}
        </div>
        <div className="text-center">
          <div className="max-w-[8rem] truncate font-heading text-[13px] font-bold leading-tight">{shortName(p.name)}</div>
          <div className="text-[10px] text-muted-foreground">{positionName(p.role)}</div>
        </div>
      </button>
    );
  };

  return (
    <div
      className="flex flex-col mx-auto max-w-[430px]"
      style={{ height: 'calc(100dvh - 56px - 64px)' }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* ── Match stub (inline) ── */}
      <div className="flex-shrink-0 px-4 pt-2 pb-2.5 border-b border-border bg-gradient-to-b from-primary/5 to-background space-y-1.5">
        {/* Meta row — context before content */}
        <div className="flex items-center gap-2">
          <span className="font-heading text-[10px] uppercase tracking-wider text-muted-foreground/60">{stageLabel}</span>
          {isKnockout && (
            <span className="rounded bg-amber-500/15 px-1 py-px font-heading text-[9px] font-bold text-amber-500">2×</span>
          )}
          <div className="flex-1" />
          <div className="flex flex-col items-end gap-0.5">
            <span className="font-heading text-[9px] uppercase tracking-wider text-muted-foreground/60">kickoff</span>
            <div className="flex items-center gap-1 text-primary">
              <Clock className="h-3 w-3" />
              <span className="font-heading text-xs font-bold tabular-nums">{countdown}</span>
            </div>
          </div>
        </div>
        {/* Teams row */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.push('/predictions')}
            className="shrink-0 text-muted-foreground hover:text-foreground"
            aria-label="Back to predictions"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-1.5 leading-none min-w-0 flex-1">
            <TeamFlag shortName={team_1.short_name} name={team_1.name} className="h-3.5 w-5 shrink-0 rounded-[2px]" />
            <span className="font-heading text-sm font-bold">{team_1.short_name}</span>
            {team_1.fifa_ranking && (
              <span className="font-heading text-[9px] text-muted-foreground/50">#{team_1.fifa_ranking}</span>
            )}
            <span className="font-heading text-[10px] text-muted-foreground/40 shrink-0">vs</span>
            {team_2.fifa_ranking && (
              <span className="font-heading text-[9px] text-muted-foreground/50">#{team_2.fifa_ranking}</span>
            )}
            <span className="font-heading text-sm font-bold">{team_2.short_name}</span>
            <TeamFlag shortName={team_2.short_name} name={team_2.name} className="h-3.5 w-5 shrink-0 rounded-[2px]" />
          </div>
        </div>
      </div>

      {/* ── Step pills + meta ── */}
      <div className="flex-shrink-0 px-5 pt-3">
        <div className="flex items-center gap-1.5">
          {[0, 1].map(i => (
            <div
              key={i}
              className={cn(
                'h-1 flex-1 rounded-full transition-all duration-300',
                i <= step ? 'bg-primary' : 'bg-muted',
              )}
            />
          ))}
          <span className="shrink-0 font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            {String(step + 1).padStart(2, '0')} / 02
          </span>
        </div>
        <h2 className="mt-2 font-heading text-2xl font-bold tracking-tight">{STEP_META[step].title}</h2>
        {step === 0 && <ScorePointsHint isKnockout={isKnockout} />}
      </div>

      {/* ── Panels ── */}
      <div
        key={step}
        className={cn(
          'flex-1 overflow-y-auto px-5 pb-5 pt-3',
          slideDir === 'left' && 'animate-slide-in-left',
          slideDir === 'right' && 'animate-slide-in-right',
        )}
        onAnimationEnd={() => setSlideDir(null)}
      >

        {/* ── Step 0: Scoreline ── */}
        {step === 0 && isLoadingPick && (
          <div className="flex-1 flex items-center justify-center py-16">
            <div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        )}
        {step === 0 && !isLoadingPick && (
          <div className="space-y-4">
            <WinnerChip
              score={score}
              team1={team_1}
              team2={team_2}
              isKnockout={isKnockout}
              advanceWinner={advanceWinner}
            />

            <div className="rounded-2xl border border-border bg-card/60 px-4 py-7">
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
                <ScoreColumn label={team_1.name} flagUrl={getTeamLogoUrl(team_1.short_name)} value={score.a} onStep={d => changeScore('a', d)} />
                <span className="font-heading text-4xl font-medium text-muted-foreground/40">–</span>
                <ScoreColumn label={team_2.name} flagUrl={getTeamLogoUrl(team_2.short_name)} value={score.b} onStep={d => changeScore('b', d)} />
              </div>
            </div>

            {/* Knockout draw: advance winner picker */}
            {isKnockout && isDraw && (
              <div>
                <p className="mb-2 text-center text-xs text-muted-foreground">
                  It&apos;s level — who goes through on pens?
                </p>
                <div className="flex gap-2">
                  {([team_1, team_2] as const).map(t => {
                    const key = t.id === team_1.id ? 'team1' : 'team2' as const;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setAdvanceWinner(key)}
                        className={cn(
                          'flex-1 rounded-xl border-2 py-3 font-heading text-sm font-bold transition-all',
                          advanceWinner === key
                            ? 'border-primary bg-primary/10 text-foreground'
                            : 'border-border text-muted-foreground active:scale-[0.98]',
                        )}
                      >
                        {t.name} on pens
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div>
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
          </div>
        )}

        {/* ── Step 1: Pitch map ── */}
        {step === 1 && (
          <div>
            <PlayerPointsHint open={showPointsHint} onToggle={() => setShowPointsHint(v => !v)} />
            {/* Tray */}
            <div className="flex gap-2 mb-3">
              {[0, 1, 2].map(i => {
                const p = scorers[i] != null ? playerById.get(scorers[i]) : undefined;
                const tc = p ? teamColors(isTeam1Player(p)) : null;
                return (
                  <div
                    key={i}
                    className={cn(
                      'flex-1 flex items-center gap-1.5 rounded-xl border px-2 py-2 transition-all min-w-0',
                      tc ? tc.border : 'border-dashed border-border bg-background/40',
                    )}
                  >
                    <div className={cn(
                      'grid h-7 w-7 shrink-0 place-items-center rounded-full text-[10px] font-bold',
                      tc ? tc.fill : 'bg-muted text-muted-foreground',
                    )}>
                      {p ? getInitials(p.name) : <span className="text-[9px] font-semibold">{i + 1}</span>}
                    </div>
                    {p ? (
                      <span className="truncate font-heading text-xs font-bold leading-tight">{shortName(p.name)}</span>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">{i === 0 ? 'Tap player' : `Slot ${i + 1}`}</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Lineup status */}
            <div className="mb-2 text-center text-[10px] font-heading uppercase tracking-[0.18em]">
              {matchData.lineup_announced ? (
                <span className="text-primary">
                  Confirmed XI
                  {(matchData.team_1_formation || matchData.team_2_formation) && (
                    <span className="text-muted-foreground"> · {matchData.team_1_formation ?? '—'} v {matchData.team_2_formation ?? '—'}</span>
                  )}
                </span>
              ) : (
                <span className="text-muted-foreground">Predicted XI · lineup not announced yet</span>
              )}
            </div>

            {/* Pitch */}
            <div className="relative w-full rounded-xl overflow-hidden" style={{ aspectRatio: '360/560' }}>
              <PitchSVG />

              {/* Team 2 tokens — top half, attacks down */}
              {team2Tokens.map(({ player, x, y }) => {
                const selected = scorers.includes(player.id);
                const full = scorers.length >= 3 && !selected;
                const isGK = player.role.toLowerCase() === 'goalkeeper';
                return (
                  <button
                    key={player.id}
                    type="button"
                    disabled={full}
                    onClick={() => toggleScorer(player.id)}
                    style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
                    className="absolute flex flex-col items-center gap-1 z-10"
                    aria-label={player.name}
                  >
                    <div className="relative">
                      <div className={cn(
                        'w-9 h-9 rounded-full flex items-center justify-center text-[10px] font-bold transition-all',
                        'bg-amber-500 text-black',
                        selected && 'ring-2 ring-white scale-110 shadow-lg',
                        (full || isGK) && 'opacity-50',
                      )}>
                        {getInitials(player.name)}
                      </div>
                      {selected && (
                        <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-white text-black shadow">
                          <Check className="h-2.5 w-2.5" strokeWidth={3} />
                        </span>
                      )}
                    </div>
                    <span className={cn(
                      'max-w-[68px] truncate rounded px-1.5 py-0.5 text-[9px] font-bold leading-tight text-white shadow-sm',
                      selected ? 'bg-black/85' : 'bg-black/55',
                    )}>
                      {shortName(player.name)}
                    </span>
                  </button>
                );
              })}

              {/* Team 1 tokens — bottom half, attacks up */}
              {team1Tokens.map(({ player, x, y }) => {
                const selected = scorers.includes(player.id);
                const full = scorers.length >= 3 && !selected;
                const isGK = player.role.toLowerCase() === 'goalkeeper';
                return (
                  <button
                    key={player.id}
                    type="button"
                    disabled={full}
                    onClick={() => toggleScorer(player.id)}
                    style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}
                    className="absolute flex flex-col items-center gap-1 z-10"
                    aria-label={player.name}
                  >
                    <div className="relative">
                      <div className={cn(
                        'w-9 h-9 rounded-full flex items-center justify-center text-[10px] font-bold transition-all',
                        'bg-primary text-primary-foreground',
                        selected && 'ring-2 ring-white scale-110 shadow-lg',
                        (full || isGK) && 'opacity-50',
                      )}>
                        {getInitials(player.name)}
                      </div>
                      {selected && (
                        <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-white text-black shadow">
                          <Check className="h-2.5 w-2.5" strokeWidth={3} />
                        </span>
                      )}
                    </div>
                    <span className={cn(
                      'max-w-[68px] truncate rounded px-1.5 py-0.5 text-[9px] font-bold leading-tight text-white shadow-sm',
                      selected ? 'bg-black/85' : 'bg-black/55',
                    )}>
                      {shortName(player.name)}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Subs — paired two-column layout */}
            {(subs1.length > 0 || subs2.length > 0) && (
              <div className="mt-4">
                <div className="mb-2 flex items-center gap-2">
                  <span className="h-px flex-1 bg-gradient-to-l from-border to-transparent" />
                  <span className="font-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Substitutes</span>
                  <span className="h-px flex-1 bg-gradient-to-r from-border to-transparent" />
                </div>
                <div className="mb-1.5 flex items-center justify-between px-2">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-primary" />
                    <span className="font-heading text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{team_1.short_name}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-heading text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{team_2.short_name}</span>
                    <span className="h-2 w-2 rounded-full bg-amber-500" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                  {Array.from({ length: Math.max(subs1.length, subs2.length) }).map((_, i) => {
                    const left = subs1[i];
                    const right = subs2[i];
                    return (
                      <Fragment key={i}>
                        {left ? renderSub(left) : <span />}
                        {right ? renderSub(right) : <span />}
                      </Fragment>
                    );
                  })}
                </div>
              </div>
            )}
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
          {step === 0 && !isSubmitting && <ArrowRight className="h-4 w-4" />}
        </Button>
      </div>

      {error && (
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
            <DialogDescription>{team_1.name} vs {team_2.name} · {stageLabel}</DialogDescription>
          </DialogHeader>
          <div className="divide-y divide-border rounded-lg border border-border bg-muted/30 text-sm">
            <SummaryRow label="Result" value={`${resultText} · ${score.a}–${score.b}`} />
            <SummaryRow
              label="Players"
              value={scorers.map(id => shortName(playerById.get(id)?.name ?? '')).filter(Boolean).join(' · ') || '—'}
            />
          </div>
          <div className="flex flex-col gap-3">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(
                `⚽ ${team_1.name} vs ${team_2.name} — I've locked my picks!\nThink you can do better? ${process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app'}/predictions`,
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
