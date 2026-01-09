'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import styles from './predictions.module.css';

interface Prediction {
    id: number;
    user_id: number;
    username: string;
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
        } catch (err) {
            setError('Failed to load predictions');
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

    if (!data) {
        return (
            <div className="page">
                <div className="container">
                    <div className="alert alert-error">{error || 'Match not found'}</div>
                    <Link href="/admin" className="btn btn-secondary">
                        ← Back to Admin
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <Link href="/admin" className={styles.backLink}>
                    ← Back to Admin
                </Link>

                <div className={styles.header}>
                    <div>
                        <h1 className="page-title">
                            {data.team_1.short_name} vs {data.team_2.short_name}
                        </h1>
                        <p className="page-subtitle">
                            {data.predictions.length} predictions • Status: {data.status}
                        </p>
                    </div>
                    {data.status === 'SCHEDULED' && (
                        <Link href={`/admin/matches/${matchId}/result`} className="btn btn-primary">
                            Set Result
                        </Link>
                    )}
                </div>

                {data.predictions.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📊</div>
                        <p>No predictions for this match yet</p>
                    </div>
                ) : (
                    <div className={styles.tableWrapper}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Winner</th>
                                    <th>Most Runs</th>
                                    <th>Most Wickets</th>
                                    <th>POM</th>
                                    <th>Points</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.predictions.map((pred) => (
                                    <tr key={pred.id}>
                                        <td>
                                            <strong>{pred.username}</strong>
                                        </td>
                                        <td>{pred.predicted_winner}</td>
                                        <td>{pred.predicted_most_runs}</td>
                                        <td>{pred.predicted_most_wickets}</td>
                                        <td>{pred.predicted_pom}</td>
                                        <td>
                                            {pred.is_processed ? (
                                                <span className={styles.points}>{pred.points_earned}</span>
                                            ) : (
                                                <span className={styles.pending}>Pending</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {data.status === 'COMPLETED' && data.predictions.length > 0 && (
                    <div className={styles.summary}>
                        <h3>Summary</h3>
                        <p>
                            Total points awarded:{' '}
                            <strong>
                                {data.predictions.reduce((sum, p) => sum + p.points_earned, 0)}
                            </strong>
                        </p>
                        <p>
                            Average points:{' '}
                            <strong>
                                {(
                                    data.predictions.reduce((sum, p) => sum + p.points_earned, 0) /
                                    data.predictions.length
                                ).toFixed(1)}
                            </strong>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
