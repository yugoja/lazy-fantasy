'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { createLeague, ApiError } from '@/lib/api';
import styles from './create.module.css';

export default function CreateLeaguePage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const router = useRouter();
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    if (!authLoading && !isAuthenticated) {
        router.push('/login');
        return null;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!name.trim()) {
            setError('Please enter a league name');
            return;
        }

        setIsLoading(true);

        try {
            const league = await createLeague(name.trim());
            router.push(`/leagues/${league.id}`);
        } catch (err) {
            if (err instanceof ApiError) {
                setError(err.message);
            } else {
                setError('Failed to create league');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="page">
            <div className="container">
                <div className={styles.createCard}>
                    <Link href="/leagues" className={styles.backLink}>
                        ← Back to Leagues
                    </Link>

                    <h1 className={styles.title}>Create a New League</h1>
                    <p className={styles.subtitle}>
                        Start your own fantasy cricket league and invite friends to compete
                    </p>

                    {error && <div className="alert alert-error">{error}</div>}

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">League Name</label>
                            <input
                                type="text"
                                className="form-input"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Office Cricket League"
                                maxLength={100}
                            />
                        </div>

                        <button
                            type="submit"
                            className={`btn btn-primary ${styles.submitBtn}`}
                            disabled={isLoading}
                        >
                            {isLoading ? 'Creating...' : 'Create League'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
