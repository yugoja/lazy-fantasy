'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
    getTournamentPicks,
    getTournamentTeams,
    getTournamentPlayers,
    submitTournamentPicks,
    TournamentPicksResponse,
    TeamPickOption,
    PlayerPickOption,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Check, Trophy, Star, User, Search } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';

const WINDOW_LABELS: Record<string, { label: string; color: string }> = {
    open: { label: 'Picks Open', color: 'bg-green-100 text-green-800' },
    open2: { label: 'Window 2 Open (Half Points)', color: 'bg-yellow-100 text-yellow-800' },
    locked: { label: 'Picks Locked', color: 'bg-red-100 text-red-800' },
    finalized: { label: 'Finalized', color: 'bg-slate-100 text-slate-700' },
    closed: { label: 'Picks Closed', color: 'bg-slate-100 text-slate-700' },
};

export default function TournamentPicksPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const tournamentId = Number(params.id);

    const [picks, setPicks] = useState<TournamentPicksResponse | null>(null);
    const [teams, setTeams] = useState<TeamPickOption[]>([]);
    const [players, setPlayers] = useState<PlayerPickOption[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');

    // Local selection state
    const [selectedTop4, setSelectedTop4] = useState<number[]>([]);
    const [selectedBatsman, setSelectedBatsman] = useState<number | null>(null);
    const [selectedBowler, setSelectedBowler] = useState<number | null>(null);
    const [playerSearch, setPlayerSearch] = useState('');

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
        setIsLoading(true);
        try {
            const [picksData, teamsData, playersData] = await Promise.allSettled([
                getTournamentPicks(tournamentId),
                getTournamentTeams(tournamentId),
                getTournamentPlayers(tournamentId),
            ]);
            if (picksData.status === 'fulfilled') {
                const p = picksData.value;
                setPicks(p);
                setSelectedTop4(p.top4_team_ids.filter((id): id is number => id !== null));
                setSelectedBatsman(p.best_batsman_player_id);
                setSelectedBowler(p.best_bowler_player_id);
            }
            if (teamsData.status === 'fulfilled') setTeams(teamsData.value);
            if (playersData.status === 'fulfilled') setPlayers(playersData.value);
        } catch {
            setError('Failed to load tournament data');
        } finally {
            setIsLoading(false);
        }
    };

    const toggleTeam = (teamId: number) => {
        setSelectedTop4(prev => {
            if (prev.includes(teamId)) return prev.filter(id => id !== teamId);
            if (prev.length >= 4) return prev;
            return [...prev, teamId];
        });
    };

    const handleSubmit = async () => {
        setError('');
        setIsSubmitting(true);
        try {
            const updated = await submitTournamentPicks(
                tournamentId,
                selectedTop4,
                selectedBatsman,
                selectedBowler,
            );
            setPicks(updated);
            router.push(`/tournaments/${tournamentId}`);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Failed to save picks');
        } finally {
            setIsSubmitting(false);
        }
    };

    const isOpen = picks?.picks_window === 'open' || picks?.picks_window === 'open2';

    const filteredPlayers = players.filter(p =>
        playerSearch === '' ||
        p.name.toLowerCase().includes(playerSearch.toLowerCase()) ||
        (p.team_name ?? '').toLowerCase().includes(playerSearch.toLowerCase())
    );

    const batsmen = filteredPlayers.filter(p =>
        ['Batsman', 'All-Rounder', 'Wicketkeeper'].includes(p.role)
    );
    const bowlers = filteredPlayers.filter(p =>
        ['Bowler', 'All-Rounder'].includes(p.role)
    );

    if (authLoading || isLoading) {
        return (
            <div className="container-mobile py-6 space-y-4">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    const windowInfo = picks ? WINDOW_LABELS[picks.picks_window] ?? WINDOW_LABELS['closed'] : WINDOW_LABELS['closed'];

    return (
        <div className="container-mobile py-6 space-y-6 pb-48">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{picks?.tournament_name ?? 'Tournament'}</h1>
                <p className="text-muted-foreground text-sm mt-1">Season picks — up to {picks?.is_window2 ? '100' : '200'} pts</p>
            </div>

            {/* Window status */}
            <div className={cn('rounded-lg px-4 py-2 text-sm font-medium inline-flex', windowInfo.color)}>
                {windowInfo.label}
            </div>

            {/* Current picks summary */}
            {(selectedTop4.length > 0 || selectedBatsman || selectedBowler) && (
                <Card>
                    <CardContent className="pt-4 space-y-3">
                        {/* Playoff teams */}
                        <div>
                            <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Playoff Teams</p>
                            <div className="flex flex-wrap gap-2">
                                {selectedTop4.map(teamId => {
                                    const team = teams.find(t => t.id === teamId);
                                    const logoSrc = team ? getTeamLogoUrl(team.short_name) : null;
                                    return team ? (
                                        <div key={teamId} className="flex items-center gap-1.5 bg-primary/10 text-primary rounded-full px-3 py-1 text-xs font-medium">
                                            {logoSrc && (
                                                // eslint-disable-next-line @next/next/no-img-element
                                                <img src={logoSrc} alt={team.short_name} width={14} height={14}
                                                    className="h-3.5 w-3.5 object-contain"
                                                    onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                            )}
                                            {team.short_name}
                                        </div>
                                    ) : null;
                                })}
                                {Array.from({ length: 4 - selectedTop4.length }).map((_, i) => (
                                    <div key={`empty-${i}`} className="border border-dashed border-border rounded-full px-3 py-1 text-xs text-muted-foreground">—</div>
                                ))}
                            </div>
                        </div>
                        {/* Batsman + Bowler */}
                        <div className="flex gap-4 pt-1 border-t border-border">
                            <div className="flex-1">
                                <p className="text-xs text-muted-foreground mb-0.5">Best Batsman</p>
                                <p className={cn('text-sm font-medium', selectedBatsman ? 'text-foreground' : 'text-muted-foreground/50')}>
                                    {selectedBatsman ? (players.find(p => p.id === selectedBatsman)?.name ?? '—') : '—'}
                                </p>
                            </div>
                            <div className="flex-1">
                                <p className="text-xs text-muted-foreground mb-0.5">Best Bowler</p>
                                <p className={cn('text-sm font-medium', selectedBowler ? 'text-foreground' : 'text-muted-foreground/50')}>
                                    {selectedBowler ? (players.find(p => p.id === selectedBowler)?.name ?? '—') : '—'}
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Points breakdown */}
            {isOpen && (
                <Card>
                    <CardContent className="pt-4 text-sm text-muted-foreground space-y-1">
                        <div className="flex justify-between">
                            <span>Each correct playoff team</span>
                            <span className="font-semibold text-foreground">{picks?.is_window2 ? '12' : '25'} pts</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Best Batsman</span>
                            <span className="font-semibold text-foreground">{picks?.is_window2 ? '25' : '50'} pts</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Best Bowler</span>
                            <span className="font-semibold text-foreground">{picks?.is_window2 ? '25' : '50'} pts</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Points earned (after finalized) */}
            {picks?.is_processed && (
                <Card className="border-green-200 bg-green-50">
                    <CardContent className="pt-4">
                        <div className="text-center">
                            <Trophy className="w-8 h-8 text-green-600 mx-auto mb-1" />
                            <p className="text-2xl font-bold text-green-700">{picks.points_earned} pts</p>
                            <p className="text-sm text-green-600">Tournament picks points earned</p>
                        </div>
                    </CardContent>
                </Card>
            )}

            {error && <p className="text-red-500 text-sm">{error}</p>}

            {/* Top 4 Teams */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Trophy className="w-4 h-4" />
                        Top 4 Playoff Teams
                        <Badge variant="outline" className="ml-auto text-xs">
                            {selectedTop4.length}/4 selected
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-2">
                        {teams.map(team => {
                            const isSelected = selectedTop4.includes(team.id);
                            const isDisabled = !isOpen;
                            const canAdd = selectedTop4.length < 4 || isSelected;
                            const logoSrc = getTeamLogoUrl(team.short_name);
                            return (
                                <button
                                    key={team.id}
                                    disabled={isDisabled || (!canAdd && !isSelected)}
                                    onClick={() => toggleTeam(team.id)}
                                    className={cn(
                                        'relative flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                                        isSelected
                                            ? 'border-primary bg-primary/10 text-primary font-medium'
                                            : 'border-border bg-background hover:bg-muted',
                                        (isDisabled || (!canAdd && !isSelected)) && 'opacity-50 cursor-not-allowed',
                                    )}
                                >
                                    {logoSrc ? (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img src={logoSrc} alt={team.short_name} width={20} height={20}
                                            className="h-5 w-5 object-contain shrink-0"
                                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                    ) : isSelected ? (
                                        <Check className="w-3 h-3 shrink-0" />
                                    ) : null}
                                    <span className="truncate">{team.short_name}</span>
                                    {isSelected && logoSrc && (
                                        <Check className="w-3 h-3 shrink-0 ml-auto" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Player search */}
            {(isOpen || picks?.best_batsman_player_id || picks?.best_bowler_player_id) && (
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search players..."
                        value={playerSearch}
                        onChange={e => setPlayerSearch(e.target.value)}
                        className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        disabled={!isOpen}
                    />
                </div>
            )}

            {/* Best Batsman */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Star className="w-4 h-4" />
                        Best Batsman
                        {selectedBatsman && (
                            <Badge variant="secondary" className="ml-auto text-xs">
                                {players.find(p => p.id === selectedBatsman)?.name ?? '—'}
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-1 max-h-64 overflow-y-auto">
                        {batsmen.length === 0 && (
                            <p className="text-sm text-muted-foreground text-center py-4">No players found</p>
                        )}
                        {batsmen.map(player => {
                            const isSelected = selectedBatsman === player.id;
                            return (
                                <button
                                    key={player.id}
                                    disabled={!isOpen}
                                    onClick={() => setSelectedBatsman(isSelected ? null : player.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors text-left',
                                        isSelected
                                            ? 'bg-primary/10 text-primary font-medium'
                                            : 'hover:bg-muted',
                                        !isOpen && 'cursor-default',
                                    )}
                                >
                                    <div>
                                        <span>{player.name}</span>
                                        <span className="text-xs text-muted-foreground ml-2">{player.team_name}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">{player.role}</span>
                                        {isSelected && <Check className="w-3 h-3 text-primary" />}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Best Bowler */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <User className="w-4 h-4" />
                        Best Bowler
                        {selectedBowler && (
                            <Badge variant="secondary" className="ml-auto text-xs">
                                {players.find(p => p.id === selectedBowler)?.name ?? '—'}
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-1 max-h-64 overflow-y-auto">
                        {bowlers.length === 0 && (
                            <p className="text-sm text-muted-foreground text-center py-4">No players found</p>
                        )}
                        {bowlers.map(player => {
                            const isSelected = selectedBowler === player.id;
                            return (
                                <button
                                    key={player.id}
                                    disabled={!isOpen}
                                    onClick={() => setSelectedBowler(isSelected ? null : player.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors text-left',
                                        isSelected
                                            ? 'bg-primary/10 text-primary font-medium'
                                            : 'hover:bg-muted',
                                        !isOpen && 'cursor-default',
                                    )}
                                >
                                    <div>
                                        <span>{player.name}</span>
                                        <span className="text-xs text-muted-foreground ml-2">{player.team_name}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">{player.role}</span>
                                        {isSelected && <Check className="w-3 h-3 text-primary" />}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Sticky submit */}
            {isOpen && (
                <div className="fixed bottom-16 left-0 right-0 z-10 bg-background border-t border-border px-4 py-3">
                    <div className="container-mobile">
                        <div className="flex items-center justify-between mb-2 text-xs text-muted-foreground">
                            <span>{selectedTop4.length}/4 teams</span>
                            <span>{selectedBatsman ? '✓' : '–'} Batsman · {selectedBowler ? '✓' : '–'} Bowler</span>
                        </div>
                        <Button
                            className="w-full"
                            onClick={handleSubmit}
                            disabled={isSubmitting || selectedTop4.length === 0}
                        >
                            {isSubmitting ? 'Saving...' : 'Save Picks'}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
