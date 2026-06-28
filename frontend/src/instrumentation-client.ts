// PostHog client-side init (Next.js App Router — runs once before hydration).
// Initialises the posthog-js singleton so the typed analytics module
// (src/lib/analytics.ts) and the auth context share the same instance.
// No-ops when the key is absent, mirroring src/lib/sentry.ts.
import posthog from 'posthog-js';

const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;

if (key) {
    posthog.init(key, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST, // https://eu.i.posthog.com
        ui_host: 'https://eu.posthog.com',
        defaults: '2026-05-30', // auto SPA pageviews — do NOT also set capture_pageview
        person_profiles: 'identified_only',
        // No cookie banner: hash a server-side identifier instead of setting cookies.
        // Requires "Cookieless server hash mode" enabled in PostHog Project Settings.
        cookieless_mode: 'on_reject',
    });
}
