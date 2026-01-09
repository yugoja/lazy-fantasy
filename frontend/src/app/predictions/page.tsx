'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyPredictions, ApiError } from '@/lib/api';
import styles from './predictions.module.css';

interface Prediction {
    id: number;
    user_id: number;
    match_id: number;
    predicted_winner_id: number;
    predicted_most_runs_player_id: number;
    predicted_most_wickets_player_id: number;
    predicted_pom_player_id: number;
    points_earned: number;
    is_processed: boolean;
}

export default function PredictionsPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [predictions, setPredictions] = useState<Prediction[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            loadPredictions();
        }
    }, [isAuthenticated]);

    const loadPredictions = async () => {
        try {
            const data = await getMyPredictions();
            setPredictions(data);
        } catch (err) {
            console.error('Failed to load predictions', err);
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
    const processedCount = predictions.filter(p => p.is_processed).length;

    return (
        <div className="page">
            <div className="container">
                <div className="page-header">
                    <h1 className="page-title">My Predictions</h1>
                    <p className="page-subtitle">Track your predictions and points</p>
                </div>

                {/* Stats Summary */}
                <div className={styles.summary}>
                    <div className={styles.summaryItem}>
                        <div className={styles.summaryValue}>{predictions.length}</div>
                        <div className={styles.summaryLabel}>Total</div>
                    </div>
                    <div className={styles.summaryItem}>
                        <div className={styles.summaryValue}>{processedCount}</div>
                        <div className={styles.summaryLabel}>Completed</div>
                    </div>
                    <div className={styles.summaryItem}>
                        <div className={styles.summaryValue}>{predictions.length - processedCount}</div>
                        <div className={styles.summaryLabel}>Pending</div>
                    </div>
                    <div className={styles.summaryItem}>
                        <div className={`${styles.summaryValue} ${styles.points}`}>{totalPoints}</div>
                        <div className={styles.summaryLabel}>Points Earned</div>
                    </div>
                </div>

                {predictions.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">🎯</div>
                        <p>You haven&apos;t made any predictions yet</p>
                        <Link href="/matches" className="btn btn-primary mt-md">
                            View Matches
                        </Link>
                    </div>
                ) : (
                    <div className={styles.predictionsList}>
                        {predictions.map((prediction) => (
                            <div key={prediction.id} className={styles.predictionCard}>
                                <div className={styles.predictionHeader}>
                                    <span className={styles.matchId}>Match #{prediction.match_id}</span>
                                    <span className={`badge ${prediction.is_processed ? 'badge-success' : 'badge-warning'}`}>
                                        {prediction.is_processed ? 'COMPLETED' : 'PENDING'}
                                    </span>
                                </div>

                                <div className={styles.predictionDetails}>
                                    <div className={styles.detailRow}>
                                        <span className={styles.label}>Winner Pick:</span>
                                        <span>Team #{prediction.predicted_winner_id}</span>
                                    </div>
                                    <div className={styles.detailRow}>
                                        <span className={styles.label}>Most Runs:</span>
                                        <span>Player #{prediction.predicted_most_runs_player_id}</span>
                                    </div>
                                    <div className={styles.detailRow}>
                                        <span className={styles.label}>Most Wickets:</span>
                                        <span>Player #{prediction.predicted_most_wickets_player_id}</span>
                                    </div>
                                    <div className={styles.detailRow}>
                                        <span className={styles.label}>Player of Match:</span>
                                        <span>Player #{prediction.predicted_pom_player_id}</span>
                                    </div>
                                </div>

                                <div className={styles.predictionFooter}>
                                    <div className={styles.pointsEarned}>
                                        {prediction.is_processed ? (
                                            <>
                                                <span className={styles.pointsLabel}>Points Earned:</span>
                                                <span className={styles.pointsValue}>{prediction.points_earned}</span>
                                            </>
                                        ) : (
                                            <span className={styles.pendingText}>Waiting for match results...</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
