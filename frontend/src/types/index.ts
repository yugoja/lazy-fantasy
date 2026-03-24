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
  sport?: string;
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
  predicted_most_runs_team1_player_id: number;
  predicted_most_runs_team2_player_id: number;
  predicted_most_wickets_team1_player_id: number;
  predicted_most_wickets_team2_player_id: number;
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
  sport?: string;
}

export interface JoinLeagueRequest {
  invite_code: string;
}

export interface PredictionRequest {
  match_id: number;
  predicted_winner_id: number;
  predicted_most_runs_team1_player_id: number;
  predicted_most_runs_team2_player_id: number;
  predicted_most_wickets_team1_player_id: number;
  predicted_most_wickets_team2_player_id: number;
  predicted_pom_player_id: number;
}

// F1 Types
export type Sport = 'cricket' | 'f1';

export interface F1Race {
  id: number;
  tournament_id: number;
  name: string;
  circuit: string;
  start_time: string;
  status: 'SCHEDULED' | 'COMPLETED';
}

export interface F1RaceDetail extends F1Race {
  result_p1_driver: Player | null;
  result_p2_driver: Player | null;
  result_p3_driver: Player | null;
  result_fastest_lap_driver: Player | null;
  result_biggest_mover_driver: Player | null;
  result_safety_car: boolean | null;
}

export interface F1Prediction {
  id: number;
  user_id: number;
  race_id: number;
  predicted_p1_driver_id: number;
  predicted_p2_driver_id: number;
  predicted_p3_driver_id: number;
  predicted_fastest_lap_driver_id: number;
  predicted_biggest_mover_driver_id: number;
  predicted_safety_car: boolean;
  points_earned: number;
  is_processed: boolean;
  points_podium: number;
  points_fastest_lap: number;
  points_biggest_mover: number;
  points_safety_car: number;
}

export interface F1PredictionDetail {
  id: number;
  race_id: number;
  points_earned: number;
  is_processed: boolean;
  points_podium: number;
  points_fastest_lap: number;
  points_biggest_mover: number;
  points_safety_car: number;
  race_name: string;
  circuit: string;
  start_time: string;
  status: string;
  predicted_p1_driver: Player;
  predicted_p2_driver: Player;
  predicted_p3_driver: Player;
  predicted_fastest_lap_driver: Player;
  predicted_biggest_mover_driver: Player;
  predicted_safety_car: boolean;
  actual_p1_driver: Player | null;
  actual_p2_driver: Player | null;
  actual_p3_driver: Player | null;
  actual_fastest_lap_driver: Player | null;
  actual_biggest_mover_driver: Player | null;
  actual_safety_car: boolean | null;
}

export interface F1PredictionRequest {
  race_id: number;
  predicted_p1_driver_id: number;
  predicted_p2_driver_id: number;
  predicted_p3_driver_id: number;
  predicted_fastest_lap_driver_id: number;
  predicted_biggest_mover_driver_id: number;
  predicted_safety_car: boolean;
}
