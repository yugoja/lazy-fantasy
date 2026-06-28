'use client';

// Initialises the posthog-js singleton on the client.
// Replaces the instrumentation-client.ts hook, which Next 16 + Turbopack
// did not reliably execute (window.posthog stayed undefined). A useEffect in
// a layout-level client component runs reliably on every page. The typed
// analytics module (lib/analytics.ts) imports the same singleton, so once this
// runs, all analytics.* calls share the initialised instance.
import { useEffect } from 'react';
import posthog from 'posthog-js';

export default function PostHogInit() {
    useEffect(() => {
        const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
        if (!key || posthog.__loaded) return;
        posthog.init(key, {
            api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST, // https://eu.i.posthog.com
            ui_host: 'https://eu.posthog.com',
            defaults: '2025-05-24', // auto SPA pageviews — do NOT also set capture_pageview
            person_profiles: 'identified_only',
        });
    }, []);

    return null;
}
