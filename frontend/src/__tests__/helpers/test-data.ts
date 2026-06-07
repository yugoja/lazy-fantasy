export const mockTeam1 = {
  id: 1,
  name: 'India',
  short_name: 'IND',
  logo_url: null,
};

export const mockTeam2 = {
  id: 2,
  name: 'Australia',
  short_name: 'AUS',
  logo_url: null,
};

export const mockPlayers = {
  team_1_players: [
    { id: 101, name: 'Virat Kohli', team_id: 1, role: 'batsman', played_last_match: true },
    { id: 102, name: 'Rohit Sharma', team_id: 1, role: 'batsman', played_last_match: true },
    { id: 103, name: 'Jasprit Bumrah', team_id: 1, role: 'bowler', played_last_match: false },
  ],
  team_2_players: [
    { id: 201, name: 'Steve Smith', team_id: 2, role: 'batsman', played_last_match: true },
    { id: 202, name: 'Pat Cummins', team_id: 2, role: 'bowler', played_last_match: false },
    { id: 203, name: 'Mitchell Starc', team_id: 2, role: 'bowler', played_last_match: true },
  ],
};

export const mockMatchPlayersResponse = {
  match_id: 42,
  team_1: { id: 1, name: 'India', short_name: 'IND' },
  team_2: { id: 2, name: 'Australia', short_name: 'AUS' },
  team_1_form: [
    { match_id: 31, opponent_short_name: 'ENG', result: 'W' as const, start_time: '2026-04-21T14:00:00Z' },
    { match_id: 29, opponent_short_name: 'NZ', result: 'W' as const, start_time: '2026-04-18T14:00:00Z' },
    { match_id: 27, opponent_short_name: 'SA', result: 'L' as const, start_time: '2026-04-15T14:00:00Z' },
    { match_id: 24, opponent_short_name: 'PAK', result: 'NR' as const, start_time: '2026-04-12T14:00:00Z' },
    { match_id: 20, opponent_short_name: 'SL', result: 'W' as const, start_time: '2026-04-09T14:00:00Z' },
  ],
  team_2_form: [
    { match_id: 32, opponent_short_name: 'NZ', result: 'L' as const, start_time: '2026-04-22T14:00:00Z' },
    { match_id: 30, opponent_short_name: 'ENG', result: 'W' as const, start_time: '2026-04-19T14:00:00Z' },
    { match_id: 28, opponent_short_name: 'SA', result: 'W' as const, start_time: '2026-04-16T14:00:00Z' },
    { match_id: 25, opponent_short_name: 'PAK', result: 'L' as const, start_time: '2026-04-13T14:00:00Z' },
    { match_id: 21, opponent_short_name: 'SL', result: 'W' as const, start_time: '2026-04-10T14:00:00Z' },
  ],
  lineup_announced: false,
  start_time: new Date(Date.now() + 3600000).toISOString(),
  sport: 'cricket',
  stage: null,
  ...mockPlayers,
};

export const mockExistingPrediction = {
  id: 99,
  user_id: 1,
  match_id: 42,
  predicted_winner_id: 1,
  predicted_most_runs_team1_player_id: 101,
  predicted_most_runs_team2_player_id: 201,
  predicted_most_wickets_team1_player_id: 103,
  predicted_most_wickets_team2_player_id: 202,
  predicted_pom_player_id: 101,
  points_earned: 0,
  is_processed: false,
};

export const mockLeagues = [
  { id: 10, name: 'Test League', invite_code: 'ABC123', owner_id: 1, sport: 'cricket', image_url: null },
  { id: 20, name: 'Another League', invite_code: 'DEF456', owner_id: 2, sport: 'cricket', image_url: null },
];

export const mockLeaderboardEntries = [
  { user_id: 1, username: 'alice', total_points: 150, rank: 1, rank_delta: null, is_owner: true, avatar_url: null },
  { user_id: 2, username: 'bob', total_points: 120, rank: 2, rank_delta: 1, is_owner: false, avatar_url: null },
  { user_id: 3, username: 'testuser', total_points: 100, rank: 3, rank_delta: -1, is_owner: false, avatar_url: null },
  { user_id: 4, username: 'dave', total_points: 80, rank: 4, rank_delta: null, is_owner: false, avatar_url: null },
];

