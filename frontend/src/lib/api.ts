const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'ApiError';
    }
}

async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const token = typeof window !== 'undefined'
        ? localStorage.getItem('token')
        : null;

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'An error occurred' }));

        // Token expired or invalid — clear auth and redirect to login
        if (response.status === 401 && typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            window.location.href = '/login';
            // Return a never-resolving promise to prevent callers from
            // re-rendering with error state and firing more requests
            return new Promise<T>(() => {});
        }

        const apiError = new ApiError(response.status, error.detail || 'An error occurred');
        import('@sentry/nextjs').then(Sentry => Sentry.captureException(apiError)).catch(() => {});
        throw apiError;
    }

    return response.json();
}

// Auth
export async function signup(username: string, email: string, password: string) {
    return request<{ id: number; username: string; email: string }>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ username, email, password }),
    });
}

export async function login(username: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new ApiError(response.status, error.detail || 'Login failed');
    }

    return response.json() as Promise<{ access_token: string; token_type: string }>;
}

export async function googleLogin(credential: string) {
    return request<{ access_token: string; token_type: string; username: string }>('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ credential }),
    });
}

// Leagues
export async function getMyLeagues() {
    return request<Array<{ id: number; name: string; invite_code: string; owner_id: number }>>('/leagues/my');
}

export async function createLeague(name: string) {
    return request<{ id: number; name: string; invite_code: string; owner_id: number }>('/leagues/', {
        method: 'POST',
        body: JSON.stringify({ name }),
    });
}

export async function joinLeague(inviteCode: string) {
    return request<{ id: number; name: string; invite_code: string; owner_id: number }>('/leagues/join', {
        method: 'POST',
        body: JSON.stringify({ invite_code: inviteCode }),
    });
}

export async function getLeaderboard(leagueId: number) {
    return request<{
        league_id: number;
        league_name: string;
        entries: Array<{ user_id: number; username: string; total_points: number; rank: number }>;
    }>(`/leagues/${leagueId}/leaderboard`);
}

// Matches
export async function getMatches(tournamentId?: number) {
    const params = new URLSearchParams({ include_completed: 'true' });
    if (tournamentId) params.set('tournament_id', String(tournamentId));
    return request<Array<{
        id: number;
        tournament_id: number;
        team_1: { id: number; name: string; short_name: string; logo_url: string | null };
        team_2: { id: number; name: string; short_name: string; logo_url: string | null };
        start_time: string;
        status: string;
        lineup_announced: boolean;
    }>>(`/matches/?${params}`);
}

interface TeamInfo { id: number; name: string; short_name: string; logo_url?: string | null }
interface PlayerInfo { id: number; name: string; team_id: number; role: string }

export interface MatchDetail {
    id: number;
    tournament_id: number;
    team_1: TeamInfo;
    team_2: TeamInfo;
    start_time: string;
    status: string;
    winner: TeamInfo | null;
    most_runs_player: PlayerInfo | null;
    most_wickets_player: PlayerInfo | null;
    pom_player: PlayerInfo | null;
}

export async function getMatchDetail(matchId: number) {
    return request<MatchDetail>(`/matches/${matchId}`);
}

export interface PredictionDetail {
    id: number;
    match_id: number;
    points_earned: number;
    is_processed: boolean;
    team_1: TeamInfo;
    team_2: TeamInfo;
    start_time: string;
    status: string;
    predicted_winner: TeamInfo;
    predicted_most_runs_player: PlayerInfo;
    predicted_most_wickets_player: PlayerInfo;
    predicted_pom_player: PlayerInfo;
    actual_winner: TeamInfo | null;
    actual_most_runs_player: PlayerInfo | null;
    actual_most_wickets_player: PlayerInfo | null;
    actual_pom_player: PlayerInfo | null;
}

export async function getMyPredictionsDetailed() {
    return request<PredictionDetail[]>('/predictions/my/detailed');
}

export async function getMatchPlayers(matchId: number) {
    return request<{
        match_id: number;
        team_1: { id: number; name: string; short_name: string };
        team_2: { id: number; name: string; short_name: string };
        team_1_players: Array<{ id: number; name: string; team_id: number; role: string }>;
        team_2_players: Array<{ id: number; name: string; team_id: number; role: string }>;
        lineup_announced: boolean;
    }>(`/matches/${matchId}/players`);
}

// Predictions
export async function submitPrediction(data: {
    match_id: number;
    predicted_winner_id: number;
    predicted_most_runs_player_id: number;
    predicted_most_wickets_player_id: number;
    predicted_pom_player_id: number;
}) {
    return request<{
        id: number;
        user_id: number;
        match_id: number;
        points_earned: number;
        is_processed: boolean;
    }>('/predictions/', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function getMyPredictions() {
    return request<Array<{
        id: number;
        user_id: number;
        match_id: number;
        predicted_winner_id: number;
        predicted_most_runs_player_id: number;
        predicted_most_wickets_player_id: number;
        predicted_pom_player_id: number;
        points_earned: number;
        is_processed: boolean;
    }>>('/predictions/my');
}

export { ApiError, API_BASE };
