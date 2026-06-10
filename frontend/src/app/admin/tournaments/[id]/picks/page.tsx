'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
    getTournamentPicks,
    getTournamentTeams,
    getTournamentPlayers,
    TeamPickOption,
    PlayerPickOption,
    ApiError,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function adminRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error' }));
        throw new ApiError(res.status, err.detail || 'Error');
    }
    return res.json();
}

const WINDOWS = ['closed', 'open', 'locked', 'open2', 'finalized'] as const;

export default function AdminTournamentPicksPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const tournamentId = Number(params.id);

    const [teams, setTeams] = useState<TeamPickOption[]>([]);
    const [players, setPlayers] = useState<PlayerPickOption[]>([]);
    const [currentWindow, setCurrentWindow] = useState('closed');
    const [sport, setSport] = useState('cricket');
    const [tournamentName, setTournamentName] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [windowLoading, setWindowLoading] = useState(false);
    const [resultLoading, setResultLoading] = useState(false);
    const [message, setMessage] = useState('');

    // Result form state (cricket)
    const [resultTop4, setResultTop4] = useState<number[]>([]);
    const [resultBatsman, setResultBatsman] = useState<number | null>(null);
    const [resultBowler, setResultBowler] = useState<number | null>(null);
    // Result form state (football awards)
    const [resultBall, setResultBall] = useState<number | null>(null);
    const [resultBoot, setResultBoot] = useState<number | null>(null);
    const [resultGlove, setResultGlove] = useState<number | null>(null);

    const isFootball = sport === 'football';

    useEffect(() => {
        if (!authLoading && !isAuthenticated) router.push('/login');
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated && tournamentId) loadData();
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
                setCurrentWindow(picksData.value.picks_window);
                setTournamentName(picksData.value.tournament_name);
                setSport(picksData.value.sport);
            }
            if (teamsData.status === 'fulfilled') setTeams(teamsData.value);
            if (playersData.status === 'fulfilled') setPlayers(playersData.value);
        } finally {
            setIsLoading(false);
        }
    };

    const setWindow = async (window: string) => {
        setWindowLoading(true);
        setMessage('');
        try {
            const res = await adminRequest<{ picks_window: string }>(
                `/admin/tournaments/${tournamentId}/picks-window`,
                { method: 'PATCH', body: JSON.stringify({ window }) },
            );
            setCurrentWindow(res.picks_window);
            setMessage(`Window set to: ${res.picks_window}`);
        } catch (e: unknown) {
            setMessage(e instanceof Error ? e.message : 'Error');
        } finally {
            setWindowLoading(false);
        }
    };

    const submitResult = async () => {
        if (resultTop4.length !== 4) {
            setMessage(isFootball ? 'Select exactly 4 semi-finalists' : 'Select exactly 4 teams');
            return;
        }
        if (isFootball && (!resultBall || !resultBoot || !resultGlove)) {
            setMessage('Select Golden Ball, Boot, and Glove winners');
            return;
        }
        if (!isFootball && (!resultBatsman || !resultBowler)) {
            setMessage('Select 1 batsman and 1 bowler');
            return;
        }
        setResultLoading(true);
        setMessage('');
        try {
            const body = isFootball
                ? {
                    result_top4_team_ids: resultTop4,
                    result_golden_ball_player_id: resultBall,
                    result_golden_boot_player_id: resultBoot,
                    result_golden_glove_player_id: resultGlove,
                }
                : {
                    result_top4_team_ids: resultTop4,
                    result_best_batsman_player_id: resultBatsman,
                    result_best_bowler_player_id: resultBowler,
                };
            const res = await adminRequest<{ picks_scored: number }>(
                `/admin/tournaments/${tournamentId}/picks-result`,
                { method: 'POST', body: JSON.stringify(body) },
            );
            setMessage(`Results saved. ${res.picks_scored} picks scored.`);
        } catch (e: unknown) {
            setMessage(e instanceof Error ? e.message : 'Error');
        } finally {
            setResultLoading(false);
        }
    };

    const toggleResultTop4 = (id: number) => {
        setResultTop4(prev => {
            if (prev.includes(id)) return prev.filter(x => x !== id);
            if (prev.length >= 4) return prev;
            return [...prev, id];
        });
    };

    const batsmen = players.filter(p => ['Batsman', 'All-Rounder', 'Wicketkeeper'].includes(p.role));
    const bowlers = players.filter(p => ['Bowler', 'All-Rounder'].includes(p.role));
    const keepers = players.filter(p => p.role === 'Goalkeeper');

    const renderResultPicker = (
        label: string,
        pool: PlayerPickOption[],
        selected: number | null,
        set: (v: number | null) => void,
    ) => (
        <div>
            <p className="text-sm font-medium mb-2">
                {label}{selected ? `: ${players.find(p => p.id === selected)?.name}` : ''}
            </p>
            <div className="space-y-1 max-h-48 overflow-y-auto border rounded-lg p-2">
                {pool.map(p => (
                    <button
                        key={p.id}
                        onClick={() => set(selected === p.id ? null : p.id)}
                        className={cn(
                            'w-full flex items-center justify-between rounded px-3 py-1.5 text-sm text-left transition-colors',
                            selected === p.id ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted',
                        )}
                    >
                        <span>{p.name}</span>
                        <span className="text-xs text-muted-foreground">{p.team_name}</span>
                    </button>
                ))}
            </div>
        </div>
    );

    if (authLoading || isLoading) {
        return (
            <div className="container-mobile py-6 space-y-4">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    return (
        <div className="container-mobile py-6 space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Admin — Tournament Picks</h1>
                <p className="text-muted-foreground text-sm mt-1">{tournamentName}</p>
            </div>

            {message && (
                <div className="rounded-lg bg-muted px-4 py-2 text-sm">{message}</div>
            )}

            {/* Window controls */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Picks Window</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    {isFootball ? (
                        <p className="text-sm text-muted-foreground">
                            Football picks open automatically and lock at the first knockout kickoff —
                            no manual window control needed.
                        </p>
                    ) : (
                        <>
                            <p className="text-sm text-muted-foreground">
                                Current: <span className="font-semibold text-foreground">{currentWindow}</span>
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {WINDOWS.map(w => (
                                    <Button
                                        key={w}
                                        size="sm"
                                        variant={currentWindow === w ? 'default' : 'outline'}
                                        disabled={windowLoading}
                                        onClick={() => setWindow(w)}
                                    >
                                        {w}
                                    </Button>
                                ))}
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Results form */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Set Results & Score Picks</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Top 4 / Semi-finalists */}
                    <div>
                        <p className="text-sm font-medium mb-2">
                            {isFootball ? 'Semi-Finalists' : 'Top 4 Teams'} ({resultTop4.length}/4)
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                            {teams.map(t => (
                                <button
                                    key={t.id}
                                    onClick={() => toggleResultTop4(t.id)}
                                    className={cn(
                                        'rounded-lg border px-3 py-2 text-sm text-left transition-colors',
                                        resultTop4.includes(t.id)
                                            ? 'border-primary bg-primary/10 text-primary font-medium'
                                            : 'border-border hover:bg-muted',
                                        resultTop4.length >= 4 && !resultTop4.includes(t.id) && 'opacity-50 cursor-not-allowed',
                                    )}
                                >
                                    {t.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {isFootball ? (
                        <>
                            {renderResultPicker('Golden Boot', players, resultBoot, setResultBoot)}
                            {renderResultPicker('Golden Ball', players, resultBall, setResultBall)}
                            {renderResultPicker('Golden Glove', keepers, resultGlove, setResultGlove)}
                        </>
                    ) : (
                        <>
                            {renderResultPicker('Best Batsman', batsmen, resultBatsman, setResultBatsman)}
                            {renderResultPicker('Best Bowler', bowlers, resultBowler, setResultBowler)}
                        </>
                    )}

                    <Button
                        className="w-full"
                        onClick={submitResult}
                        disabled={resultLoading}
                    >
                        {resultLoading ? 'Scoring...' : 'Save Results & Score Picks'}
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}
