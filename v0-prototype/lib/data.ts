export interface Match {
  id: string
  team1: string
  team1Code: string
  team2: string
  team2Code: string
  venue: string
  date: string
  time: string
  status: "upcoming" | "live" | "completed"
  predictionsCount: number
}

export interface Prediction {
  matchId: string
  winner: string | null
  topBatsman: string | null
  topBowler: string | null
  manOfTheMatch: string | null
  submitted: boolean
}

export interface League {
  id: string
  name: string
  code: string
  members: number
  maxMembers: number
  createdBy: string
  rank: number
  points: number
}

export interface LeaderboardEntry {
  rank: number
  name: string
  avatar: string
  points: number
  correctPredictions: number
  totalPredictions: number
  streak: number
  isCurrentUser?: boolean
}

export interface Player {
  id: string
  name: string
  team: string
  role: "batsman" | "bowler" | "all-rounder" | "wicket-keeper"
}

export const matches: Match[] = [
  {
    id: "m1",
    team1: "India",
    team1Code: "IND",
    team2: "Australia",
    team2Code: "AUS",
    venue: "Melbourne Cricket Ground",
    date: "Feb 15, 2026",
    time: "14:30 IST",
    status: "upcoming",
    predictionsCount: 1247,
  },
  {
    id: "m2",
    team1: "England",
    team1Code: "ENG",
    team2: "South Africa",
    team2Code: "SA",
    venue: "Lord's Cricket Ground",
    date: "Feb 16, 2026",
    time: "15:00 IST",
    status: "upcoming",
    predictionsCount: 893,
  },
  {
    id: "m3",
    team1: "Pakistan",
    team1Code: "PAK",
    team2: "New Zealand",
    team2Code: "NZ",
    venue: "Dubai International Stadium",
    date: "Feb 14, 2026",
    time: "19:30 IST",
    status: "live",
    predictionsCount: 2156,
  },
  {
    id: "m4",
    team1: "West Indies",
    team1Code: "WI",
    team2: "Sri Lanka",
    team2Code: "SL",
    venue: "Kensington Oval",
    date: "Feb 13, 2026",
    time: "20:00 IST",
    status: "completed",
    predictionsCount: 1842,
  },
  {
    id: "m5",
    team1: "Bangladesh",
    team1Code: "BAN",
    team2: "Afghanistan",
    team2Code: "AFG",
    venue: "Sher-e-Bangla Stadium",
    date: "Feb 17, 2026",
    time: "14:00 IST",
    status: "upcoming",
    predictionsCount: 412,
  },
]

export const leagues: League[] = [
  {
    id: "l1",
    name: "Office Champions",
    code: "OFC-2026-XK9",
    members: 12,
    maxMembers: 20,
    createdBy: "Rahul S.",
    rank: 3,
    points: 245,
  },
  {
    id: "l2",
    name: "Cricket Fanatics",
    code: "CRK-FAN-77A",
    members: 8,
    maxMembers: 15,
    createdBy: "You",
    rank: 1,
    points: 310,
  },
  {
    id: "l3",
    name: "Weekend Warriors",
    code: "WKD-WAR-55B",
    members: 20,
    maxMembers: 20,
    createdBy: "Anil K.",
    rank: 7,
    points: 189,
  },
  {
    id: "l4",
    name: "IPL Predictors",
    code: "IPL-PRD-12C",
    members: 15,
    maxMembers: 25,
    createdBy: "Priya M.",
    rank: 2,
    points: 278,
  },
]

export const leaderboard: LeaderboardEntry[] = [
  { rank: 1, name: "Virat F.", avatar: "VF", points: 310, correctPredictions: 28, totalPredictions: 35, streak: 5 },
  { rank: 2, name: "Rohit K.", avatar: "RK", points: 278, correctPredictions: 25, totalPredictions: 35, streak: 3 },
  { rank: 3, name: "You", avatar: "YO", points: 245, correctPredictions: 22, totalPredictions: 35, streak: 2, isCurrentUser: true },
  { rank: 4, name: "MS Dhan.", avatar: "MD", points: 234, correctPredictions: 21, totalPredictions: 35, streak: 0 },
  { rank: 5, name: "Sachin T.", avatar: "ST", points: 220, correctPredictions: 20, totalPredictions: 35, streak: 4 },
  { rank: 6, name: "Jasprit B.", avatar: "JB", points: 198, correctPredictions: 18, totalPredictions: 35, streak: 1 },
  { rank: 7, name: "Kane W.", avatar: "KW", points: 189, correctPredictions: 17, totalPredictions: 35, streak: 0 },
  { rank: 8, name: "Ben S.", avatar: "BS", points: 176, correctPredictions: 16, totalPredictions: 35, streak: 2 },
  { rank: 9, name: "Pat C.", avatar: "PC", points: 165, correctPredictions: 15, totalPredictions: 35, streak: 1 },
  { rank: 10, name: "Babar A.", avatar: "BA", points: 155, correctPredictions: 14, totalPredictions: 35, streak: 3 },
]

