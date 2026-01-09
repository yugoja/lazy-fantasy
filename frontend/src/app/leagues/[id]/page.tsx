'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getLeaderboard, ApiError } from '@/lib/api';
import styles from './league-detail.module.css';

interface LeaderboardEntry {
    user_id: number;
    username: string;
    total_points: number;
    rank: number;
}

interface Leaderboard {
    league_id: number;
    league_name: string;
    entries: LeaderboardEntry[];
}

export default function LeagueDetailPage() {
    const { isAuthenticated, isLoading: authLoading, username } = useAuth();
    const router = useRouter();
    const params = useParams();
    const leagueId = Number(params.id);

    const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated && leagueId) {
            loadLeaderboard();
        }
    }, [isAuthenticated, leagueId]);

    const loadLeaderboard = async () => {
        try {
            const data = await getLeaderboard(leagueId);
            setLeaderboard(data);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to load leaderboard');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const copyInviteCode = () => {
        // The invite code would need to be fetched - for now we'll use league name
        navigator.clipboard.writeText(`Join my fantasy cricket league!`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (authLoading || isLoading) {
        return (
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page">
                <div className="container">
                    <div className="alert alert-error">{error}</div>
                    <Link href="/leagues" className="btn btn-secondary">
                        ← Back to Leagues
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <Link href="/leagues" className={styles.backLink}>
                    ← Back to Leagues
                </Link>

                <div className={styles.header}>
                    <div>
                        <h1 className="page-title">{leaderboard?.league_name}</h1>
                        <p className="page-subtitle">League Leaderboard</p>
                    </div>
                    <button onClick={copyInviteCode} className="btn btn-secondary">
                        {copied ? '✓ Copied!' : '📋 Share Invite'}
                    </button>
                </div>

                {leaderboard?.entries.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📊</div>
                        <p>No members yet</p>
                    </div>
                ) : (
                    <div className={styles.tableWrapper}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Player</th>
                                    <th>Points</th>
                                </tr>
                            </thead>
                            <tbody>
                                {leaderboard?.entries.map((entry) => (
                                    <tr
                                        key={entry.user_id}
                                        className={entry.username === username ? styles.currentUser : ''}
                                    >
                                        <td>
                                            <span className={styles.rank}>
                                                {entry.rank === 1 && '🥇 '}
                                                {entry.rank === 2 && '🥈 '}
                                                {entry.rank === 3 && '🥉 '}
                                                #{entry.rank}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={styles.playerName}>
                                                {entry.username}
                                                {entry.username === username && (
                                                    <span className={styles.youBadge}>You</span>
                                                )}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={styles.points}>{entry.total_points}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
