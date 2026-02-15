'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        Sentry.captureException(error);
    }, [error]);

    return (
        <html>
            <body className="flex min-h-screen items-center justify-center bg-gray-950 text-white">
                <div className="text-center space-y-4">
                    <h2 className="text-2xl font-bold">Something went wrong</h2>
                    <p className="text-gray-400">An unexpected error occurred.</p>
                    <button
                        onClick={reset}
                        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
                    >
                        Try again
                    </button>
                </div>
            </body>
        </html>
    );
}
