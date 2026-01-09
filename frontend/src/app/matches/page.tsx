'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { getMatches } from '@/lib/api';
import { getTeamLogo } from '@/lib/teams';
import styles from './matches.module.css';

interface Match {
    id: number;
    tournament_id: number;
    team_1: { id: number; name: string; short_name: string };
    team_2: { id: number; name: string; short_name: string };
    start_time: string;
    status: string;
}

export default function MatchesPage() {
    const [matches, setMatches] = useState<Match[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadMatches();
    }, []);

    const loadMatches = async () => {
        try {
            const data = await getMatches();
            setMatches(data);
        } catch (err) {
            console.error('Failed to load matches', err);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <div className="page-header">
                    <h1 className="page-title">Upcoming Matches</h1>
                    <p className="page-subtitle">Make your predictions before the match starts</p>
                </div>

                {matches.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">🏏</div>
                        <p>No upcoming matches at the moment</p>
                        <p className="text-muted">Check back later for new matches</p>
                    </div>
                ) : (
                    <div className={styles.matchGrid}>
                        {matches.map((match) => {
                            const matchDate = new Date(match.start_time);
                            const isUpcoming = matchDate > new Date();
                            const team1Logo = getTeamLogo(match.team_1.short_name);
                            const team2Logo = getTeamLogo(match.team_2.short_name);

                            return (
                                <div key={match.id} className={styles.matchCard}>
                                    <div className={styles.matchHeader}>
                                        <span className={`badge ${isUpcoming ? 'badge-primary' : 'badge-success'}`}>
                                            {isUpcoming ? 'UPCOMING' : match.status}
                                        </span>
                                    </div>

                                    <div className={styles.teams}>
                                        <div className={styles.team}>
                                            <div className={styles.teamLogo}>
                                                {team1Logo ? (
                                                    <img src={team1Logo} alt={match.team_1.short_name} width={60} height={60} />
                                                ) : (
                                                    '🏏'
                                                )}
                                            </div>
                                            <div className={styles.teamName}>{match.team_1.name}</div>
                                            <div className={styles.teamShort}>{match.team_1.short_name}</div>
                                        </div>

                                        <div className={styles.versus}>VS</div>

                                        <div className={styles.team}>
                                            <div className={styles.teamLogo}>
                                                {team2Logo ? (
                                                    <img src={team2Logo} alt={match.team_2.short_name} width={60} height={60} />
                                                ) : (
                                                    '🏏'
                                                )}
                                            </div>
                                            <div className={styles.teamName}>{match.team_2.name}</div>
                                            <div className={styles.teamShort}>{match.team_2.short_name}</div>
                                        </div>
                                    </div>

                                    <div className={styles.matchTime}>
                                        📅 {matchDate.toLocaleDateString('en-US', {
                                            weekday: 'short',
                                            month: 'short',
                                            day: 'numeric',
                                        })}
                                        {' • '}
                                        🕐 {matchDate.toLocaleTimeString('en-US', {
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        })}
                                    </div>

                                    {isUpcoming && (
                                        <Link
                                            href={`/matches/${match.id}/predict`}
                                            className={`btn btn-primary ${styles.predictBtn}`}
                                        >
                                            Make Prediction
                                        </Link>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
