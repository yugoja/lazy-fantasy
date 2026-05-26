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

    if (response.status === 204) {
        return null as unknown as T;
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

    return response.json() as Promise<{ access_token: string; token_type: string; display_name?: string | null }>;
}

export async function googleLogin(credential: string) {
    return request<{ access_token: string; token_type: string; username: string; display_name: string | null }>('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ credential }),
    });
}

export async function getMe() {
    return request<{ id: number; username: string; email: string; display_name: string | null }>('/auth/me');
}

export async function updateProfile(displayName: string) {
    return request<{ id: number; username: string; email: string; display_name: string | null }>('/auth/me', {
        method: 'PUT',
        body: JSON.stringify({ display_name: displayName }),
    });
}

// Leagues
export async function getLeaguePreview(inviteCode: string) {
    return request<{ name: string; invite_code: string; member_count: number }>(
        `/leagues/preview/${inviteCode}`,
    );
}

export async function getMyLeagues() {
    return request<Array<{ id: number; name: string; invite_code: string; owner_id: number; sport: string }>>('/leagues/my');
}

export async function createLeague(name: string, sport: string = 'cricket') {
    return request<{ id: number; name: string; invite_code: string; owner_id: number; sport: string }>('/leagues/', {
        method: 'POST',
        body: JSON.stringify({ name, sport }),
    });
}

export async function joinLeague(inviteCode: string) {
    return request<{ id: number; name: string; invite_code: string; owner_id: number }>('/leagues/join', {
        method: 'POST',
        body: JSON.stringify({ invite_code: inviteCode }),
    });
}

export interface FriendPrediction {
    username: string;
    display_name: string | null;
    is_me: boolean;
    points_earned: number;
    is_processed: boolean;
    predicted_winner: { id: number; name: string; short_name: string };
    predicted_most_runs_team1_player: { id: number; name: string; team_id: number; role: string };
    predicted_most_runs_team2_player: { id: number; name: string; team_id: number; role: string };
    predicted_most_wickets_team1_player: { id: number; name: string; team_id: number; role: string };
    predicted_most_wickets_team2_player: { id: number; name: string; team_id: number; role: string };
    predicted_pom_player: { id: number; name: string; team_id: number; role: string };
    actual_winner: { id: number; name: string; short_name: string } | null;
    actual_most_runs_team1_player: { id: number; name: string; team_id: number; role: string } | null;
    actual_most_runs_team2_player: { id: number; name: string; team_id: number; role: string } | null;
    actual_most_wickets_team1_player: { id: number; name: string; team_id: number; role: string } | null;
    actual_most_wickets_team2_player: { id: number; name: string; team_id: number; role: string } | null;
    actual_pom_player: { id: number; name: string; team_id: number; role: string } | null;
}

export async function getLeagueMatchPredictions(leagueId: number, matchId: number) {
    return request<FriendPrediction[]>(`/leagues/${leagueId}/matches/${matchId}/predictions`);
}

