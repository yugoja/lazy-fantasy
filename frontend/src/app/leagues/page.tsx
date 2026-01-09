'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, joinLeague, ApiError } from '@/lib/api';
import styles from './leagues.module.css';

interface League {
    id: number;
    name: string;
    invite_code: string;
    owner_id: number;
}

export default function LeaguesPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [leagues, setLeagues] = useState<League[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [inviteCode, setInviteCode] = useState('');
    const [joinError, setJoinError] = useState('');
    const [joinSuccess, setJoinSuccess] = useState('');

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            loadLeagues();
        }
    }, [isAuthenticated]);

    const loadLeagues = async () => {
        try {
            const data = await getMyLeagues();
            setLeagues(data);
        } catch (err) {
            console.error('Failed to load leagues', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleJoin = async (e: React.FormEvent) => {
        e.preventDefault();
        setJoinError('');
        setJoinSuccess('');

        if (!inviteCode.trim()) {
            setJoinError('Please enter an invite code');
            return;
        }

        try {
            const newLeague = await joinLeague(inviteCode.trim().toUpperCase());
            setLeagues([...leagues, newLeague]);
            setJoinSuccess(`Successfully joined ${newLeague.name}!`);
            setInviteCode('');
        } catch (err) {
            if (err instanceof ApiError) {
                setJoinError(err.message);
            } else {
                setJoinError('Failed to join league');
            }
        }
    };

    if (authLoading || isLoading) {
        return (
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <div className="page-header flex-between">
                    <div>
                        <h1 className="page-title">My Leagues</h1>
                        <p className="page-subtitle">Manage your fantasy cricket leagues</p>
                    </div>
                    <Link href="/leagues/create" className="btn btn-primary">
                        + Create League
                    </Link>
                </div>

                {/* Join League Form */}
                <div className={styles.joinCard}>
                    <h3>Join a League</h3>
                    <form onSubmit={handleJoin} className={styles.joinForm}>
                        <input
                            type="text"
                            className="form-input"
                            placeholder="Enter invite code"
                            value={inviteCode}
                            onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                            maxLength={6}
                        />
                        <button type="submit" className="btn btn-secondary">
                            Join
                        </button>
                    </form>
                    {joinError && <p className="form-error">{joinError}</p>}
                    {joinSuccess && <p className="text-success mt-sm">{joinSuccess}</p>}
                </div>

                {/* Leagues List */}
                {leagues.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">🏆</div>
                        <p>You haven&apos;t joined any leagues yet</p>
                        <p className="text-muted">Create a new league or join one with an invite code</p>
                    </div>
                ) : (
                    <div className={styles.leaguesGrid}>
                        {leagues.map((league) => (
                            <Link
                                key={league.id}
                                href={`/leagues/${league.id}`}
                                className={styles.leagueCard}
                            >
                                <div className={styles.leagueName}>{league.name}</div>
                                <div className={styles.leagueInfo}>
                                    <span className={styles.label}>Invite Code</span>
                                    <code className={styles.code}>{league.invite_code}</code>
                                </div>
                                <div className={styles.leagueAction}>
                                    View Leaderboard →
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
