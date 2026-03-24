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
    { id: 101, name: 'Virat Kohli', team_id: 1, role: 'batsman' },
    { id: 102, name: 'Rohit Sharma', team_id: 1, role: 'batsman' },
    { id: 103, name: 'Jasprit Bumrah', team_id: 1, role: 'bowler' },
  ],
  team_2_players: [
    { id: 201, name: 'Steve Smith', team_id: 2, role: 'batsman' },
    { id: 202, name: 'Pat Cummins', team_id: 2, role: 'bowler' },
    { id: 203, name: 'Mitchell Starc', team_id: 2, role: 'bowler' },
  ],
};

export const mockMatchPlayersResponse = {
  match_id: 42,
  team_1: { id: 1, name: 'India', short_name: 'IND' },
  team_2: { id: 2, name: 'Australia', short_name: 'AUS' },
  lineup_announced: false,
  start_time: new Date(Date.now() + 3600000).toISOString(),
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
  { id: 10, name: 'Test League', invite_code: 'ABC123', owner_id: 1, sport: 'cricket' },
  { id: 20, name: 'Another League', invite_code: 'DEF456', owner_id: 2, sport: 'cricket' },
];

export const mockLeaderboardEntries = [
  { user_id: 1, username: 'alice', total_points: 150, rank: 1, rank_delta: null },
  { user_id: 2, username: 'bob', total_points: 120, rank: 2, rank_delta: 1 },
  { user_id: 3, username: 'testuser', total_points: 100, rank: 3, rank_delta: -1 },
  { user_id: 4, username: 'dave', total_points: 80, rank: 4, rank_delta: null },
];

export const mockLeaderboardResponse = {
  league_id: 10,
  league_name: 'Test League',
  entries: mockLeaderboardEntries,
};