export async function getLeaderboard(leagueId: number) {
    return request<{
        league_id: number;
        league_name: string;
        entries: Array<{ user_id: number; username: string; total_points: number; rank: number; rank_delta: number | null }>;
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
export interface TeamFormEntry {
    match_id: number;
    opponent_short_name: string;
    result: 'W' | 'L' | 'NR';
    start_time: string;
}

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
    sport?: 'cricket';
    id: number;
    match_id: number;
    points_earned: number;
    is_processed: boolean;
    team_1: TeamInfo;
    team_2: TeamInfo;
    start_time: string;
    status: string;
    predicted_winner: TeamInfo;
    predicted_most_runs_team1_player: PlayerInfo;
    predicted_most_runs_team2_player: PlayerInfo;
    predicted_most_wickets_team1_player: PlayerInfo;
    predicted_most_wickets_team2_player: PlayerInfo;
    predicted_pom_player: PlayerInfo;
    actual_winner: TeamInfo | null;
    actual_most_runs_team1_player: PlayerInfo | null;
    actual_most_runs_team2_player: PlayerInfo | null;
    actual_most_wickets_team1_player: PlayerInfo | null;
    actual_most_wickets_team2_player: PlayerInfo | null;
    actual_pom_player: PlayerInfo | null;
}

export async function getMyPredictionsDetailed() {
    return request<Array<PredictionDetail | FootballPredictionDetail>>('/predictions/my/detailed');
}

export interface FootballPlayerPickDetail {
    player: PlayerInfo;
    points: number | null;
}

export interface FootballPredictionDetail {
    sport: 'football';
    id: number;
    match_id: number;
    points_earned: number;
    is_processed: boolean;
    team_1: TeamInfo;
    team_2: TeamInfo;
    start_time: string;
    status: string;
    stage: string | null;
    team1_goals: number;
    team2_goals: number;
    advance_winner: TeamInfo | null;
    player_picks: FootballPlayerPickDetail[];
    actual_team1_goals_reg: number | null;
    actual_team2_goals_reg: number | null;
    actual_team1_goals_et: number | null;
    actual_team2_goals_et: number | null;
    actual_shootout_winner: TeamInfo | null;
    result_score: number | null;
}

/**
 * Fetch the current user's football prediction for a single match (for
 * prefilling the football predict flow), or null if none exists.
 * Hits the sport-tagged /predictions/my/detailed endpoint and narrows.
 */
export async function getMyFootballPredictionDetail(matchId: number): Promise<FootballPredictionDetail | null> {
    const all = await request<Array<PredictionDetail | FootballPredictionDetail>>('/predictions/my/detailed');
    const match = all.find(
        (p): p is FootballPredictionDetail => p.sport === 'football' && p.match_id === matchId,
    );
    return match ?? null;
}

export async function getVapidPublicKey() {
    return request<{ public_key: string }>('/notifications/vapid-public-key');
}

export async function subscribePush(endpoint: string, auth: string, p256dh: string) {
    return request<{ status: string }>('/notifications/push/subscribe', {
        method: 'POST',
        body: JSON.stringify({ endpoint, auth, p256dh }),
    });
}

export interface MatchPlayersResponse {
    match_id: number;
    team_1: { id: number; name: string; short_name: string };
    team_2: { id: number; name: string; short_name: string };
    team_1_players: Array<{ id: number; name: string; team_id: number; role: string; played_last_match: boolean }>;
    team_2_players: Array<{ id: number; name: string; team_id: number; role: string; played_last_match: boolean }>;
    team_1_form: TeamFormEntry[];
    team_2_form: TeamFormEntry[];
    lineup_announced: boolean;
    start_time: string;
    sport: string;
    stage: string | null;
}

export async function getMatchPlayers(matchId: number) {
    return request<MatchPlayersResponse>(`/matches/${matchId}/players`);
}

// Predictions
export async function submitPrediction(data: {
    match_id: number;
    predicted_winner_id: number;
    predicted_most_runs_team1_player_id: number;
    predicted_most_runs_team2_player_id: number;
    predicted_most_wickets_team1_player_id: number;
    predicted_most_wickets_team2_player_id: number;
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

export interface FootballPredictionRequest {
    match_id: number;
    team1_goals: number;
    team2_goals: number;
    advance_winner_id: number | null;
    player_pick_1_id: number;
    player_pick_2_id: number;
    player_pick_3_id: number;
}

export async function submitFootballPrediction(data: FootballPredictionRequest) {
    return request<{
        id: number;
        user_id: number;
        match_id: number;
        team1_goals: number;
        team2_goals: number;
        advance_winner_id: number | null;
        player_pick_1_id: number;
        player_pick_2_id: number;
        player_pick_3_id: number;
        points_earned: number;
        is_processed: boolean;
    }>('/predictions/football', {
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
        predicted_most_runs_team1_player_id: number;
        predicted_most_runs_team2_player_id: number;
        predicted_most_wickets_team1_player_id: number;
        predicted_most_wickets_team2_player_id: number;
        predicted_pom_player_id: number;
        points_earned: number;
        is_processed: boolean;
    }>>('/predictions/my');
}

// F1
import type { F1Race, F1RaceDetail, F1Prediction, F1PredictionDetail, F1PredictionRequest, Player } from '@/types';

export async function getF1Races(tournamentId?: number) {
    const params = new URLSearchParams({ include_completed: 'true' });
    if (tournamentId) params.set('tournament_id', String(tournamentId));
    return request<F1Race[]>(`/f1/races/?${params}`);
}

export async function getF1RaceDetail(raceId: number) {
    return request<F1RaceDetail>(`/f1/races/${raceId}`);
}

export async function getF1RaceDrivers(raceId: number) {
    return request<{ race_id: number; drivers: Player[] }>(`/f1/races/${raceId}/drivers`);
}

export async function submitF1Prediction(data: F1PredictionRequest) {
    return request<F1Prediction>('/f1/predictions/', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function getMyF1Predictions() {
    return request<F1Prediction[]>('/f1/predictions/my');
}

export async function getMyF1PredictionsDetailed() {
    return request<F1PredictionDetail[]>('/f1/predictions/my/detailed');
}

// Dugout
export interface VerdictHits {
    winner: boolean;
    runs_t1: boolean;
    runs_t2: boolean;
    wkts_t1: boolean;
    wkts_t2: boolean;
    pom: boolean;
}

export interface VerdictWinner {
    user_id: number;
    username: string;
    display_name: string | null;
    points_earned: number;
    hits: VerdictHits;
    prev_rank: number | null;
    new_rank: number;
}

export interface VerdictRunner {
    user_id: number;
    username: string;
    display_name: string | null;
    points_earned: number;
    prev_rank: number | null;
    new_rank: number;
}

export interface DugoutEvent {
    type: 'contrarian' | 'agreement' | 'streak' | 'rank_shift' | 'match_verdict';
    league_name: string;
    league_id: number;
    match_id: number | null;
    username: string;
    display_name: string | null;
    is_me: boolean;
    streak_count: number | null;
    rank: number | null;
    rank_delta: number | null;
    agreement_count: number | null;
    team_short_name: string | null;
    // Match verdict fields
    winners?: VerdictWinner[] | null;
    runners_up?: VerdictRunner[] | null;
    pom_player_name?: string | null;
    winning_team_short?: string | null;
    losing_team_short?: string | null;
    match_label?: string | null;
    top_score?: number | null;
    runner_up_score?: number | null;
}

export async function getDugoutEvents() {
    return request<DugoutEvent[]>('/dugout/');
}

export async function dismissDugoutEvent(event: DugoutEvent) {
    return request<void>('/dugout/dismiss', {
        method: 'POST',
        body: JSON.stringify({
            type: event.type,
            league_id: event.league_id,
            match_id: event.match_id,
            subject_username: event.username,
        }),
    });
}

export async function getMatchVerdict(leagueId: number, matchId: number) {
    return request<DugoutEvent>(`/leagues/${leagueId}/matches/${matchId}/verdict`);
}

// Tournament Picks
export interface TournamentSummary {
    id: number;
    name: string;
    start_date: string;
    end_date: string;
    picks_window: string;
}

export interface TournamentPicksResponse {
    tournament_id: number;
    tournament_name: string;
    picks_window: string;
    top4_team_ids: (number | null)[];
    best_batsman_player_id: number | null;
    best_bowler_player_id: number | null;
    points_earned: number;
    is_window2: boolean;
    is_processed: boolean;
}

export interface TeamPickOption {
    id: number;
    name: string;
    short_name: string;
    logo_url?: string;
}

export interface PlayerPickOption {
    id: number;
    name: string;
    role: string;
    team_id: number;
    team_name?: string;
}

export async function listTournaments() {
    return request<TournamentSummary[]>('/tournaments/');
}

export async function getTournamentPicks(tournamentId: number) {
    return request<TournamentPicksResponse>(`/tournaments/${tournamentId}/picks`);
}

export async function submitTournamentPicks(
    tournamentId: number,
    top4TeamIds: number[],
    bestBatsmanPlayerId: number | null,
    bestBowlerPlayerId: number | null,
) {
    return request<TournamentPicksResponse>(`/tournaments/${tournamentId}/picks`, {
        method: 'POST',
        body: JSON.stringify({
            top4_team_ids: top4TeamIds,
            best_batsman_player_id: bestBatsmanPlayerId,
            best_bowler_player_id: bestBowlerPlayerId,
        }),
    });
}

export async function getMatchesByTournament(tournamentId: number, includeCompleted = true) {
    const params = new URLSearchParams({ include_completed: String(includeCompleted) });
    params.set('tournament_id', String(tournamentId));
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

export async function getTournamentTeams(tournamentId: number) {
    return request<TeamPickOption[]>(`/tournaments/${tournamentId}/teams`);
}

export async function getTournamentPlayers(tournamentId: number) {
    return request<PlayerPickOption[]>(`/tournaments/${tournamentId}/players`);
}

export { ApiError, API_BASE };
