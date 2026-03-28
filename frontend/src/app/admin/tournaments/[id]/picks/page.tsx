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
    const [tournamentName, setTournamentName] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [windowLoading, setWindowLoading] = useState(false);
    const [resultLoading, setResultLoading] = useState(false);
    const [message, setMessage] = useState('');

    // Result form state
    const [resultTop4, setResultTop4] = useState<number[]>([]);
    const [resultBatsman, setResultBatsman] = useState<number | null>(null);
    const [resultBowler, setResultBowler] = useState<number | null>(null);

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
        if (resultTop4.length !== 4 || !resultBatsman || !resultBowler) {
            setMessage('Select exactly 4 teams, 1 batsman, and 1 bowler');
            return;
        }
        setResultLoading(true);
        setMessage('');
        try {
            const res = await adminRequest<{ picks_scored: number }>(
                `/admin/tournaments/${tournamentId}/picks-result`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        result_top4_team_ids: resultTop4,
                        result_best_batsman_player_id: resultBatsman,
                        result_best_bowler_player_id: resultBowler,
                    }),
                },
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
                </CardContent>
            </Card>

            {/* Results form */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Set Results & Score Picks</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Top 4 */}
                    <div>
                        <p className="text-sm font-medium mb-2">
                            Top 4 Teams ({resultTop4.length}/4)
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

                    {/* Best Batsman */}
                    <div>
                        <p className="text-sm font-medium mb-2">
                            Best Batsman{resultBatsman ? `: ${players.find(p => p.id === resultBatsman)?.name}` : ''}
                        </p>
                        <div className="space-y-1 max-h-48 overflow-y-auto border rounded-lg p-2">
                            {batsmen.map(p => (
                                <button
                                    key={p.id}
                                    onClick={() => setResultBatsman(resultBatsman === p.id ? null : p.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between rounded px-3 py-1.5 text-sm text-left transition-colors',
                                        resultBatsman === p.id
                                            ? 'bg-primary/10 text-primary font-medium'
                                            : 'hover:bg-muted',
                                    )}
                                >
                                    <span>{p.name}</span>
                                    <span className="text-xs text-muted-foreground">{p.team_name}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Best Bowler */}
                    <div>
                        <p className="text-sm font-medium mb-2">
                            Best Bowler{resultBowler ? `: ${players.find(p => p.id === resultBowler)?.name}` : ''}
                        </p>
                        <div className="space-y-1 max-h-48 overflow-y-auto border rounded-lg p-2">
                            {bowlers.map(p => (
                                <button
                                    key={p.id}
                                    onClick={() => setResultBowler(resultBowler === p.id ? null : p.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between rounded px-3 py-1.5 text-sm text-left transition-colors',
                                        resultBowler === p.id
                                            ? 'bg-primary/10 text-primary font-medium'
                                            : 'hover:bg-muted',
                                    )}
                                >
                                    <span>{p.name}</span>
                                    <span className="text-xs text-muted-foreground">{p.team_name}</span>
                                </button>
                            ))}
                        </div>
                    </div>

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
