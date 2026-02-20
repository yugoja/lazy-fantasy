'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { googleLogin, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';

declare global {
    interface Window {
        google?: {
            accounts: {
                id: {
                    initialize: (config: {
                        client_id: string;
                        callback: (response: { credential: string }) => void;
                    }) => void;
                    renderButton: (
                        element: HTMLElement,
                        config: {
                            theme?: string;
                            size?: string;
                            width?: number;
                            text?: string;
                        },
                    ) => void;
                };
            };
        };
    }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function GoogleSignInButton({ onError }: { onError?: (msg: string) => void }) {
    const buttonRef = useRef<HTMLDivElement>(null);
    const router = useRouter();
    const { login } = useAuth();

    const handleCredentialResponse = useCallback(
        async (response: { credential: string }) => {
            try {
                const result = await googleLogin(response.credential);
                login(result.access_token, result.username);
                router.push('/dashboard');
            } catch (err) {
                if (err instanceof ApiError) {
                    onError?.(err.message);
                } else {
                    onError?.('Google sign-in failed');
                }
            }
        },
        [login, router, onError],
    );

    useEffect(() => {
        if (!GOOGLE_CLIENT_ID || !buttonRef.current) return;

        const renderButton = () => {
            if (!window.google || !buttonRef.current) return;
            window.google.accounts.id.initialize({
                client_id: GOOGLE_CLIENT_ID,
                callback: handleCredentialResponse,
            });
            window.google.accounts.id.renderButton(buttonRef.current, {
                theme: 'outline',
                size: 'large',
                text: 'continue_with',
            });
        };

        if (window.google) {
            renderButton();
        } else {
            // GIS script may not have loaded yet — wait for it
            const interval = setInterval(() => {
                if (window.google) {
                    clearInterval(interval);
                    renderButton();
                }
            }, 100);
            return () => clearInterval(interval);
        }
    }, [handleCredentialResponse]);

    if (!GOOGLE_CLIENT_ID) return null;

    return <div ref={buttonRef} className="w-full flex justify-center" />;
}
