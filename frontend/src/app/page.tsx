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
    <div className={styles.landing}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.badge}>
            <span className={styles.badgeIcon}>🏏</span>
            <span>Women&apos;s Premier League 2025</span>
          </div>

          <h1 className={styles.heroTitle}>
            Your Fantasy Cricket
            <span className={styles.titleAccent}> League Awaits</span>
          </h1>

          <p className={styles.heroSubtitle}>
            Join thousands of cricket fans predicting match outcomes, competing with friends,
            and climbing leaderboards. Turn your cricket knowledge into glory!
          </p>

          <div className={styles.heroActions}>
            <Link href="/signup" className={`btn btn-primary ${styles.ctaButton}`}>
              Start Playing Free
              <span className={styles.arrow}>→</span>
            </Link>
            <Link href="/login" className={`btn btn-secondary ${styles.ctaButton}`}>
              Sign In
            </Link>
          </div>

          <div className={styles.stats}>
            <div className={styles.stat}>
              <div className={styles.statNumber}>1000+</div>
              <div className={styles.statLabel}>Active Players</div>
            </div>
            <div className={styles.stat}>
              <div className={styles.statNumber}>50+</div>
              <div className={styles.statLabel}>Live Leagues</div>
            </div>
            <div className={styles.stat}>
              <div className={styles.statNumber}>5000+</div>
              <div className={styles.statLabel}>Predictions Made</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className={styles.featuresSection}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Everything You Need to Dominate</h2>
          <p className={styles.sectionSubtitle}>
            Powerful features that make fantasy cricket exciting and competitive
          </p>
        </div>

        <div className={styles.features}>
          <div className={styles.feature}>
            <div className={styles.featureIcon}>🏆</div>
            <h3>Private Leagues</h3>
            <p>Create exclusive leagues with custom rules. Invite friends, family, or colleagues to compete.</p>
          </div>

          <div className={styles.feature}>
            <div className={styles.featureIcon}>🎯</div>
            <h3>Smart Predictions</h3>
            <p>Predict match winners, top scorers, and player performances. Earn points for accurate calls.</p>
          </div>

          <div className={styles.feature}>
            <div className={styles.featureIcon}>📊</div>
            <h3>Live Leaderboards</h3>
            <p>Track your rank in real-time. See how you stack up against competitors with detailed stats.</p>
          </div>

          <div className={styles.feature}>
            <div className={styles.featureIcon}>⚡</div>
            <h3>Instant Updates</h3>
            <p>Get real-time match updates and automatic score calculations. Never miss a moment.</p>
          </div>

          <div className={styles.feature}>
            <div className={styles.featureIcon}>🎖️</div>
            <h3>Achievement System</h3>
            <p>Unlock badges and rewards as you improve. Build your reputation as a cricket expert.</p>
          </div>

          <div className={styles.feature}>
            <div className={styles.featureIcon}>📱</div>
            <h3>Mobile Optimized</h3>
            <p>Play anywhere, anytime. Fully responsive design for seamless mobile experience.</p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className={styles.howItWorks}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>How It Works</h2>
          <p className={styles.sectionSubtitle}>
            Get started in three simple steps
          </p>
        </div>

        <div className={styles.steps}>
          <div className={styles.step}>
            <div className={styles.stepNumber}>1</div>
            <h3>Create Your Account</h3>
            <p>Sign up in seconds. No payment required. Start with a free account.</p>
          </div>

          <div className={styles.stepConnector}></div>

          <div className={styles.step}>
            <div className={styles.stepNumber}>2</div>
            <h3>Join or Create a League</h3>
            <p>Browse public leagues or create a private one. Invite your friends with a simple code.</p>
          </div>

          <div className={styles.stepConnector}></div>

          <div className={styles.step}>
            <div className={styles.stepNumber}>3</div>
            <h3>Make Predictions & Win</h3>
            <p>Predict match outcomes before each game. Earn points and climb the leaderboard!</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={styles.cta}>
        <div className={styles.ctaContent}>
          <h2 className={styles.ctaTitle}>Ready to Prove Your Cricket Knowledge?</h2>
          <p className={styles.ctaSubtitle}>
            Join the community and start competing today. It&apos;s free!
          </p>
          <Link href="/signup" className={`btn btn-primary ${styles.ctaButtonLarge}`}>
            Get Started Now
            <span className={styles.arrow}>→</span>
          </Link>
        </div>
      </section>
    </div>
  );
}
