'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, API_BASE } from '@/lib/api';
import styles from './result.module.css';

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
    const [winnerId, setWinnerId] = useState<number | ''>('');
    const [mostRunsId, setMostRunsId] = useState<number | ''>('');
    const [mostWicketsId, setMostWicketsId] = useState<number | ''>('');
    const [pomId, setPomId] = useState<number | ''>('');

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
        } catch (err) {
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
                    result_most_runs_player_id: mostRunsId,
                    result_most_wickets_player_id: mostWicketsId,
                    result_pom_player_id: pomId,
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
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    if (!matchData) {
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
                    <h1 className="page-title">
                        Set Match Result
                    </h1>
                    <p className="page-subtitle">
                        {matchData.team_1.name} vs {matchData.team_2.name}
                    </p>
                </div>

                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                <form onSubmit={handleSubmit} className={styles.form}>
                    {/* Winner */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>🏆 Match Winner</h2>
                        <div className={styles.teamSelect}>
                            <label className={`${styles.teamOption} ${winnerId === matchData.team_1.id ? styles.selected : ''}`}>
                                <input
                                    type="radio"
                                    name="winner"
                                    value={matchData.team_1.id}
                                    checked={winnerId === matchData.team_1.id}
                                    onChange={() => setWinnerId(matchData.team_1.id)}
                                />
                                <span>{matchData.team_1.name}</span>
                            </label>
                            <label className={`${styles.teamOption} ${winnerId === matchData.team_2.id ? styles.selected : ''}`}>
                                <input
                                    type="radio"
                                    name="winner"
                                    value={matchData.team_2.id}
                                    checked={winnerId === matchData.team_2.id}
                                    onChange={() => setWinnerId(matchData.team_2.id)}
                                />
                                <span>{matchData.team_2.name}</span>
                            </label>
                        </div>
                    </div>

                    {/* Most Runs */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>🏏 Most Runs</h2>
                        <select
                            className="form-select"
                            value={mostRunsId}
                            onChange={(e) => setMostRunsId(Number(e.target.value))}
                        >
                            <option value="">Select player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    {/* Most Wickets */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>🎯 Most Wickets</h2>
                        <select
                            className="form-select"
                            value={mostWicketsId}
                            onChange={(e) => setMostWicketsId(Number(e.target.value))}
                        >
                            <option value="">Select player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    {/* Player of Match */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>⭐ Player of the Match</h2>
                        <select
                            className="form-select"
                            value={pomId}
                            onChange={(e) => setPomId(Number(e.target.value))}
                        >
                            <option value="">Select player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name} ({p.role})</option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    <button
                        type="submit"
                        className={`btn btn-primary ${styles.submitBtn}`}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Saving...' : 'Save Result & Calculate Scores'}
                    </button>
                </form>
            </div>
        </div>
    );
}