export const teamFlags: Record<string, { iso: string; label: string }> = {
  IND: { iso: "in", label: "India" },
  AUS: { iso: "au", label: "Australia" },
  ENG: { iso: "gb-eng", label: "England" },
  SA: { iso: "za", label: "South Africa" },
  PAK: { iso: "pk", label: "Pakistan" },
  NZ: { iso: "nz", label: "New Zealand" },
  WI: { iso: "wi", label: "West Indies" },
  SL: { iso: "lk", label: "Sri Lanka" },
  BAN: { iso: "bd", label: "Bangladesh" },
  AFG: { iso: "af", label: "Afghanistan" },
}

export function getFlagUrl(teamCode: string, size: number = 80): string {
  const entry = teamFlags[teamCode]
  if (!entry) return ""
  // flagcdn doesn't have gb-eng or wi, use fallback
  if (entry.iso === "gb-eng") {
    return `https://flagcdn.com/w${size}/gb-eng.png`
  }
  if (entry.iso === "wi") {
    return "" // West Indies has no country flag
  }
  return `https://flagcdn.com/w${size}/${entry.iso}.png`
}

export const players: Record<string, Player[]> = {
  IND: [
    { id: "p1", name: "Virat Kohli", team: "India", role: "batsman" },
    { id: "p2", name: "Rohit Sharma", team: "India", role: "batsman" },
    { id: "p3", name: "Jasprit Bumrah", team: "India", role: "bowler" },
    { id: "p4", name: "Ravindra Jadeja", team: "India", role: "all-rounder" },
    { id: "p5", name: "KL Rahul", team: "India", role: "wicket-keeper" },
    { id: "p6", name: "Shubman Gill", team: "India", role: "batsman" },
    { id: "p7", name: "Mohammed Siraj", team: "India", role: "bowler" },
  ],
  AUS: [
    { id: "p8", name: "Steve Smith", team: "Australia", role: "batsman" },
    { id: "p9", name: "Pat Cummins", team: "Australia", role: "bowler" },
    { id: "p10", name: "Mitchell Starc", team: "Australia", role: "bowler" },
    { id: "p11", name: "Marnus Labuschagne", team: "Australia", role: "batsman" },
    { id: "p12", name: "Travis Head", team: "Australia", role: "batsman" },
    { id: "p13", name: "Josh Hazlewood", team: "Australia", role: "bowler" },
    { id: "p14", name: "Alex Carey", team: "Australia", role: "wicket-keeper" },
  ],
  ENG: [
    { id: "p15", name: "Joe Root", team: "England", role: "batsman" },
    { id: "p16", name: "Ben Stokes", team: "England", role: "all-rounder" },
    { id: "p17", name: "Jofra Archer", team: "England", role: "bowler" },
    { id: "p18", name: "Harry Brook", team: "England", role: "batsman" },
    { id: "p19", name: "Mark Wood", team: "England", role: "bowler" },
  ],
  SA: [
    { id: "p20", name: "Quinton de Kock", team: "South Africa", role: "wicket-keeper" },
    { id: "p21", name: "Kagiso Rabada", team: "South Africa", role: "bowler" },
    { id: "p22", name: "Aiden Markram", team: "South Africa", role: "batsman" },
    { id: "p23", name: "Anrich Nortje", team: "South Africa", role: "bowler" },
    { id: "p24", name: "David Miller", team: "South Africa", role: "batsman" },
  ],
  PAK: [
    { id: "p25", name: "Babar Azam", team: "Pakistan", role: "batsman" },
    { id: "p26", name: "Shaheen Afridi", team: "Pakistan", role: "bowler" },
    { id: "p27", name: "Mohammad Rizwan", team: "Pakistan", role: "wicket-keeper" },
    { id: "p28", name: "Fakhar Zaman", team: "Pakistan", role: "batsman" },
  ],
  NZ: [
    { id: "p29", name: "Kane Williamson", team: "New Zealand", role: "batsman" },
    { id: "p30", name: "Trent Boult", team: "New Zealand", role: "bowler" },
    { id: "p31", name: "Tim Southee", team: "New Zealand", role: "bowler" },
    { id: "p32", name: "Devon Conway", team: "New Zealand", role: "batsman" },
  ],
  WI: [
    { id: "p33", name: "Nicholas Pooran", team: "West Indies", role: "wicket-keeper" },
    { id: "p34", name: "Shai Hope", team: "West Indies", role: "batsman" },
    { id: "p35", name: "Alzarri Joseph", team: "West Indies", role: "bowler" },
  ],
  SL: [
    { id: "p36", name: "Charith Asalanka", team: "Sri Lanka", role: "batsman" },
    { id: "p37", name: "Wanindu Hasaranga", team: "Sri Lanka", role: "all-rounder" },
    { id: "p38", name: "Dushmantha Chameera", team: "Sri Lanka", role: "bowler" },
  ],
  BAN: [
    { id: "p39", name: "Shakib Al Hasan", team: "Bangladesh", role: "all-rounder" },
    { id: "p40", name: "Mushfiqur Rahim", team: "Bangladesh", role: "wicket-keeper" },
    { id: "p41", name: "Mustafizur Rahman", team: "Bangladesh", role: "bowler" },
  ],
  AFG: [
    { id: "p42", name: "Rashid Khan", team: "Afghanistan", role: "bowler" },
    { id: "p43", name: "Rahmanullah Gurbaz", team: "Afghanistan", role: "batsman" },
    { id: "p44", name: "Fazalhaq Farooqi", team: "Afghanistan", role: "bowler" },
  ],
}
