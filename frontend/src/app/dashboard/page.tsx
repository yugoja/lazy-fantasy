'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, getMatches, getMyPredictions, getDugoutEvents, DugoutEvent, ApiError } from '@/lib/api';
import { DugoutFeed } from '@/components/DugoutFeed';
import { MatchCard } from '@/components/MatchCard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronRight, Clock, Users } from 'lucide-react';
import { OnboardingChecklist } from '@/components/OnboardingChecklist';

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
    sport?: string;
    stage?: string | null;
}

interface Prediction {
    id: number;
    match_id: number;
    points_earned: number;
    is_processed: boolean;
}

export default function DashboardPage() {
    const { isAuthenticated, username, displayName, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [leagues, setLeagues] = useState<League[]>([]);
    const [matches, setMatches] = useState<Match[]>([]);
    const [predictions, setPredictions] = useState<Prediction[]>([]);
    const [dugoutEvents, setDugoutEvents] = useState<DugoutEvent[]>([]);
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
            const [leaguesData, matchesData, predictionsData, dugoutData] = await Promise.allSettled([
                getMyLeagues(),
                getMatches(),
                getMyPredictions(),
                getDugoutEvents(),
            ]);
            if (leaguesData.status === 'fulfilled') setLeagues(leaguesData.value);
            if (matchesData.status === 'fulfilled') setMatches(matchesData.value);
            if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
            if (dugoutData.status === 'fulfilled') setDugoutEvents(dugoutData.value);
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

    const now = new Date();
    const upcomingMatches = matches
        .filter(m => m.status === 'SCHEDULED' && new Date(m.start_time) > now)
        .slice(0, 3);

    const predictedMatchIds = new Set(predictions.map(p => p.match_id));
    const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
    const todayEnd = new Date(); todayEnd.setHours(23, 59, 59, 999);
    const unpredictedToday = upcomingMatches.filter(
        m => !predictedMatchIds.has(m.id) && new Date(m.start_time) >= todayStart && new Date(m.start_time) <= todayEnd
    );

    const heroContent = (() => {
        if (unpredictedToday.length > 0) {
            const count = unpredictedToday.length;
            const next = unpredictedToday[0];
            const hoursUntil = Math.round(
                (new Date(next.start_time).getTime() - Date.now()) / 36e5
            );
            const timeLabel = hoursUntil < 1
                ? 'in < 1h'
                : hoursUntil < 24
                ? `in ${hoursUntil}h`
                : null;

            return (
                <div className="rounded-xl border-l-4 border-l-yellow-400 bg-yellow-400/15 p-4 flex items-center justify-between gap-4">
                    <div>
                        <p className="font-bold text-base leading-tight">
                            {count === 1 ? '1 match needs your call' : `${count} matches need your call`}
                        </p>
                        {timeLabel && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                                <Clock className="h-3 w-3" /> Next starts {timeLabel}
                            </p>
                        )}
                    </div>
                    <Link href="/predictions">
                        <Button size="sm" className="shrink-0 bg-yellow-400 hover:bg-yellow-500 text-black font-bold">Predict</Button>
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

            const lockedMatch = [...matches]
                .filter(m => new Date(m.start_time) < now && predictedMatchIds.has(m.id))
                .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())[0];
            const friendsPicksHref = lockedMatch && leagues.length > 0
                ? `/leagues/${leagues[0].id}/match/${lockedMatch.id}`
                : null;

            return (
                <div className="rounded-xl border-l-4 border-l-primary bg-primary/10 p-4">
                    <p className="font-bold text-base leading-tight">You&apos;re locked in</p>
                    <p className="text-xs text-muted-foreground mt-1">
                        All predictions made · next match {timeLabel}
                    </p>
                    {friendsPicksHref && (
                        <Link href={friendsPicksHref} className="inline-flex items-center gap-1 text-sm text-primary font-semibold mt-2 hover:underline">
                            <Users className="h-3.5 w-3.5" />
                            See what your league picked →
                        </Link>
                    )}
                </div>
            );
        }

        return (
            <div className="rounded-xl border-l-4 border-l-muted-foreground/30 bg-muted/30 p-4">
                <p className="font-bold text-base leading-tight">No matches yet</p>
                <p className="text-xs text-muted-foreground mt-1">Check back soon for upcoming matches</p>
            </div>
        );
    })();

    return (
        <div className="container-mobile pt-5 pb-8">
            {/* Greeting */}
            <p className="text-sm text-muted-foreground mb-1">
                {new Date().getHours() < 12 ? 'Morning' : new Date().getHours() < 17 ? 'Afternoon' : 'Evening'}, <span className="text-foreground font-semibold">{displayName || username}</span>
            </p>

            <div className="mt-4">
                <OnboardingChecklist
                    hasPredicted={predictions.length > 0}
                    hasLeague={leagues.length > 0}
                />
            </div>

            <div className="mt-4">
                {heroContent}
            </div>

            {/* Dugout — more breathing room */}
            <div className="mt-8">
                <DugoutFeed events={dugoutEvents} />
            </div>

            {/* Matches — visual separator via top border */}
            <section className="mt-8 pt-6 border-t border-border">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-bold">Upcoming</h2>
                    <Link href="/predictions">
                        <Button variant="ghost" size="sm" className="text-xs text-muted-foreground">
                            All matches
                            <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    </Link>
                </div>
                {upcomingMatches.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-6 text-center">No upcoming matches</p>
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
                                sport={match.sport as 'football' | 'cricket' | undefined}
                                stage={match.stage}
                                onAutoPickSuccess={(matchId) => {
                                    setPredictions(prev => prev.some(p => p.match_id === matchId)
                                        ? prev
                                        : [...prev, { id: -1, match_id: matchId, points_earned: 0, is_processed: false }]);
                                }}
                            />
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
