'use client';

import { useEffect, useRef, useState } from 'react';
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
import { ArrowLeft, Trophy, Target, Star, CheckCircle2, Clock } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';

interface Player {
  id: number;
  name: string;
  team_id: number;
  role: string;
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
    '',
    `I've locked in my call. Have you? ⏰`,
    `Closes in ${formatCountdown(startTime)} 👇`,
    `${appUrl}/predictions`,
  ].join('\n');
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

  const [winnerId, setWinnerId] = useState<number | null>(null);
  const [mostRunsTeam1Id, setMostRunsTeam1Id] = useState<number | null>(null);
  const [mostRunsTeam2Id, setMostRunsTeam2Id] = useState<number | null>(null);
  const [mostWicketsTeam1Id, setMostWicketsTeam1Id] = useState<number | null>(null);
  const [mostWicketsTeam2Id, setMostWicketsTeam2Id] = useState<number | null>(null);
  const [pomId, setPomId] = useState<number | null>(null);

  // Section refs for scroll-to-on-pick-click
  const scrollRef = useRef<HTMLDivElement>(null);
  const winnerRef = useRef<HTMLElement>(null);
  const bat1Ref = useRef<HTMLElement>(null);
  const bat2Ref = useRef<HTMLElement>(null);
  const bowl1Ref = useRef<HTMLElement>(null);
  const bowl2Ref = useRef<HTMLElement>(null);
  const pomRef = useRef<HTMLElement>(null);

  const scrollToSection = (ref: React.RefObject<HTMLElement | null>) => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

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
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
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

  // Lookup helpers
  const findPlayer = (id: number | null, pool: Player[]) => pool.find(p => p.id === id);
  const winnerTeam = winnerId ? (winnerId === matchData.team_1.id ? matchData.team_1 : matchData.team_2) : null;
  const runsT1 = findPlayer(mostRunsTeam1Id, matchData.team_1_players);
  const runsT2 = findPlayer(mostRunsTeam2Id, matchData.team_2_players);
  const wktsT1 = findPlayer(mostWicketsTeam1Id, matchData.team_1_players);
  const wktsT2 = findPlayer(mostWicketsTeam2Id, matchData.team_2_players);
  const pomPlayer = findPlayer(pomId, allPlayers);

  const renderPlayerGrid = (players: Player[], selectedId: number | null, onSelect: (id: number) => void) => (
    <div className="grid grid-cols-3 gap-2">
      {players.map((player) => {
        const isSelected = selectedId === player.id;
        return (
          <button
            key={player.id}
            type="button"
            onClick={() => onSelect(player.id)}
            className={cn(
              'flex flex-col items-center gap-1 p-2.5 rounded-xl border transition-all',
              isSelected ? 'border-primary bg-primary/10' : 'border-border bg-card hover:border-border/80'
            )}
          >
            <div className={cn(
              'h-9 w-9 rounded-full flex items-center justify-center text-xs font-bold',
              isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
            )}>
              {getInitials(player.name)}
            </div>
            <span className="text-xs font-medium truncate w-full text-center leading-tight">
              {getLastName(player.name)}
            </span>
            <span className="text-[9px] text-muted-foreground tracking-wide">{getRoleLabel(player.role)}</span>
          </button>
        );
      })}
    </div>
  );

  const SectionHeader = ({ icon, label, team, pts }: { icon: React.ReactNode; label: string; team?: string; pts: number }) => (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-primary">{icon}</span>
      <span className="font-semibold text-sm">{label}</span>
      {team && <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-muted text-muted-foreground">{team}</span>}
      <span className="ml-auto text-[11px] font-semibold text-primary">+{pts} pts</span>
    </div>
  );

  // h-screen minus app header (h-14=56px) minus bottom nav (h-16=64px)
  return (
    <div className="flex flex-col mx-auto max-w-[430px]" style={{ height: 'calc(100dvh - 56px - 64px)' }}>

      {/* ── Sticky top: match info + picks strip ── */}
      <div className="flex-shrink-0 px-4 pt-3 pb-3 border-b border-border bg-background space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Link href="/predictions" className="shrink-0 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <h1 className="text-base font-bold">
                  {matchData.team_1.short_name} vs {matchData.team_2.short_name}
                </h1>
                {matchData.lineup_announced && (
                  <Badge className="bg-green-600/20 text-green-400 border-green-600/30 text-[9px] py-0">PLAYING XI</Badge>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground">
                {new Date(matchData.start_time).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                {' · '}
                {new Date(matchData.start_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })} IST
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0 px-2 py-1 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
            <Clock className="h-3 w-3" />
            {formatCountdown(matchData.start_time)}
          </div>
        </div>

        {/* Picks summary strip */}
        <div className="rounded-xl border border-border bg-card p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">Your Picks</span>
            <span className="text-[9px] text-muted-foreground">{filledCount} of 6 made</span>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {[
              { label: 'WINNER',                                        value: winnerTeam?.short_name,              ref: winnerRef },
              { label: `BAT · ${matchData.team_1.short_name}`,         value: runsT1  ? getLastName(runsT1.name)  : null, ref: bat1Ref },
              { label: `BAT · ${matchData.team_2.short_name}`,         value: runsT2  ? getLastName(runsT2.name)  : null, ref: bat2Ref },
              { label: `BOWL · ${matchData.team_1.short_name}`,        value: wktsT1  ? getLastName(wktsT1.name)  : null, ref: bowl1Ref },
              { label: `BOWL · ${matchData.team_2.short_name}`,        value: wktsT2  ? getLastName(wktsT2.name)  : null, ref: bowl2Ref },
              { label: 'MOTM',                                         value: pomPlayer ? getLastName(pomPlayer.name) : null, ref: pomRef },
            ].map(({ label, value, ref }) => (
              <button
                key={label}
                type="button"
                onClick={() => scrollToSection(ref)}
                className={cn(
                  'rounded-lg px-2 py-1.5 border text-left transition-colors',
                  value ? 'border-primary/30 bg-primary/5' : 'border-border bg-muted/30'
                )}
              >
                <p className="text-[8px] text-muted-foreground uppercase tracking-wide leading-none mb-0.5">{label}</p>
                <p className={cn('text-[11px] font-semibold truncate', value ? 'text-primary' : 'text-muted-foreground')}>
                  {value ?? '—'}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Scrollable sections ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
        {error && (
          <div className="p-3 rounded-lg border border-destructive/50 bg-destructive/10">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        <section ref={winnerRef}>
          <SectionHeader icon={<Trophy className="h-4 w-4" />} label="Match Winner" pts={10} />
          <div className="grid grid-cols-2 gap-3">
            {[matchData.team_1, matchData.team_2].map((team) => {
              const isSelected = winnerId === team.id;
              const logoSrc = getTeamLogoUrl(team.short_name);
              return (
                <button
                  key={team.id}
                  type="button"
                  onClick={() => setWinnerId(team.id)}
                  className={cn(
                    'relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all',
                    isSelected ? 'border-primary bg-primary/10' : 'border-border bg-card hover:border-border/80'
                  )}
                >
                  {isSelected && <CheckCircle2 className="absolute top-2 right-2 h-4 w-4 text-primary" />}
                  {logoSrc && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={logoSrc} alt={team.name} width={40} height={40}
                      className="h-10 w-10 object-contain"
                      onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                  )}
                  <span className="font-bold text-base">{team.short_name}</span>
                  <span className="text-xs text-muted-foreground">{team.name}</span>
                </button>
              );
            })}
          </div>
        </section>

        <section ref={bat1Ref}>
          <SectionHeader icon={<Target className="h-4 w-4" />} label="Top Batsman" team={matchData.team_1.short_name} pts={20} />
          {renderPlayerGrid(t1Batters, mostRunsTeam1Id, setMostRunsTeam1Id)}
        </section>

        <section ref={bat2Ref}>
          <SectionHeader icon={<Target className="h-4 w-4" />} label="Top Batsman" team={matchData.team_2.short_name} pts={20} />
          {renderPlayerGrid(t2Batters, mostRunsTeam2Id, setMostRunsTeam2Id)}
        </section>

        <section ref={bowl1Ref}>
          <SectionHeader icon={<Target className="h-4 w-4" />} label="Top Bowler" team={matchData.team_1.short_name} pts={20} />
          {renderPlayerGrid(t1Bowlers, mostWicketsTeam1Id, setMostWicketsTeam1Id)}
        </section>

        <section ref={bowl2Ref}>
          <SectionHeader icon={<Target className="h-4 w-4" />} label="Top Bowler" team={matchData.team_2.short_name} pts={20} />
          {renderPlayerGrid(t2Bowlers, mostWicketsTeam2Id, setMostWicketsTeam2Id)}
        </section>

        <section ref={pomRef}>
          <SectionHeader icon={<Star className="h-4 w-4" />} label="Man of the Match" pts={50} />
          {renderPlayerGrid(allPlayers, pomId, setPomId)}
        </section>
      </div>

      {/* ── Sticky bottom: submit bar ── */}
      <div className="flex-shrink-0 bg-background/95 backdrop-blur-sm border-t border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {picks.map((v, i) => (
              <div key={i} className={cn('rounded-full transition-all', v ? 'h-2.5 w-2.5 bg-primary' : 'h-2 w-2 bg-muted')} />
            ))}
            <span className="text-xs text-muted-foreground ml-1">Up to 140 pts</span>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={filledCount < 6 || isSubmitting}
            className="ml-auto"
            size="lg"
          >
            {isSubmitting ? 'Saving...' : isEditing ? 'Update Picks' : 'Submit Picks'}
          </Button>
        </div>
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
