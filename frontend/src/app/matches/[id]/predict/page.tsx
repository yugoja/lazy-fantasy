'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, submitPrediction, ApiError } from '@/lib/api';
import { getTeamLogo } from '@/lib/teams';
import styles from './predict.module.css';

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

export default function PredictPage() {
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
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to load match data');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!winnerId || !mostRunsId || !mostWicketsId || !pomId) {
            setError('Please fill in all predictions');
            return;
        }

        setIsSubmitting(true);

        try {
            await submitPrediction({
                match_id: matchId,
                predicted_winner_id: winnerId as number,
                predicted_most_runs_player_id: mostRunsId as number,
                predicted_most_wickets_player_id: mostWicketsId as number,
                predicted_pom_player_id: pomId as number,
            });
            setSuccess('Prediction submitted successfully!');
            setTimeout(() => router.push('/predictions'), 1500);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to submit prediction');
            }
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
                    <Link href="/matches" className="btn btn-secondary">
                        ← Back to Matches
                    </Link>
                </div>
            </div>
        );
    }

    const allPlayers = [...matchData.team_1_players, ...matchData.team_2_players];

    return (
        <div className="page">
            <div className="container">
                <Link href="/matches" className={styles.backLink}>
                    ← Back to Matches
                </Link>

                <div className={styles.matchHeader}>
                    <div className={styles.matchTeams}>
                        <div className={styles.headerTeam}>
                            {getTeamLogo(matchData.team_1.short_name) && (
                                <img src={getTeamLogo(matchData.team_1.short_name)} alt={matchData.team_1.short_name} />
                            )}
                            <span>{matchData.team_1.short_name}</span>
                        </div>
                        <span className={styles.headerVs}>VS</span>
                        <div className={styles.headerTeam}>
                            {getTeamLogo(matchData.team_2.short_name) && (
                                <img src={getTeamLogo(matchData.team_2.short_name)} alt={matchData.team_2.short_name} />
                            )}
                            <span>{matchData.team_2.short_name}</span>
                        </div>
                    </div>
                    <p className="page-subtitle">Make your prediction</p>
                </div>

                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                <form onSubmit={handleSubmit} className={styles.form}>
                    {/* Winner Prediction */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            🏆 Who will win? <span className={styles.points}>+10 pts</span>
                        </h2>
                        <div className={styles.teamSelect}>
                            <label
                                className={`${styles.teamOption} ${winnerId === matchData.team_1.id ? styles.selected : ''}`}
                            >
                                <input
                                    type="radio"
                                    name="winner"
                                    value={matchData.team_1.id}
                                    checked={winnerId === matchData.team_1.id}
                                    onChange={() => setWinnerId(matchData.team_1.id)}
                                />
                                {getTeamLogo(matchData.team_1.short_name) && (
                                    <img src={getTeamLogo(matchData.team_1.short_name)} alt={matchData.team_1.short_name} className={styles.optionLogo} />
                                )}
                                <span className={styles.teamName}>{matchData.team_1.name}</span>
                            </label>
                            <label
                                className={`${styles.teamOption} ${winnerId === matchData.team_2.id ? styles.selected : ''}`}
                            >
                                <input
                                    type="radio"
                                    name="winner"
                                    value={matchData.team_2.id}
                                    checked={winnerId === matchData.team_2.id}
                                    onChange={() => setWinnerId(matchData.team_2.id)}
                                />
                                {getTeamLogo(matchData.team_2.short_name) && (
                                    <img src={getTeamLogo(matchData.team_2.short_name)} alt={matchData.team_2.short_name} className={styles.optionLogo} />
                                )}
                                <span className={styles.teamName}>{matchData.team_2.name}</span>
                            </label>
                        </div>
                    </div>

                    {/* Most Runs */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            🏏 Most Runs <span className={styles.points}>+20 pts</span>
                        </h2>
                        <select
                            className="form-select"
                            value={mostRunsId}
                            onChange={(e) => setMostRunsId(Number(e.target.value))}
                        >
                            <option value="">Select a player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    {/* Most Wickets */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            🎯 Most Wickets <span className={styles.points}>+20 pts</span>
                        </h2>
                        <select
                            className="form-select"
                            value={mostWicketsId}
                            onChange={(e) => setMostWicketsId(Number(e.target.value))}
                        >
                            <option value="">Select a player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    {/* Player of the Match */}
                    <div className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            ⭐ Player of the Match <span className={styles.points}>+50 pts</span>
                        </h2>
                        <select
                            className="form-select"
                            value={pomId}
                            onChange={(e) => setPomId(Number(e.target.value))}
                        >
                            <option value="">Select a player</option>
                            <optgroup label={matchData.team_1.name}>
                                {matchData.team_1_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                            <optgroup label={matchData.team_2.name}>
                                {matchData.team_2_players.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.name} ({p.role})
                                    </option>
                                ))}
                            </optgroup>
                        </select>
                    </div>

                    <div className={styles.maxPoints}>
                        Maximum possible points: <strong>100</strong>
                    </div>

                    <button
                        type="submit"
                        className={`btn btn-primary ${styles.submitBtn}`}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Submitting...' : 'Submit Prediction'}
                    </button>
                </form>
            </div>
        </div>
    );
}
