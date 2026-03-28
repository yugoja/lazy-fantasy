'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, API_BASE } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowLeft, Trophy, Target, Star, CheckCircle2 } from 'lucide-react';
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
}

export default function SetResultPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const matchId = Number(params.id);

    const [matchData, setMatchData] = useState<MatchData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Form state — per-team fields
    const [winnerId, setWinnerId] = useState<number | null>(null);
    const [mostRunsTeam1Id, setMostRunsTeam1Id] = useState('');
    const [mostRunsTeam2Id, setMostRunsTeam2Id] = useState('');
    const [mostWicketsTeam1Id, setMostWicketsTeam1Id] = useState('');
    const [mostWicketsTeam2Id, setMostWicketsTeam2Id] = useState('');
    const [pomId, setPomId] = useState('');

    useEffect(() => {
        if (!authLoading && !isAuthenticated) router.push('/login');
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (matchId) loadMatchData();
    }, [matchId]);

    const loadMatchData = async () => {
        try {
            const data = await getMatchPlayers(matchId);
            setMatchData(data);
        } catch {
            setError('Failed to load match data');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!winnerId || !mostRunsTeam1Id || !mostRunsTeam2Id ||
            !mostWicketsTeam1Id || !mostWicketsTeam2Id || !pomId) {
            setError('Please fill in all fields');
            return;
        }

        setIsSubmitting(true);
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE}/admin/matches/${matchId}/result`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    result_winner_id: winnerId,
                    result_most_runs_team1_player_id: Number(mostRunsTeam1Id),
                    result_most_runs_team2_player_id: Number(mostRunsTeam2Id),
                    result_most_wickets_team1_player_id: Number(mostWicketsTeam1Id),
                    result_most_wickets_team2_player_id: Number(mostWicketsTeam2Id),
                    result_pom_player_id: Number(pomId),
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to set result');
            }

            const data = await response.json();
            setSuccess(`Result saved! ${data.predictions_processed} predictions processed.`);
            setTimeout(() => router.push('/admin'), 2000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to set result');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (authLoading || isLoading) {
        return (
            <div className="container-mobile py-6 space-y-6">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-32 w-full" />
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
        );
    }

    if (!matchData) {
        return (
            <div className="container-mobile py-6 space-y-4">
                <Card className="p-6 text-center space-y-3">
                    <p className="text-sm text-destructive">{error || 'Match not found'}</p>
                    <Link href="/admin"><Button variant="outline" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back to Admin</Button></Link>
                </Card>
            </div>
        );
    }

    const renderTeamSelect = (
        players: Player[],
        value: string,
        onValueChange: (v: string) => void,
        placeholder: string
    ) => (
        <Select value={value} onValueChange={onValueChange}>
            <SelectTrigger>
                <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
                {players.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                        {p.name} <span className="text-muted-foreground">({p.role})</span>
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );

    const renderPerTeamSection = (
        icon: React.ReactNode,
        label: string,
        team1Value: string,
        onTeam1Change: (v: string) => void,
        team2Value: string,
        onTeam2Change: (v: string) => void,
    ) => (
        <section className="space-y-3">
            <div className="flex items-center gap-2">
                {icon}
                <h2 className="font-semibold text-sm">{label}</h2>
            </div>
            <div className="space-y-2">
                <div className="space-y-1">
                    <p className="text-xs text-muted-foreground font-medium px-1">{matchData!.team_1.short_name}</p>
                    {renderTeamSelect(matchData!.team_1_players, team1Value, onTeam1Change, `Select ${matchData!.team_1.short_name} player`)}
                </div>
                <div className="space-y-1">
                    <p className="text-xs text-muted-foreground font-medium px-1">{matchData!.team_2.short_name}</p>
                    {renderTeamSelect(matchData!.team_2_players, team2Value, onTeam2Change, `Select ${matchData!.team_2.short_name} player`)}
                </div>
            </div>
        </section>
    );

    const allPlayers = [...matchData.team_1_players, ...matchData.team_2_players];

    return (
        <div className="container-mobile py-6 space-y-5">
            <Link href="/admin" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ArrowLeft className="h-4 w-4" />
                Back to Admin
            </Link>

            <div>
                <h1 className="text-xl font-bold">Set Match Result</h1>
                <p className="text-xs text-muted-foreground mt-1">
                    {matchData.team_1.name} vs {matchData.team_2.name}
                </p>
            </div>

            {error && (
                <Card className="p-3 border-destructive/50 bg-destructive/10">
                    <p className="text-sm text-destructive">{error}</p>
                </Card>
            )}
            {success && (
                <Card className="p-3 border-green-500/50 bg-green-500/10">
                    <p className="text-sm text-green-400">{success}</p>
                </Card>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
                {/* Winner */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Match Winner</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {[matchData.team_1, matchData.team_2].map((team) => {
                            const isSelected = winnerId === team.id;
                            const flagSrc = getTeamLogoUrl(team.short_name);
                            return (
                                <button
                                    key={team.id}
                                    type="button"
                                    onClick={() => setWinnerId(team.id)}
                                    className={cn(
                                        'flex flex-col items-center gap-2 p-4 rounded-lg border transition-all hover:border-primary/50',
                                        isSelected ? 'border-primary bg-primary/10' : 'border-border bg-card'
                                    )}
                                >
                                    {flagSrc && (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img src={flagSrc} alt={team.name} width={36} height={36}
                                            className="h-9 w-9 object-contain"
                                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                    )}
                                    <span className="font-semibold text-sm">{team.short_name}</span>
                                    <span className="text-xs text-muted-foreground text-center">{team.name}</span>
                                    {isSelected && <CheckCircle2 className="h-4 w-4 text-primary" />}
                                </button>
                            );
                        })}
                    </div>
                </section>

                {/* Most Runs — per team */}
                {renderPerTeamSection(
                    <Target className="h-4 w-4 text-primary" />,
                    'Most Runs',
                    mostRunsTeam1Id, setMostRunsTeam1Id,
                    mostRunsTeam2Id, setMostRunsTeam2Id,
                )}

                {/* Most Wickets — per team */}
                {renderPerTeamSection(
                    <Target className="h-4 w-4 text-primary" />,
                    'Most Wickets',
                    mostWicketsTeam1Id, setMostWicketsTeam1Id,
                    mostWicketsTeam2Id, setMostWicketsTeam2Id,
                )}

                {/* Player of the Match — any player */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Star className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Player of the Match</h2>
                    </div>
                    <Select value={pomId} onValueChange={setPomId}>
                        <SelectTrigger>
                            <SelectValue placeholder="Select player" />
                        </SelectTrigger>
                        <SelectContent>
                            {allPlayers.map((p) => (
                                <SelectItem key={p.id} value={String(p.id)}>
                                    {p.name} <span className="text-muted-foreground">({p.role})</span>
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </section>

                <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
                    {isSubmitting ? 'Saving...' : 'Save Result & Calculate Scores'}
                </Button>
            </form>
        </div>
    );
}
