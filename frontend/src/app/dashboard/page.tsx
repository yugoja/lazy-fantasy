'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, getMatches, getMyPredictions, ApiError } from '@/lib/api';
import { StatsOverview } from '@/components/StatsOverview';
import { MatchCard } from '@/components/MatchCard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Shield, ChevronRight, Zap, Target, Trophy, Clock } from 'lucide-react';

interface League {
    id: number;
    name: string;
    invite_code: string;
    owner_id: number;
}

interface Match {
    id: number;
    team_1: { name: string; short_name: string; flag_code?: string };
    team_2: { name: string; short_name: string; flag_code?: string };
    start_time: string;
    status: string;
    venue?: string;
    lineup_announced: boolean;
}

interface Prediction {
    id: number;
    match_id: number;
    points_earned: number;
    is_processed: boolean;
}

export default function DashboardPage() {
    const { isAuthenticated, username, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [leagues, setLeagues] = useState<League[]>([]);
    const [matches, setMatches] = useState<Match[]>([]);
    const [predictions, setPredictions] = useState<Prediction[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            loadData();
        }
    }, [isAuthenticated]);

    const loadData = async () => {
        try {
            const [leaguesData, matchesData, predictionsData] = await Promise.allSettled([
                getMyLeagues(),
                getMatches(),
                getMyPredictions(),
            ]);
            if (leaguesData.status === 'fulfilled') setLeagues(leaguesData.value);
            if (matchesData.status === 'fulfilled') setMatches(matchesData.value);
            if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            }
        } finally {
            setIsLoading(false);
        }
    };

    if (authLoading || isLoading) {
        return (
            <div className="container-mobile py-6 space-y-6">
                <div className="space-y-2">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-4 w-48" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                    {[...Array(4)].map((_, i) => (
                        <Skeleton key={i} className="h-24" />
                    ))}
                </div>
            </div>
        );
    }

    const totalPoints = predictions.reduce((sum, p) => sum + p.points_earned, 0);
    const processedPredictions = predictions.filter(p => p.is_processed).length;
    const accuracy = predictions.length > 0
        ? Math.round((processedPredictions / predictions.length) * 100)
        : 0;

    // Get upcoming matches (scheduled and start time in the future)
    const now = new Date();
    const upcomingMatches = matches
        .filter(m => m.status === 'SCHEDULED' && new Date(m.start_time) > now)
        .slice(0, 3);

    const predictedMatchIds = new Set(predictions.map(p => p.match_id));
    const unpredictedUpcoming = upcomingMatches.filter(m => !predictedMatchIds.has(m.id));

    const heroContent = (() => {
        if (unpredictedUpcoming.length > 0) {
            const count = unpredictedUpcoming.length;
            const next = unpredictedUpcoming[0];
            const hoursUntil = Math.round(
                (new Date(next.start_time).getTime() - Date.now()) / 36e5
            );
            const timeLabel = hoursUntil < 1
                ? 'in < 1h'
                : hoursUntil < 24
                ? `in ${hoursUntil}h`
                : null;

            return (
                <div className="rounded-xl bg-yellow-400/10 border border-yellow-400/20 p-4 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-yellow-400/20 flex items-center justify-center shrink-0">
                            <Zap className="h-5 w-5 text-yellow-400" />
                        </div>
                        <div>
                            <p className="font-bold text-base leading-tight">
                                {count === 1 ? '1 match needs your call' : `${count} matches need your call`}
                            </p>
                            {timeLabel && (
                                <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                    <Clock className="h-3 w-3" /> Next starts {timeLabel}
                                </p>
                            )}
                        </div>
                    </div>
                    <Link href="/predictions">
                        <Button size="sm" className="shrink-0 bg-yellow-400 hover:bg-yellow-500 text-black">Predict</Button>
                    </Link>
                </div>
            );
        }

        if (upcomingMatches.length > 0) {
            const next = upcomingMatches[0];
            const hoursUntil = Math.round(
                (new Date(next.start_time).getTime() - Date.now()) / 36e5
            );
            const timeLabel = hoursUntil < 24 ? `in ${hoursUntil}h` : `in ${Math.round(hoursUntil / 24)}d`;

            return (
                <div className="rounded-xl bg-green-500/10 border border-green-500/20 p-4 flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-green-500/20 flex items-center justify-center shrink-0">
                        <Target className="h-5 w-5 text-green-500" />
                    </div>
                    <div>
                        <p className="font-bold text-base leading-tight">You&apos;re locked in</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            All predictions made · next match {timeLabel}
                        </p>
                    </div>
                </div>
            );
        }

        return (
            <div className="rounded-xl bg-muted/50 border border-border p-4 flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Trophy className="h-5 w-5 text-primary" />
                </div>
                <div>
                    <p className="font-bold text-base leading-tight">{totalPoints} pts total</p>
                    <p className="text-xs text-muted-foreground mt-0.5">No upcoming matches right now</p>
                </div>
            </div>
        );
    })();

    return (
        <div className="container-mobile py-6 space-y-6">
            {heroContent}

            {/* Stats Overview */}
            <StatsOverview
                totalPoints={totalPoints}
                accuracy={accuracy}
                totalPredictions={predictions.length}
                processedPredictions={processedPredictions}
            />

            {/* Upcoming Matches */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-bold">Upcoming Matches</h2>
                        <p className="text-xs text-muted-foreground">{upcomingMatches.length} matches</p>
                    </div>
                    <Link href="/predictions">
                        <Button variant="ghost" size="sm" className="text-xs">
                            View All
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    </Link>
                </div>

                {upcomingMatches.length === 0 ? (
                    <Card className="p-6 text-center">
                        <p className="text-sm text-muted-foreground">No upcoming matches</p>
                    </Card>
                ) : (
                    <div className="space-y-3">
                        {upcomingMatches.map((match) => (
                            <MatchCard
                                key={match.id}
                                id={match.id}
                                team1={match.team_1}
                                team2={match.team_2}
                                startTime={match.start_time}
                                status={match.status as 'SCHEDULED' | 'LIVE' | 'COMPLETED'}
                                venue={match.venue}
                                hasPredicted={predictedMatchIds.has(match.id)}
                                lineupAnnounced={match.lineup_announced}
                            />
                        ))}
                    </div>
                )}
            </section>

            {/* My Leagues */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-bold">My Leagues</h2>
                        <p className="text-xs text-muted-foreground">{leagues.length} leagues</p>
                    </div>
                    <Link href="/leagues">
                        <Button variant="ghost" size="sm" className="text-xs">
                            View All
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    </Link>
                </div>

                {leagues.length === 0 ? (
                    <Card className="p-6 text-center space-y-3">
                        <p className="text-sm text-muted-foreground">You haven't joined any leagues yet</p>
                        <Link href="/leagues">
                            <Button size="sm">Join or Create League</Button>
                        </Link>
                    </Card>
                ) : (
                    <div className="space-y-3">
                        {leagues.slice(0, 3).map((league) => (
                            <Link key={league.id} href={`/leaderboard?league=${league.id}`}>
                                <Card className="p-4 hover:border-primary/50 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                                <Shield className="h-5 w-5 text-primary" />
                                            </div>
                                            <div>
                                                <div className="font-semibold text-sm">{league.name}</div>
                                                <Badge variant="outline" className="text-[10px] mt-1">
                                                    {league.invite_code}
                                                </Badge>
                                            </div>
                                        </div>
                                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                                    </div>
                                </Card>
                            </Link>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
