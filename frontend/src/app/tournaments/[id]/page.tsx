'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getTournamentPicks, getMatchesByTournament, getTournamentTeams, getTournamentPlayers, TournamentPicksResponse, TeamPickOption, PlayerPickOption } from '@/lib/api';
import { getTeamLogoUrl } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, Check, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MatchItem {
  id: number;
  tournament_id: number;
  team_1: { id: number; name: string; short_name: string; logo_url: string | null };
  team_2: { id: number; name: string; short_name: string; logo_url: string | null };
  start_time: string;
  status: string;
  lineup_announced: boolean;
}

function formatMatchTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) +
    ' · ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function isWithin24h(iso: string) {
  return new Date(iso).getTime() - Date.now() < 24 * 60 * 60 * 1000;
}

export default function TournamentCentralPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const tournamentId = Number(params.id);

  const [picks, setPicks] = useState<TournamentPicksResponse | null>(null);
  const [teams, setTeams] = useState<TeamPickOption[]>([]);
  const [players, setPlayers] = useState<PlayerPickOption[]>([]);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [tab, setTab] = useState<'upcoming' | 'done'>('upcoming');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated && tournamentId) {
      loadData();
    }
  }, [isAuthenticated, tournamentId]);

  const loadData = async () => {
    try {
      const [picksResult, matchesResult, teamsResult, playersResult] = await Promise.allSettled([
        getTournamentPicks(tournamentId),
        getMatchesByTournament(tournamentId, true),
        getTournamentTeams(tournamentId),
        getTournamentPlayers(tournamentId),
      ]);
      if (picksResult.status === 'fulfilled') setPicks(picksResult.value);
      if (matchesResult.status === 'fulfilled') setMatches(matchesResult.value);
      if (teamsResult.status === 'fulfilled') setTeams(teamsResult.value);
      if (playersResult.status === 'fulfilled') setPlayers(playersResult.value);
    } catch {
      // empty state
    } finally {
      setIsLoading(false);
    }
  };

  const isOpen = picks?.picks_window === 'open' || picks?.picks_window === 'open2';
  const hasPicks = picks && (
    picks.top4_team_ids.some(id => id !== null) ||
    picks.best_batsman_player_id !== null ||
    picks.best_bowler_player_id !== null
  );

  const upcomingMatches = matches.filter(m => m.status !== 'completed' && m.status !== 'result_set').slice(0, 3);
  const doneMatches = matches.filter(m => m.status === 'completed' || m.status === 'result_set');
  const displayMatches = tab === 'upcoming' ? upcomingMatches : doneMatches;

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-10 w-full" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-5">
      {/* Back nav */}
      <div>
        <Link href="/tournaments">
          <Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Tournaments
          </Button>
        </Link>
        <h1 className="text-2xl font-bold mt-1">{picks?.tournament_name ?? 'Tournament'}</h1>
      </div>

      {/* Mega Predictions */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">Mega Predictions</p>
          {isOpen && (
            <div className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
              <span className="text-[10px] font-semibold text-green-500 uppercase tracking-wider">Open</span>
            </div>
          )}
        </div>

        {hasPicks ? (
          <Card className="p-4 space-y-4">
            {/* Top 4 teams */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Top 4 Teams</p>
              <div className="flex flex-wrap gap-2">
                {picks!.top4_team_ids.filter((id): id is number => id !== null).map((teamId, idx) => {
                  const team = teams.find(t => t.id === teamId);
                  const logoSrc = team ? getTeamLogoUrl(team.short_name) : undefined;
                  return (
                    <div key={idx} className="flex items-center gap-1.5 bg-primary/10 text-primary rounded-full px-2.5 py-1 text-xs font-medium">
                      {logoSrc ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={logoSrc} alt={team?.short_name ?? ''} width={16} height={16}
                          className="h-4 w-4 object-contain"
                          onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                      ) : (
                        <Check className="h-3 w-3" />
                      )}
                      <span>{team?.short_name ?? '…'}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-border" />

            {/* Batsman + Bowler */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">Batsman</p>
                {picks!.best_batsman_player_id ? (
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-amber-500/20 flex items-center justify-center text-xs font-bold text-amber-500">
                      {(players.find(p => p.id === picks!.best_batsman_player_id)?.name ?? '?').charAt(0)}
                    </div>
                    <span className="text-sm font-medium truncate">
                      {players.find(p => p.id === picks!.best_batsman_player_id)?.name ?? '…'}
                    </span>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Not picked</p>
                )}
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">Bowler</p>
                {picks!.best_bowler_player_id ? (
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-sky-500/20 flex items-center justify-center text-xs font-bold text-sky-500">
                      {(players.find(p => p.id === picks!.best_bowler_player_id)?.name ?? '?').charAt(0)}
                    </div>
                    <span className="text-sm font-medium truncate">
                      {players.find(p => p.id === picks!.best_bowler_player_id)?.name ?? '…'}
                    </span>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Not picked</p>
                )}
              </div>
            </div>

            {isOpen && (
              <div className="pt-2">
                <Link href={`/tournaments/${tournamentId}/picks`}>
                  <Button className="w-full">Update Picks ›</Button>
                </Link>
              </div>
            )}

            {picks!.is_processed && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Points earned</span>
                <div className="flex items-center gap-1.5 font-bold text-primary">
                  <Trophy className="h-4 w-4" />
                  {picks!.points_earned} pts
                </div>
              </div>
            )}
          </Card>
        ) : (
          <Card className="p-6 text-center space-y-3">
            <Trophy className="h-8 w-8 text-muted-foreground mx-auto" />
            {isOpen ? (
              <>
                <p className="text-sm text-muted-foreground">Make your tournament mega picks</p>
                <Link href={`/tournaments/${tournamentId}/picks`}>
                  <Button size="sm">Make your picks →</Button>
                </Link>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Picks window is closed</p>
            )}
          </Card>
        )}
      </section>

      {/* Matches */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">Matches</p>
          {/* Segmented toggle */}
          <div className="flex rounded-lg bg-muted p-0.5 gap-0.5">
            <button
              onClick={() => setTab('upcoming')}
              className={cn(
                'text-xs font-medium px-3 py-1 rounded-md transition-colors',
                tab === 'upcoming' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'
              )}
            >
              Upcoming
            </button>
            <button
              onClick={() => setTab('done')}
              className={cn(
                'text-xs font-medium px-3 py-1 rounded-md transition-colors',
                tab === 'done' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'
              )}
            >
              Done
            </button>
          </div>
        </div>

        {displayMatches.length === 0 ? (
          <Card className="p-6 text-center">
            <p className="text-sm text-muted-foreground">
              {tab === 'upcoming' ? 'No upcoming matches' : 'No completed matches'}
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {displayMatches.map(match => {
              const imminent = isWithin24h(match.start_time) && tab === 'upcoming';
              return (
                <Card key={match.id} className="p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">
                        {match.team_1.short_name} <span className="text-muted-foreground font-normal">vs</span> {match.team_2.short_name}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{formatMatchTime(match.start_time)}</p>
                    </div>
                    {tab === 'upcoming' && (
                      <Link href={`/matches/${match.id}/predict`}>
                        <Button
                          size="sm"
                          variant={imminent ? 'default' : 'outline'}
                          className="text-xs shrink-0"
                        >
                          Predict
                        </Button>
                      </Link>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
