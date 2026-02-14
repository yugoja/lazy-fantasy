'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import styles from './Navbar.module.css';

export default function Navbar() {
    const { isAuthenticated, username, logout, isLoading } = useAuth();

    if (isLoading) {
        return (
            <nav className={styles.navbar}>
                <div className={styles.container}>
                    <Link href="/" className={styles.logo}>
                        🏏 CrickPredict
                    </Link>
                </div>
            </nav>
        );
    }

    return (
        <nav className={styles.navbar}>
            <div className={styles.container}>
                <Link href="/" className={styles.logo}>
                    🏏 CrickPredict
                </Link>

                <div className={styles.links}>
                    {isAuthenticated ? (
                        <>
                            <Link href="/dashboard" className={styles.link}>
                                Dashboard
                            </Link>
                            <Link href="/leagues" className={styles.link}>
                                Leagues
                            </Link>
                            <Link href="/matches" className={styles.link}>
                                Matches
                            </Link>
                            <Link href="/predictions" className={styles.link}>
                                My Predictions
                            </Link>
                            <Link href="/admin" className={styles.link}>
                                Admin
                            </Link>
                            <div className={styles.userSection}>
                                <span className={styles.username}>{username}</span>
                                <button onClick={logout} className={styles.logoutBtn}>
                                    Logout
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <Link href="/login" className={styles.link}>
                                Login
                            </Link>
                            <Link href="/signup" className={`btn btn-primary ${styles.signupBtn}`}>
                                Sign Up
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
}
