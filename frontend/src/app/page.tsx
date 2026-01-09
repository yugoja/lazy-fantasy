'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import styles from './home.module.css';
import Link from 'next/link';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className={styles.hero}>
      <div className={styles.heroContent}>
        <h1 className={styles.heroTitle}>
          Fantasy Cricket League
        </h1>
        <p className={styles.heroSubtitle}>
          Predict match outcomes, compete with friends, and prove you&apos;re the ultimate cricket expert.
        </p>
        <div className={styles.heroActions}>
          <Link href="/signup" className="btn btn-primary">
            Get Started
          </Link>
          <Link href="/login" className="btn btn-secondary">
            Sign In
          </Link>
        </div>

        <div className={styles.features}>
          <div className={styles.feature}>
            <div className={styles.featureIcon}>🏆</div>
            <h3>Create Leagues</h3>
            <p>Start private leagues and invite friends</p>
          </div>
          <div className={styles.feature}>
            <div className={styles.featureIcon}>🎯</div>
            <h3>Make Predictions</h3>
            <p>Predict winners and top performers</p>
          </div>
          <div className={styles.feature}>
            <div className={styles.featureIcon}>📊</div>
            <h3>Climb Leaderboards</h3>
            <p>Earn points and compete for the top spot</p>
          </div>
        </div>
      </div>
    </div>
  );
}
