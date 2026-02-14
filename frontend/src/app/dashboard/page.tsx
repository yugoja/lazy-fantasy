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
import { Shield, ChevronRight } from 'lucide-react';

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
            const [leaguesData, matchesData, predictionsData] = await Promise.all([
                getMyLeagues(),
                getMatches(),
                getMyPredictions(),
            ]);
            setLeagues(leaguesData);
            setMatches(matchesData);
            setPredictions(predictionsData);
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

    // Get upcoming matches
    const upcomingMatches = matches
        .filter(m => m.status === 'upcoming')
        .slice(0, 3);

    return (
        <div className="container-mobile py-6 space-y-6">
            {/* Welcome Header */}
            <div>
                <h1 className="text-2xl font-bold">
                    Welcome back, <span className="text-primary">{username}</span> 👋
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                    Track your performance and make predictions
                </p>
            </div>

            {/* Stats Overview */}
            <StatsOverview
                totalPoints={totalPoints}
                accuracy={accuracy}
                totalPredictions={predictions.length}
                processedPredictions={processedPredictions}
                bestRank={1}
                streak={2}
            />

            {/* Upcoming Matches */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-bold">Upcoming Matches</h2>
                        <p className="text-xs text-muted-foreground">{upcomingMatches.length} matches</p>
                    </div>
                    <Link href="/matches">
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
                                status={match.status.toUpperCase() as 'UPCOMING' | 'LIVE' | 'COMPLETED'}
                                venue={match.venue}
                                participantCount={Math.floor(Math.random() * 50) + 10}
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
                            <Link key={league.id} href={`/leagues/${league.id}`}>
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
