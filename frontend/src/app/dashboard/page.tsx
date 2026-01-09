'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, getMatches, getMyPredictions, ApiError } from '@/lib/api';
import styles from './dashboard.module.css';

interface League {
    id: number;
    name: string;
    invite_code: string;
    owner_id: number;
}

interface Match {
    id: number;
    team_1: { name: string; short_name: string };
    team_2: { name: string; short_name: string };
    start_time: string;
    status: string;
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
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    const totalPoints = predictions.reduce((sum, p) => sum + p.points_earned, 0);
    const processedPredictions = predictions.filter(p => p.is_processed).length;

    return (
        <div className="page">
            <div className="container">
                <div className="page-header">
                    <h1 className="page-title">Welcome, {username}! 👋</h1>
                    <p className="page-subtitle">Here&apos;s your fantasy cricket overview</p>
                </div>

                {error && <div className="alert alert-error">{error}</div>}

                {/* Stats */}
                <div className={styles.stats}>
                    <div className={styles.statCard}>
                        <div className={styles.statValue}>{totalPoints}</div>
                        <div className={styles.statLabel}>Total Points</div>
                    </div>
                    <div className={styles.statCard}>
                        <div className={styles.statValue}>{leagues.length}</div>
                        <div className={styles.statLabel}>Leagues Joined</div>
                    </div>
                    <div className={styles.statCard}>
                        <div className={styles.statValue}>{predictions.length}</div>
                        <div className={styles.statLabel}>Predictions Made</div>
                    </div>
                    <div className={styles.statCard}>
                        <div className={styles.statValue}>{processedPredictions}</div>
                        <div className={styles.statLabel}>Results In</div>
                    </div>
                </div>

                <div className={styles.grid}>
                    {/* Upcoming Matches */}
                    <section className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <h2>Upcoming Matches</h2>
                            <Link href="/matches" className="btn btn-ghost">View All →</Link>
                        </div>
                        {matches.length === 0 ? (
                            <div className="empty-state">
                                <p>No upcoming matches</p>
                            </div>
                        ) : (
                            <div className={styles.matchList}>
                                {matches.slice(0, 3).map((match) => (
                                    <div key={match.id} className={styles.matchCard}>
                                        <div className={styles.matchTeams}>
                                            <span className={styles.team}>{match.team_1.short_name}</span>
                                            <span className={styles.vs}>vs</span>
                                            <span className={styles.team}>{match.team_2.short_name}</span>
                                        </div>
                                        <div className={styles.matchTime}>
                                            {new Date(match.start_time).toLocaleDateString('en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                            })}
                                        </div>
                                        <Link
                                            href={`/matches/${match.id}/predict`}
                                            className="btn btn-primary"
                                        >
                                            Predict
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* My Leagues */}
                    <section className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <h2>My Leagues</h2>
                            <Link href="/leagues" className="btn btn-ghost">View All →</Link>
                        </div>
                        {leagues.length === 0 ? (
                            <div className="empty-state">
                                <p>You haven&apos;t joined any leagues yet</p>
                                <Link href="/leagues/create" className="btn btn-primary mt-md">
                                    Create League
                                </Link>
                            </div>
                        ) : (
                            <div className={styles.leagueList}>
                                {leagues.slice(0, 3).map((league) => (
                                    <Link
                                        key={league.id}
                                        href={`/leagues/${league.id}`}
                                        className={styles.leagueCard}
                                    >
                                        <div className={styles.leagueName}>{league.name}</div>
                                        <div className={styles.leagueCode}>
                                            Code: <code>{league.invite_code}</code>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
    );
}
