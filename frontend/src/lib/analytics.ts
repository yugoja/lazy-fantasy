// Single source of truth for the analytics event taxonomy.
// All call sites use these functions — never `posthog.capture` directly.
// Every call is guarded: a failed capture is a no-op, never a thrown error.
// Analytics must never break the app (launch-critical on match days).
import posthog from 'posthog-js';

export type PredictionMethod = 'manual' | 'auto';
// Auto strategy keys as used in code (UI labels: Accountant / Diplomat / Chaos Merchant).
export type AutoStrategy = 'safe' | 'balanced' | 'bold';
export type ShareChannel = 'whatsapp' | 'native' | 'clipboard' | 'link' | 'other';

// Event contract. Adding/changing an event = editing this map only.
type EventMap = {
    prediction_submitted: {
        method: PredictionMethod;
        auto_strategy?: AutoStrategy; // present ONLY when method === 'auto'
        match_id: string;
        is_knockout?: boolean;
        player_picks_count?: number;
        match_day?: number;
    };
    dugout_opened: {
        event_count: number;
    };
    dugout_action: {
        action: string; // e.g. 'dismiss' | 'view_picks' | 'compare' | 'leaderboard' | 'tournament_picks'
        dugout_event_type?: string;
        match_id?: string;
        league_id?: string;
    };
    result_revealed: {
        match_id: string;
        league_id?: string;
    };
    recap_shared: {
        channel: ShareChannel;
        match_id?: string;
    };
};

const isDev = process.env.NODE_ENV === 'development';

function capture<K extends keyof EventMap>(event: K, props: EventMap[K]): void {
    try {
        posthog.capture(event, props);
    } catch (err) {
        if (isDev) console.warn('[analytics] capture failed:', event, err);
        // Swallow in prod — analytics must never break the app.
    }
}

export const analytics = {
    predictionSubmitted: (p: EventMap['prediction_submitted']) => capture('prediction_submitted', p),
    dugoutOpened: (p: EventMap['dugout_opened']) => capture('dugout_opened', p),
    dugoutAction: (p: EventMap['dugout_action']) => capture('dugout_action', p),
    resultRevealed: (p: EventMap['result_revealed']) => capture('result_revealed', p),
    recapShared: (p: EventMap['recap_shared']) => capture('recap_shared', p),

    /** Call after login / session restore to tie events to a known user. */
    identify: (distinctId: string, props?: Record<string, unknown>) => {
        try {
            posthog.identify(distinctId, props);
        } catch (err) {
            if (isDev) console.warn('[analytics] identify failed:', err);
        }
    },

    /** Call on logout so the next user on a shared device isn't merged in. */
    reset: () => {
        try {
            posthog.reset();
        } catch (err) {
            if (isDev) console.warn('[analytics] reset failed:', err);
        }
    },
};
