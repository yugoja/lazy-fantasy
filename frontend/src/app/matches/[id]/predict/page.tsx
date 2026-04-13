'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, getMyPredictions, submitPrediction, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ArrowLeft, Trophy, Target, Star, CheckCircle2, Clock, Pencil, ChevronRight } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';

interface Player {
  id: number;
  name: string;
  team_id: number;
  role: string;
  played_last_match: boolean;
}

interface Team {
  id: number;
  name: string;
  short_name: string;
}

interface MatchData {
  match_id: number;
  team_1: Team;
  team_2: Team;
  team_1_players: Player[];
  team_2_players: Player[];
  lineup_announced: boolean;
  start_time: string;
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
}

function getLastName(name: string) {
  return name.split(' ').pop() ?? name;
}

function formatCountdown(startTime: string): string {
  const diff = new Date(startTime).getTime() - Date.now();
  if (diff <= 0) return 'soon';
  const totalMins = Math.floor(diff / 60000);
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h`;
  return `${mins}m`;
}

function getRoleLabel(role: string) {
  const map: Record<string, string> = {
    batsman: 'BAT', batter: 'BAT',
    bowler: 'BOWL',
    all_rounder: 'AR', allrounder: 'AR', 'all-rounder': 'AR',
    wicket_keeper: 'WK', wicketkeeper: 'WK', 'wk-batter': 'WK',
  };
  return map[role.toLowerCase()] ?? role.substring(0, 4).toUpperCase();
}


function isBatter(role: string) {
  return ['batsman', 'batter', 'wicketkeeper', 'wk-batter', 'all-rounder', 'all_rounder', 'allrounder'].includes(role.toLowerCase());
}

function isBowler(role: string) {
  return ['bowler', 'all-rounder', 'all_rounder', 'allrounder'].includes(role.toLowerCase());
}

function buildShareText(team1: string, team2: string, startTime: string): string {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
  return [
    `🏏 ${team1} vs ${team2} — predictions are open!`,
    `I've locked in my call. Have you? ⏰`,
    `Closes in ${formatCountdown(startTime)} 👇`,
    `${appUrl}/predictions`,
  ].join('\n');
}

// Total prediction steps (not counting summary)
const PREDICTION_STEPS = 6;

