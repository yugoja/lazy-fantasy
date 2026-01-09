// API Response Types

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Team {
  id: number;
  name: string;
  short_name: string;
  logo_url: string | null;
}

export interface Player {
  id: number;
  name: string;
  team_id: number;
  role: string;
}

export interface Match {
  id: number;
  tournament_id: number;
  team_1: Team;
  team_2: Team;
  start_time: string;
  status: 'SCHEDULED' | 'COMPLETED';
}

export interface MatchPlayers {
  match_id: number;
  team_1: Team;
  team_2: Team;
  team_1_players: Player[];
  team_2_players: Player[];
}

export interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
}

export interface LeaderboardEntry {
  user_id: number;
  username: string;
  total_points: number;
  rank: number;
}

export interface Leaderboard {
  league_id: number;
  league_name: string;
  entries: LeaderboardEntry[];
}

export interface Prediction {
  id: number;
  user_id: number;
  match_id: number;
  predicted_winner_id: number;
  predicted_most_runs_player_id: number;
  predicted_most_wickets_player_id: number;
  predicted_pom_player_id: number;
  points_earned: number;
  is_processed: boolean;
}

// Request Types

export interface SignupRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface CreateLeagueRequest {
  name: string;
}

export interface JoinLeagueRequest {
  invite_code: string;
}

export interface PredictionRequest {
  match_id: number;
  predicted_winner_id: number;
  predicted_most_runs_player_id: number;
  predicted_most_wickets_player_id: number;
  predicted_pom_player_id: number;
}
