'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, API_BASE } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowLeft, Trophy, Target, Star, CheckCircle2 } from 'lucide-react';
import { cn, getFlagUrl } from '@/lib/utils';

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

    // Form state
    const [winnerId, setWinnerId] = useState<number | null>(null);
    const [mostRunsId, setMostRunsId] = useState<string>('');
    const [mostWicketsId, setMostWicketsId] = useState<string>('');
    const [pomId, setPomId] = useState<string>('');

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (matchId) {
            loadMatchData();
        }
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

        if (!winnerId || !mostRunsId || !mostWicketsId || !pomId) {
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
                    result_most_runs_player_id: Number(mostRunsId),
                    result_most_wickets_player_id: Number(mostWicketsId),
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
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
            </div>
        );
    }

    if (!matchData) {
        return (
            <div className="container-mobile py-6 space-y-4">
                <Card className="p-6 text-center space-y-3">
                    <p className="text-sm text-destructive">{error || 'Match not found'}</p>
                    <Link href="/admin">
                        <Button variant="outline" size="sm">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Admin
                        </Button>
                    </Link>
                </Card>
            </div>
        );
    }

    const renderPlayerSelect = (
        value: string,
        onValueChange: (val: string) => void,
        placeholder: string
    ) => (
        <Select value={value} onValueChange={onValueChange}>
            <SelectTrigger>
                <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
                <SelectGroup>
                    <SelectLabel>{matchData.team_1.name}</SelectLabel>
                    {matchData.team_1_players.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>
                            {p.name} ({p.role})
                        </SelectItem>
                    ))}
                </SelectGroup>
                <SelectGroup>
                    <SelectLabel>{matchData.team_2.name}</SelectLabel>
                    {matchData.team_2_players.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>
                            {p.name} ({p.role})
                        </SelectItem>
                    ))}
                </SelectGroup>
            </SelectContent>
        </Select>
    );

    return (
        <div className="container-mobile py-6 space-y-5">
            {/* Back navigation */}
            <Link
                href="/admin"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="h-4 w-4" />
                Back to Admin
            </Link>

            {/* Match Header */}
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
                {/* Winner - Tappable Team Cards */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Match Winner</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {[matchData.team_1, matchData.team_2].map((team) => {
                            const isSelected = winnerId === team.id;
                            const flagSrc = getFlagUrl(team.short_name);
                            return (
                                <button
                                    key={team.id}
                                    type="button"
                                    onClick={() => setWinnerId(team.id)}
                                    className={cn(
                                        'flex flex-col items-center gap-2 p-4 rounded-lg border transition-all',
                                        'hover:border-primary/50',
                                        isSelected
                                            ? 'border-primary bg-primary/10'
                                            : 'border-border bg-card'
                                    )}
                                >
                                    {flagSrc && (
                                        <Image
                                            src={flagSrc}
                                            alt={`${team.name} flag`}
                                            width={32}
                                            height={24}
                                            className="h-6 w-8 object-cover rounded-sm"
                                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                        />
                                    )}
                                    <span className="font-semibold text-sm">{team.short_name}</span>
                                    <span className="text-xs text-muted-foreground">{team.name}</span>
                                    {isSelected && (
                                        <CheckCircle2 className="h-4 w-4 text-primary" />
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </section>

                {/* Most Runs */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Most Runs</h2>
                    </div>
                    {renderPlayerSelect(mostRunsId, setMostRunsId, 'Select player')}
                </section>

                {/* Most Wickets */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Most Wickets</h2>
                    </div>
                    {renderPlayerSelect(mostWicketsId, setMostWicketsId, 'Select player')}
                </section>

                {/* Player of the Match */}
                <section className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Star className="h-4 w-4 text-primary" />
                        <h2 className="font-semibold text-sm">Player of the Match</h2>
                    </div>
                    {renderPlayerSelect(pomId, setPomId, 'Select player')}
                </section>

                <Button
                    type="submit"
                    className="w-full"
                    size="lg"
                    disabled={isSubmitting}
                >
                    {isSubmitting ? 'Saving...' : 'Save Result & Calculate Scores'}
                </Button>
            </form>
        </div>
    );
}
