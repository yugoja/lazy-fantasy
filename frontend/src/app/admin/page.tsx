'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import styles from './admin.module.css';

interface AdminMatch {
  id: number;
  tournament_id: number;
  team_1: { id: number; name: string; short_name: string };
  team_2: { id: number; name: string; short_name: string };
  start_time: string;
  status: string;
  prediction_count: number;
}

export default function AdminPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [matches, setMatches] = useState<AdminMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadMatches();
    }
  }, [isAuthenticated]);

  const loadMatches = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/admin/matches`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to load matches');
      const data = await response.json();
      setMatches(data);
    } catch (err) {
      setError('Failed to load matches');
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

  const scheduledMatches = matches.filter(m => m.status === 'SCHEDULED');
  const completedMatches = matches.filter(m => m.status === 'COMPLETED');

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">⚙️ Admin Panel</h1>
          <p className="page-subtitle">Manage matches and view predictions</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Stats */}
        <div className={styles.stats}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{matches.length}</div>
            <div className={styles.statLabel}>Total Matches</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{scheduledMatches.length}</div>
            <div className={styles.statLabel}>Scheduled</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{completedMatches.length}</div>
            <div className={styles.statLabel}>Completed</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {matches.reduce((sum, m) => sum + m.prediction_count, 0)}
            </div>
            <div className={styles.statLabel}>Predictions</div>
          </div>
        </div>

        {/* Scheduled Matches */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>🕐 Scheduled Matches</h2>
          {scheduledMatches.length === 0 ? (
            <p className="text-muted">No scheduled matches</p>
          ) : (
            <div className={styles.matchesTable}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Match</th>
                    <th>Date</th>
                    <th>Predictions</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scheduledMatches.map((match) => (
                    <tr key={match.id}>
                      <td>
                        <strong>{match.team_1.short_name}</strong> vs{' '}
                        <strong>{match.team_2.short_name}</strong>
                      </td>
                      <td>
                        {new Date(match.start_time).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td>{match.prediction_count}</td>
                      <td>
                        <div className={styles.actions}>
                          <Link
                            href={`/admin/matches/${match.id}/result`}
                            className="btn btn-primary"
                          >
                            Set Result
                          </Link>
                          <Link
                            href={`/admin/matches/${match.id}/predictions`}
                            className="btn btn-ghost"
                          >
                            View Predictions
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Completed Matches */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>✅ Completed Matches</h2>
          {completedMatches.length === 0 ? (
            <p className="text-muted">No completed matches yet</p>
          ) : (
            <div className={styles.matchesTable}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Match</th>
                    <th>Date</th>
                    <th>Predictions</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {completedMatches.map((match) => (
                    <tr key={match.id}>
                      <td>
                        <strong>{match.team_1.short_name}</strong> vs{' '}
                        <strong>{match.team_2.short_name}</strong>
                      </td>
                      <td>
                        {new Date(match.start_time).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td>{match.prediction_count}</td>
                      <td>
                        <Link
                          href={`/admin/matches/${match.id}/predictions`}
                          className="btn btn-secondary"
                        >
                          View Predictions
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