function PlayerGrid({
  players,
  selectedId,
  onSelect,
  lineupAnnounced,
}: {
  players: Player[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  lineupAnnounced: boolean;
}) {
  // Sort: played_last_match=true first
  const sorted = [...players].sort((a, b) => {
    if (a.played_last_match === b.played_last_match) return 0;
    return a.played_last_match ? -1 : 1;
  });

  return (
    <div className="grid grid-cols-3 gap-3">
      {sorted.map((player) => {
        const isSelected = selectedId === player.id;
        return (
          <button
            key={player.id}
            type="button"
            onClick={() => onSelect(player.id)}
            className={cn(
              'relative flex flex-col items-center gap-2 py-4 px-2 rounded-2xl border-2 transition-all duration-150',
              isSelected
                ? 'border-primary bg-primary/10'
                : 'border-border bg-card/60 active:scale-95'
            )}
          >
            {/* Green dot indicator for last match players */}
            {!lineupAnnounced && player.played_last_match && (
              <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-green-500 ring-1 ring-white" title="Played last match" />
            )}

            <div className={cn(
              'h-11 w-11 rounded-full flex items-center justify-center text-sm font-bold transition-colors',
              isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
            )}>
              {isSelected ? <CheckCircle2 className="h-5 w-5" /> : getInitials(player.name)}
            </div>

            <div className="flex flex-col items-center gap-0.5 w-full">
              <div className="flex flex-col items-center gap-0.5 w-full">
                {player.name.split(' ').map((namePart, i) => (
                  <span key={i} className="text-sm font-semibold truncate w-full text-center leading-tight">
                    {namePart}
                  </span>
                ))}
              </div>
              <span className={cn(
                'text-[10px] font-bold tracking-widest uppercase',
                isSelected ? 'text-primary' : 'text-muted-foreground'
              )}>
                {getRoleLabel(player.role)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

export default function PredictPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const matchId = Number(params.id);

  const [matchData, setMatchData] = useState<MatchData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0–5 = picks, 6 = summary

  const [winnerId, setWinnerId] = useState<number | null>(null);
  const [mostRunsTeam1Id, setMostRunsTeam1Id] = useState<number | null>(null);
  const [mostRunsTeam2Id, setMostRunsTeam2Id] = useState<number | null>(null);
  const [mostWicketsTeam1Id, setMostWicketsTeam1Id] = useState<number | null>(null);
  const [mostWicketsTeam2Id, setMostWicketsTeam2Id] = useState<number | null>(null);
  const [pomId, setPomId] = useState<number | null>(null);

  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const advance = useCallback(() => {
    setCurrentStep(s => Math.min(s + 1, PREDICTION_STEPS));
  }, []);

  const autoAdvance = useCallback(() => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
    advanceTimer.current = setTimeout(advance, 420);
  }, [advance]);

  useEffect(() => () => { if (advanceTimer.current) clearTimeout(advanceTimer.current); }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (matchId && isAuthenticated) loadMatchData();
  }, [matchId, isAuthenticated]);

  const loadMatchData = async () => {
    try {
      const [matchResult, predictionsResult] = await Promise.allSettled([
        getMatchPlayers(matchId),
        getMyPredictions(),
      ]);
      if (matchResult.status === 'fulfilled') {
        const data = matchResult.value;
        if (new Date(data.start_time) <= new Date()) { router.push('/predictions'); return; }
        setMatchData(data);
      } else {
        setError('Failed to load match data');
      }
      if (predictionsResult.status === 'fulfilled') {
        const existing = predictionsResult.value.find(p => p.match_id === matchId);
        if (existing) {
          setWinnerId(existing.predicted_winner_id);
          setMostRunsTeam1Id(existing.predicted_most_runs_team1_player_id);
          setMostRunsTeam2Id(existing.predicted_most_runs_team2_player_id);
          setMostWicketsTeam1Id(existing.predicted_most_wickets_team1_player_id);
          setMostWicketsTeam2Id(existing.predicted_most_wickets_team2_player_id);
          setPomId(existing.predicted_pom_player_id);
          setIsEditing(true);
          setCurrentStep(PREDICTION_STEPS); // jump straight to summary when editing
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load match data');
    } finally {
      setIsLoading(false);
    }
  };

  const picks = [winnerId, mostRunsTeam1Id, mostRunsTeam2Id, mostWicketsTeam1Id, mostWicketsTeam2Id, pomId];
  const filledCount = picks.filter(Boolean).length;

  const handleSubmit = async () => {
    setError('');
    if (!winnerId || !mostRunsTeam1Id || !mostRunsTeam2Id || !mostWicketsTeam1Id || !mostWicketsTeam2Id || !pomId) {
      setError('Please fill in all predictions');
      return;
    }
    setIsSubmitting(true);
    try {
      await submitPrediction({
        match_id: matchId,
        predicted_winner_id: winnerId,
        predicted_most_runs_team1_player_id: mostRunsTeam1Id,
        predicted_most_runs_team2_player_id: mostRunsTeam2Id,
        predicted_most_wickets_team1_player_id: mostWicketsTeam1Id,
        predicted_most_wickets_team2_player_id: mostWicketsTeam2Id,
        predicted_pom_player_id: pomId,
      });
      setShowSuccess(true);
      window.dispatchEvent(new Event('prediction-submitted'));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to submit prediction');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!matchData) {
    return (
      <div className="container-mobile py-6">
        <Card className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error || 'Match not found'}</p>
          <Link href="/predictions"><Button variant="outline" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back</Button></Link>
        </Card>
      </div>
    );
  }

  const allPlayers = [...matchData.team_1_players, ...matchData.team_2_players];
  const t1Batters = matchData.team_1_players.filter(p => isBatter(p.role));
  const t2Batters = matchData.team_2_players.filter(p => isBatter(p.role));
  const t1Bowlers = matchData.team_1_players.filter(p => isBowler(p.role));
  const t2Bowlers = matchData.team_2_players.filter(p => isBowler(p.role));

  const findPlayer = (id: number | null, pool: Player[]) => pool.find(p => p.id === id);
  const winnerTeam = winnerId ? (winnerId === matchData.team_1.id ? matchData.team_1 : matchData.team_2) : null;
  const runsT1 = findPlayer(mostRunsTeam1Id, matchData.team_1_players);
  const runsT2 = findPlayer(mostRunsTeam2Id, matchData.team_2_players);
  const wktsT1 = findPlayer(mostWicketsTeam1Id, matchData.team_1_players);
  const wktsT2 = findPlayer(mostWicketsTeam2Id, matchData.team_2_players);
  const pomPlayer = findPlayer(pomId, allPlayers);

  const isSummary = currentStep === PREDICTION_STEPS;

  // Step config
  const stepConfig = [
    {
      num: 1, label: 'Match Winner', sublabel: null, teamShortName: null, winnerTeamShortName: winnerTeam?.short_name ?? null,
      icon: <Trophy className="h-4 w-4" />, pts: 10,
      currentValue: winnerTeam?.short_name ?? null,
    },
    {
      num: 2, label: 'Top Batsman', sublabel: matchData.team_1.short_name, teamShortName: matchData.team_1.short_name, winnerTeamShortName: null,
      icon: <Target className="h-4 w-4" />, pts: 20,
      currentValue: runsT1 ? runsT1.name : null,
    },
    {
      num: 3, label: 'Top Batsman', sublabel: matchData.team_2.short_name, teamShortName: matchData.team_2.short_name, winnerTeamShortName: null,
      icon: <Target className="h-4 w-4" />, pts: 20,
      currentValue: runsT2 ? runsT2.name : null,
    },
    {
      num: 4, label: 'Top Bowler', sublabel: matchData.team_1.short_name, teamShortName: matchData.team_1.short_name, winnerTeamShortName: null,
      icon: <Target className="h-4 w-4" />, pts: 20,
      currentValue: wktsT1 ? wktsT1.name : null,
    },
    {
      num: 5, label: 'Top Bowler', sublabel: matchData.team_2.short_name, teamShortName: matchData.team_2.short_name, winnerTeamShortName: null,
      icon: <Target className="h-4 w-4" />, pts: 20,
      currentValue: wktsT2 ? wktsT2.name : null,
    },
    {
      num: 6, label: 'Man of the Match', sublabel: null, teamShortName: null, winnerTeamShortName: null,
      icon: <Star className="h-4 w-4" />, pts: 50,
      currentValue: pomPlayer ? pomPlayer.name : null,
    },
  ];

  const activeStep = stepConfig[currentStep];

  return (
    <div className="flex flex-col mx-auto max-w-[430px]" style={{ height: 'calc(100dvh - 56px - 64px)' }}>

      {/* ── Sticky header ── */}
      <div className="flex-shrink-0 px-4 pt-3 pb-3 border-b border-border bg-background">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => currentStep > 0 ? setCurrentStep(s => s - 1) : router.push('/predictions')}
              className="shrink-0 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h1 className="text-base font-bold">
                  {matchData.team_1.short_name} vs {matchData.team_2.short_name}
                </h1>
                {matchData.lineup_announced && (
                  <Badge className="bg-green-600/20 text-green-400 border-green-600/30 text-[10px] py-0">XI</Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {new Date(matchData.start_time).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0 px-2 py-1 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
            <Clock className="h-3 w-3" />
            {formatCountdown(matchData.start_time)}
          </div>
        </div>

        {/* Step progress dots */}
        {!isSummary && (
          <div className="flex items-center gap-1.5 mt-3">
            {stepConfig.map((s, i) => (
              <div
                key={i}
                className={cn(
                  'h-1 rounded-full transition-all duration-300',
                  i < currentStep
                    ? 'bg-primary flex-1'
                    : i === currentStep
                    ? 'bg-primary flex-[2]'
                    : 'bg-muted flex-1'
                )}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Step content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {isSummary ? (
          /* ── Summary ── */
          <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
            <div>
              <h2 className="text-2xl font-bold">Your Picks</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                {filledCount === 6 ? 'All done — ready to lock in.' : `${6 - filledCount} pick${6 - filledCount !== 1 ? 's' : ''} remaining.`}
              </p>
            </div>

            {error && (
              <div className="p-3 rounded-lg border border-destructive/50 bg-destructive/10">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            <div className="rounded-2xl border border-border overflow-hidden divide-y divide-border">
              {stepConfig.map((s, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3.5">
                  {/* Step number */}
                  <div className={cn(
                    'h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
                    s.currentValue ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                  )}>
                    {s.currentValue ? <CheckCircle2 className="h-4 w-4" /> : s.num}
                  </div>

                  {/* Label + value */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider leading-none">
                        {s.label}{s.sublabel ? ` · ${s.sublabel}` : ''}
                      </p>
                      {s.teamShortName && (() => {
                        const logo = getTeamLogoUrl(s.teamShortName);
                        return logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={logo} alt={s.teamShortName} width={14} height={14}
                            className="h-3.5 w-3.5 object-contain opacity-80"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        ) : null;
                      })()}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {s.winnerTeamShortName && (() => {
                        const logo = getTeamLogoUrl(s.winnerTeamShortName);
                        return logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={logo} alt={s.winnerTeamShortName} width={18} height={18}
                            className="h-4.5 w-4.5 object-contain shrink-0"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        ) : null;
                      })()}
                      <p className={cn(
                        'text-base font-semibold truncate',
                        s.currentValue ? 'text-foreground' : 'text-muted-foreground'
                      )}>
                        {s.currentValue ?? '—'}
                      </p>
                    </div>
                  </div>

                  {/* Pts + edit */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground">+{s.pts}</span>
                    <button
                      type="button"
                      onClick={() => setCurrentStep(i)}
                      className="flex items-center gap-0.5 text-xs text-primary font-medium px-2 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors"
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </button>
                  </div>
                </div>
              ))}

              {/* Potential total */}
              <div className="flex items-center justify-between px-4 py-3 bg-primary/5">
                <span className="text-sm text-muted-foreground">Potential total</span>
                <span className="font-bold text-base text-primary">Up to 140 pts</span>
              </div>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={filledCount < 6 || isSubmitting}
              className="w-full"
              size="lg"
            >
              {isSubmitting ? 'Saving...' : isEditing ? 'Update Picks' : 'Lock In Picks'}
            </Button>
          </div>
        ) : (
          /* ── Prediction step ── */
          <>
            {/* Fixed step header */}
            <div key={`header-${currentStep}`} className="flex-shrink-0 relative px-4 pt-5 pb-4 border-b border-border bg-background step-enter overflow-hidden">
              {/* Ghost step number */}
              <div
                aria-hidden
                className="absolute right-1 top-0 text-[100px] font-black select-none pointer-events-none text-muted-foreground/10"
                style={{ lineHeight: 1 }}
              >
                {activeStep.num}
              </div>
              <div className="relative">
                <p className="text-sm text-muted-foreground uppercase tracking-widest font-semibold">
                  Step {activeStep.num} of {PREDICTION_STEPS}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <h2 className="text-2xl font-bold">
                    {activeStep.label}
                    {activeStep.sublabel && (
                      <span className="text-primary"> {activeStep.sublabel}</span>
                    )}
                  </h2>
                  {activeStep.teamShortName && (() => {
                    const logo = getTeamLogoUrl(activeStep.teamShortName);
                    return logo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={logo} alt={activeStep.teamShortName} width={28} height={28}
                        className="h-7 w-7 object-contain"
                        onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                    ) : null;
                  })()}
                </div>
                <div className="flex items-center justify-between mt-1">
                  <p className="text-sm text-muted-foreground">+{activeStep.pts} pts if correct</p>
                  {activeStep.currentValue && (
                    <span className="text-sm text-primary font-medium">✓ {activeStep.currentValue}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Scrollable player grid */}
            <div key={`body-${currentStep}`} className="flex-1 overflow-y-auto px-4 pt-4 pb-4 step-enter">
              {currentStep === 0 && (
                <div className="grid grid-cols-2 gap-4">
                  {[matchData.team_1, matchData.team_2].map((team) => {
                    const isSelected = winnerId === team.id;
                    const logoSrc = getTeamLogoUrl(team.short_name);
                    return (
                      <button
                        key={team.id}
                        type="button"
                        onClick={() => { setWinnerId(team.id); autoAdvance(); }}
                        className={cn(
                          'relative flex flex-col items-center gap-3 py-8 px-4 rounded-2xl border-2 transition-all duration-150',
                          isSelected ? 'border-primary bg-primary/10' : 'border-border bg-card/60 active:scale-95'
                        )}
                      >
                        {isSelected && <CheckCircle2 className="absolute top-3 right-3 h-4 w-4 text-primary" />}
                        {logoSrc && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={logoSrc} alt={team.name} width={48} height={48}
                            className="h-12 w-12 object-contain"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        )}
                        <div>
                          <div className="font-bold text-lg text-center">{team.short_name}</div>
                          <div className="text-sm text-muted-foreground text-center leading-tight mt-0.5">{team.name}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
              {currentStep === 1 && <PlayerGrid players={t1Batters} selectedId={mostRunsTeam1Id} onSelect={(id) => { setMostRunsTeam1Id(id); autoAdvance(); }} lineupAnnounced={matchData?.lineup_announced ?? false} />}
              {currentStep === 2 && <PlayerGrid players={t2Batters} selectedId={mostRunsTeam2Id} onSelect={(id) => { setMostRunsTeam2Id(id); autoAdvance(); }} lineupAnnounced={matchData?.lineup_announced ?? false} />}
              {currentStep === 3 && <PlayerGrid players={t1Bowlers} selectedId={mostWicketsTeam1Id} onSelect={(id) => { setMostWicketsTeam1Id(id); autoAdvance(); }} lineupAnnounced={matchData?.lineup_announced ?? false} />}
              {currentStep === 4 && <PlayerGrid players={t2Bowlers} selectedId={mostWicketsTeam2Id} onSelect={(id) => { setMostWicketsTeam2Id(id); autoAdvance(); }} lineupAnnounced={matchData?.lineup_announced ?? false} />}
              {currentStep === 5 && <PlayerGrid players={allPlayers} selectedId={pomId} onSelect={(id) => { setPomId(id); autoAdvance(); }} lineupAnnounced={matchData?.lineup_announced ?? false} />}

              {/* Next / skip */}
              <div className="mt-5 flex justify-end">
                <button
                  type="button"
                  onClick={advance}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {activeStep.currentValue ? 'Next' : 'Skip'}
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Success Dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent className="sm:max-w-md">
          <div className="flex justify-center mt-2 mb-1">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
              <div className="relative h-16 w-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
            </div>
          </div>
          <DialogHeader className="items-center text-center pb-0">
            <DialogTitle className="text-xl">{isEditing ? 'Picks Updated!' : "You're locked in!"}</DialogTitle>
            <DialogDescription>{matchData.team_1.short_name} vs {matchData.team_2.short_name}</DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border border-border bg-muted/30 divide-y divide-border text-sm">
            {[
              { label: 'Winner', value: winnerTeam?.short_name, pts: 10 },
              { label: `Top Bat · ${matchData.team_1.short_name}`, value: runsT1 ? getLastName(runsT1.name) : '—', pts: 20 },
              { label: `Top Bat · ${matchData.team_2.short_name}`, value: runsT2 ? getLastName(runsT2.name) : '—', pts: 20 },
              { label: `Top Bowl · ${matchData.team_1.short_name}`, value: wktsT1 ? getLastName(wktsT1.name) : '—', pts: 20 },
              { label: `Top Bowl · ${matchData.team_2.short_name}`, value: wktsT2 ? getLastName(wktsT2.name) : '—', pts: 20 },
              { label: 'MOTM', value: pomPlayer ? getLastName(pomPlayer.name) : '—', pts: 50 },
            ].map(row => (
              <div key={row.label} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-xs text-muted-foreground">{row.label}</span>
                <span className="font-semibold text-sm">{row.value}</span>
                <span className="text-[10px] text-muted-foreground">+{row.pts} pts</span>
              </div>
            ))}
            <div className="flex items-center justify-between px-4 py-2.5 bg-primary/5">
              <span className="text-xs text-muted-foreground">Potential total</span>
              <span className="font-bold text-primary">Up to 140 pts</span>
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(buildShareText(matchData.team_1.short_name, matchData.team_2.short_name, matchData.start_time))}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg border border-[#25D366]/30 bg-[#25D366]/5 text-[#25D366] text-sm font-medium"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>
              Nudge your group
            </a>
            <Link href="/predictions" className="w-full">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />Back to Matches
              </Button>
            </Link>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