export const mockLeaderboardResponse = {
  league_id: 10,
  league_name: 'Test League',
  entries: mockLeaderboardEntries,
  available_rounds: ['GROUP_1', 'GROUP_2', 'GROUP_3', 'R16', 'QF', 'SF', 'FINAL'],
};

// ---- Match Verdict test data ----

import type { DugoutEvent, VerdictWinner, VerdictRunner } from '@/lib/api';

const allHits = { winner: true, runs_t1: true, runs_t2: true, wkts_t1: true, wkts_t2: true, pom: true };
const noHits = { winner: false, runs_t1: false, runs_t2: false, wkts_t1: false, wkts_t2: false, pom: false };

export function makeWinner(overrides: Partial<VerdictWinner> = {}): VerdictWinner {
  return {
    user_id: 10,
    username: 'alice',
    display_name: 'Alice',
    points_earned: 140,
    hits: allHits,
    prev_rank: 2,
    new_rank: 1,
    ...overrides,
  };
}

export function makeRunner(overrides: Partial<VerdictRunner> = {}): VerdictRunner {
  return {
    user_id: 20,
    username: 'bob',
    display_name: 'Bob',
    points_earned: 30,
    prev_rank: 3,
    new_rank: 2,
    ...overrides,
  };
}

function makeVerdictBase(overrides: Partial<DugoutEvent> = {}): DugoutEvent {
  return {
    type: 'match_verdict' as const,
    league_name: 'Office Squad',
    league_id: 5,
    match_id: 24,
    username: 'alice',
    display_name: 'Alice',
    is_me: false,
    streak_count: null,
    rank: null,
    rank_delta: null,
    agreement_count: null,
    team_short_name: null,
    pom_player_name: 'Virat Kohli',
    winning_team_short: 'IND',
    losing_team_short: 'AUS',
    match_label: 'M24',
    top_score: 140,
    runner_up_score: 30,
    winners: [makeWinner()],
    runners_up: [makeRunner()],
    ...overrides,
  };
}

/** Solo flawless winner — default viewer is NOT the winner */
export const mockVerdictSolo = makeVerdictBase();

/** You-won variant: viewer's username matches the winner */
export const mockVerdictYouWon = makeVerdictBase({
  is_me: true,
  username: 'testuser',
  winners: [makeWinner({ user_id: 99, username: 'testuser', display_name: 'Test User' })],
});

/** Cold variant: top_score ≤ 30, viewer is not the winner */
export const mockVerdictCold = makeVerdictBase({
  top_score: 20,
  runner_up_score: 10,
  winners: [makeWinner({ points_earned: 20 })],
  runners_up: [makeRunner({ points_earned: 10 })],
});

/** 2-way tie */
export const mockVerdictTwoWayTie = makeVerdictBase({
  top_score: 80,
  runner_up_score: 30,
  winners: [
    makeWinner({ user_id: 10, username: 'alice', display_name: 'Alice', points_earned: 80 }),
    makeWinner({ user_id: 11, username: 'carol', display_name: 'Carol', points_earned: 80 }),
  ],
});

/** 3-way tie */
export const mockVerdictThreeWayTie = makeVerdictBase({
  top_score: 60,
  runner_up_score: 30,
  winners: [
    makeWinner({ user_id: 10, username: 'alice', display_name: 'Alice', points_earned: 60 }),
    makeWinner({ user_id: 11, username: 'carol', display_name: 'Carol', points_earned: 60 }),
    makeWinner({ user_id: 12, username: 'dave', display_name: 'Dave', points_earned: 60 }),
  ],
});

/** Tight margin: solo winner with runner-up within 5 pts */
export const mockVerdictTightMargin = makeVerdictBase({
  top_score: 75,
  runner_up_score: 72,
  winners: [makeWinner({ points_earned: 75 })],
  runners_up: [makeRunner({ points_earned: 72 })],
});
