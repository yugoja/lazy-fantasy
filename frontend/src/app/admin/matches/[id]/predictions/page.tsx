'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ArrowLeft, BarChart3 } from 'lucide-react';

interface Prediction {
    id: number;
    user_id: number;
    username: string;
    display_name: string | null;
    predicted_winner: string;
    predicted_most_runs: string;
    predicted_most_wickets: string;
    predicted_pom: string;
    points_earned: number;
    is_processed: boolean;
}

interface MatchPredictions {
    match_id: number;
    team_1: { id: number; name: string; short_name: string };
    team_2: { id: number; name: string; short_name: string };
    status: string;
    predictions: Prediction[];
}

export default function ViewPredictionsPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const matchId = Number(params.id);

    const [data, setData] = useState<MatchPredictions | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (matchId && isAuthenticated) {
            loadPredictions();
        }
    }, [matchId, isAuthenticated]);

    const loadPredictions = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE}/admin/matches/${matchId}/predictions`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) throw new Error('Failed to load predictions');
            const result = await response.json();
            setData(result);
        } catch {
            setError('Failed to load predictions');
        } finally {
            setIsLoading(false);
        }
    };

    if (authLoading || isLoading) {
        return (
            <div className="container-mobile py-6 space-y-6">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-40" />
                {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-28" />
                ))}
            </div>
        );
    }

    if (!data) {
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

    const totalPoints = data.predictions.reduce((sum, p) => sum + p.points_earned, 0);
    const avgPoints = data.predictions.length > 0
        ? (totalPoints / data.predictions.length).toFixed(1)
        : '0';

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
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-bold">
                        {data.team_1.short_name} vs {data.team_2.short_name}
                    </h1>
                    <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary" className="text-[10px]">
                            {data.predictions.length} predictions
                        </Badge>
                        <Badge
                            variant={data.status === 'COMPLETED' ? 'default' : 'outline'}
                            className="text-[10px]"
                        >
                            {data.status}
                        </Badge>
                    </div>
                </div>
                {data.status === 'SCHEDULED' && (
                    <Link href={`/admin/matches/${matchId}/result`}>
                        <Button size="sm" className="text-xs">Set Result</Button>
                    </Link>
                )}
            </div>

            {/* Predictions List */}
            {data.predictions.length === 0 ? (
                <Card className="border-border bg-card">
                    <CardContent className="p-8 text-center space-y-2">
                        <BarChart3 className="h-8 w-8 text-muted-foreground mx-auto" />
                        <p className="text-sm text-muted-foreground">No predictions for this match yet</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-2">
                    {data.predictions.map((pred) => (
                        <Card key={pred.id} className="border-border bg-card">
                            <CardContent className="p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Avatar className="h-8 w-8">
                                            <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                                                {(pred.display_name || pred.username).substring(0, 2).toUpperCase()}
                                            </AvatarFallback>
                                        </Avatar>
                                        <span className="font-semibold text-sm">{pred.display_name || pred.username}</span>
                                    </div>
                                    {pred.is_processed ? (
                                        <Badge variant="default" className="text-[10px]">
                                            {pred.points_earned} pts
                                        </Badge>
                                    ) : (
                                        <Badge variant="outline" className="text-[10px]">
                                            Pending
                                        </Badge>
                                    )}
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground text-[10px]">Winner</span>
                                        <span className="font-medium">{pred.predicted_winner}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground text-[10px]">Most Runs</span>
                                        <span className="font-medium">{pred.predicted_most_runs}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground text-[10px]">Most Wickets</span>
                                        <span className="font-medium">{pred.predicted_most_wickets}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground text-[10px]">POM</span>
                                        <span className="font-medium">{pred.predicted_pom}</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Summary Card */}
            {data.status === 'COMPLETED' && data.predictions.length > 0 && (
                <Card className="border-primary/20 bg-primary/5">
                    <CardContent className="p-4">
                        <h3 className="font-semibold text-sm mb-3">Summary</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-[10px] text-muted-foreground">Total Points</p>
                                <p className="text-lg font-bold">{totalPoints}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-muted-foreground">Average Points</p>
                                <p className="text-lg font-bold">{avgPoints}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
