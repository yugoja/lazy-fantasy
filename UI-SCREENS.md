# Lazy Fantasy — Current UI Screens

## App Shell

### Top Bar (sticky)
```
┌──────────────────────────────────────┐
│ 🏆 Lazy Fantasy              [YU]   │
└──────────────────────────────────────┘
```
- Trophy icon + wordmark (links to /dashboard)
- Right: avatar with user initials (links to /profile)
- Hidden on landing page when unauthenticated

### Bottom Nav (fixed)
```
┌──────────────────────────────────────┐
│  🏆 Home   🎯 Predict  👥 Leagues  📈 Board │
└──────────────────────────────────────┘
```
- 4 tabs, active tab highlighted in primary color
- Only shown when authenticated

---

## 1. Landing Page `/`

Redirects to `/dashboard` if authenticated.

```
┌──────────────────────────────────────┐
│                                      │
│     [ 🏆 ICC T20 World Cup 2026 ]   │
│                                      │
│        Your Fantasy Cricket          │
│         League Awaits                │
│                                      │
│   Predict match outcomes, compete    │
│   with friends, prove you know       │
│   cricket best.                      │
│                                      │
│   [Start Playing Free]  [Sign In]    │
│                                      │
├──────────────────────────────────────┤
│                                      │
│         How It Works                 │
│  Three steps to get in the game      │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 👥 Create a League             │  │
│  │ Start a private league and     │  │
│  │ invite your friends            │  │
│  ├────────────────────────────────┤  │
│  │ 🎯 Predict Every Match         │  │
│  │ Pick winners, top batsmen,     │  │
│  │ bowlers and MOM                │  │
│  ├────────────────────────────────┤  │
│  │ 📈 Climb the Leaderboard       │  │
│  │ Earn points for correct        │  │
│  │ predictions and rise to #1     │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Ready to Prove Your Cricket    │  │
│  │ Knowledge?                     │  │
│  │        [Get Started Now]       │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 2. Login `/login`

```
┌──────────────────────────────────────┐
│                                      │
│            🏆                        │
│        Welcome Back                  │
│    Sign in to your account           │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  [ Error message if any ]      │  │
│  └────────────────────────────────┘  │
│                                      │
│  [       Google Sign In          ]   │
│                                      │
│  ─────────── or ───────────         │
│                                      │
│  Username  [________________]        │
│  Password  [________________]        │
│                                      │
│  [         Sign In           ]       │
│                                      │
│  Don't have an account? Sign up      │
└──────────────────────────────────────┘
```

---

## 3. Signup `/signup`

```
┌──────────────────────────────────────┐
│                                      │
│            🏆                        │
│       Create Account                 │
│  Join the fantasy cricket league     │
│                                      │
│  [       Google Sign In          ]   │
│                                      │
│  ─────────── or ───────────         │
│                                      │
│  Username         [________________] │
│  Email            [________________] │
│  Password         [________________] │
│  Confirm Password [________________] │
│                                      │
│  [       Create Account        ]     │
│                                      │
│  Already have an account? Sign in    │
└──────────────────────────────────────┘
```

---

## 4. Dashboard `/dashboard`

```
┌──────────────────────────────────────┐
│                                      │
│  ┌────────────────────────────────┐  │
│  │ ⚡ 2 matches need your call    │  │  ← Hero nudge (yellow)
│  │ 🕐 Next starts in 4h [Predict]│  │    Only today's matches
│  └────────────────────────────────┘  │
│     OR                               │
│  ┌────────────────────────────────┐  │
│  │ 🎯 You're locked in            │  │  ← All predicted (green)
│  │ All predictions made · next 2d │  │
│  └────────────────────────────────┘  │
│     OR                               │
│  ┌────────────────────────────────┐  │
│  │ 🏆 142 pts total               │  │  ← No upcoming (muted)
│  │ No upcoming matches right now  │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌─────────┐ ┌─────────┐            │
│  │ 🏆 142  │ │ 🎯 67%  │            │  ← Stats 2x2 grid
│  │ Points  │ │ Accuracy│            │
│  ├─────────┤ ├─────────┤            │
│  │ 📈 12   │ │ 🔥 11.8 │            │
│  │ Predict.│ │ Avg Pts │            │
│  └─────────┘ └─────────┘            │
│                                      │
│  Upcoming Matches    [View All >]    │
│  3 matches                           │
│  ┌────────────────────────────────┐  │
│  │ [MatchCard]                    │  │
│  ├────────────────────────────────┤  │
│  │ [MatchCard]                    │  │
│  ├────────────────────────────────┤  │
│  │ [MatchCard]                    │  │
│  └────────────────────────────────┘  │
│                                      │
│  My Leagues          [View All >]    │
│  2 leagues                           │
│  ┌────────────────────────────────┐  │
│  │ 🛡 Office Squad   [ABC123]     │  │
│  ├────────────────────────────────┤  │
│  │ 🛡 College Gang   [XYZ789]     │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 5. Match Predictions `/predictions`

```
┌──────────────────────────────────────┐
│  Match Predictions                   │
│  Pick a match to make your           │
│  predictions.                        │
│                                      │
│  ┌──────────┬──────────┬──────────┐  │
│  │ Upcoming │ Live (2) │ Done (5) │  │
│  └──────────┴──────────┴──────────┘  │
│                                      │
│  UPCOMING TAB:                       │
│  ┌────────────────────────────────┐  │
│  │ [MatchCard with predict btn]   │  │
│  ├────────────────────────────────┤  │
│  │ [MatchCard - "Locked" no btn]  │  │
│  └────────────────────────────────┘  │
│                                      │
│  LIVE TAB:                           │
│  ┌────────────────────────────────┐  │
│  │ 🇮🇳 IND vs SA 🇿🇦     Pending  │  │
│  │ Feb 22 · SCHEDULED             │  │
│  │ 🏆 Winner    IND         +10   │  │
│  │ 🎯 Most Runs Kohli       +20   │  │
│  │ 🎯 Most Wkts Bumrah      +20   │  │
│  │ ⭐ POM       Kohli       +50   │  │
│  └────────────────────────────────┘  │
│  Or "No live matches right now"      │
│                                      │
│  DONE TAB:                           │
│  ┌────────────────────────────────┐  │
│  │ Total Points Earned     Pred.  │  │
│  │      142                  12   │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ 🇮🇳 IND vs SA 🇿🇦     +30 pts  │  │
│  │ Feb 22 · COMPLETED             │  │
│  │ 🏆 Winner    IND    ✓         │  │
│  │ 🎯 Most Runs ̶K̶o̶h̶l̶i̶  ✗ Miller │  │
│  │ 🎯 Most Wkts Bumrah  ✓        │  │
│  │ ⭐ POM       ̶K̶o̶h̶l̶i̶  ✗ Miller │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 6. Make Prediction `/matches/[id]/predict`

Redirects to `/predictions` if match has started.

```
┌──────────────────────────────────────┐
│  <- Back                             │
│                                      │
│  India vs South Africa  [Playing XI] │
│  Sat, Feb 22 · 02:30 PM             │
│                                      │
│  [████████████████░░░░] 75%          │
│  ● Winner  ● Runs  ● Wickets  ○ POM │
│                                      │
│  🏆 Match Winner              +10pts │
│  ┌───────────┐ ┌───────────┐         │
│  │  🇮🇳       │ │  🇿🇦       │         │
│  │  IND  ✓   │ │  SA       │         │
│  │  India    │ │  S.Africa │         │
│  └───────────┘ └───────────┘         │
│                                      │
│  🎯 Top Batsman (Most Runs)   +20pts │
│  ┌────┐ ┌────┐ ┌────┐               │
│  │ VK │ │ RS │ │ DM │  ...          │
│  │Kohli│ │Sharma│ │Miller│            │
│  │BAT │ │BAT │ │BAT │               │
│  │ ✓  │ │    │ │    │               │
│  └────┘ └────┘ └────┘               │
│                                      │
│  🎯 Top Bowler (Most Wickets) +20pts │
│  ┌────┐ ┌────┐ ┌────┐               │
│  │ JB │ │ ... │ │ ... │              │
│  └────┘ └────┘ └────┘               │
│                                      │
│  ⭐ Man of the Match          +50pts │
│  ┌────┐ ┌────┐ ┌────┐               │
│  │ ... │ │ ... │ │ ... │              │
│  └────┘ └────┘ └────┘               │
│                                      │
│ ─────────────────────────────────── │
│ │ 3 of 4 predictions   [Submit]  │  │  ← Sticky footer
│ ─────────────────────────────────── │
└──────────────────────────────────────┘

Success Dialog:
┌────────────────────────────┐
│           ✓                │
│  Prediction Submitted!     │
│  Your predictions for      │
│  IND vs SA have been       │
│  recorded.                 │
│  [<- Back to Matches]      │
└────────────────────────────┘
```

---

## 7. Match Detail `/matches/[id]`

```
┌──────────────────────────────────────┐
│  <- Back                             │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ COMPLETED           🕐 2:30 PM │  │
│  │                                │  │
│  │   🇮🇳          vs         🇿🇦   │  │
│  │   IND                    SA    │  │
│  │   India           South Africa │  │
│  │         [Winner]               │  │
│  │                                │  │
│  │        Sat, Feb 22             │  │
│  └────────────────────────────────┘  │
│                                      │
│  Match Results                       │
│  ┌────────────────────────────────┐  │
│  │ 🏆 Winner         India  +10  │  │
│  │ 🎯 Most Runs      Kohli  +20  │  │
│  │ 🎯 Most Wickets   Bumrah +20  │  │
│  │ ⭐ POM            Kohli  +50  │  │
│  └────────────────────────────────┘  │
│                                      │
│  If SCHEDULED:                       │
│  [      Make Prediction         ]    │
└──────────────────────────────────────┘
```

---

## 8. Leaderboard `/leaderboard`

```
┌──────────────────────────────────────┐
│  Leaderboard                         │
│                                      │
│  League: [▼ Office Squad        ]    │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ #3        You       142 pts   │  │  ← Your rank card
│  │                    [Top 25%]  │  │
│  └────────────────────────────────┘  │
│                                      │
│     🥈            🥇           🥉     │
│    Rahul        Virat        Rohit   │  ← Podium
│   198 pts      256 pts      142 pts  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 1  [VK] Virat         256 pts │  │
│  │ 2  [RS] Rahul         198 pts │  │
│  │ 3  [RH] Rohit  You    142 pts │  │  ← Full rankings
│  │ 4  [MS] Mahesh        120 pts │  │
│  │ 5  [AP] Arjun          98 pts │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 9. My Leagues `/leagues`

```
┌──────────────────────────────────────┐
│  My Leagues            [Join][Create]│
│  Create or join leagues to compete.  │
│                                      │
│  [2 Leagues]                         │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 🛡 Office Squad                │  │
│  │   [ABC123]    [Share] [Board>] │  │
│  ├────────────────────────────────┤  │
│  │ 🛡 College Gang                │  │
│  │   [XYZ789]    [Share] [Board>] │  │
│  └────────────────────────────────┘  │
│                                      │
│  Join Dialog:                        │
│  ┌────────────────────────────────┐  │
│  │ Join a League                  │  │
│  │ Enter the league code          │  │
│  │ League Code [______________]   │  │
│  │ [       Join League       ]    │  │
│  └────────────────────────────────┘  │
│                                      │
│  Create Dialog:                      │
│  ┌────────────────────────────────┐  │
│  │ Create a New League            │  │
│  │ League Name [______________]   │  │
│  │ [      Create League      ]    │  │
│  └────────────────────────────────┘  │
│                                      │
│  Created Confirmation:               │
│  ┌────────────────────────────────┐  │
│  │ League Created!                │  │
│  │ League Code:                   │  │
│  │ ┌──────────────────────────┐   │  │
│  │ │       ABC123             │   │  │
│  │ └──────────────────────────┘   │  │
│  │ [invite link............] [📋] │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 10. Profile `/profile`

```
┌──────────────────────────────────────┐
│                                      │
│           ┌────┐                     │
│           │ YU │  🏆                  │
│           └────┘                     │
│           yugoja21                   │
│           @yugoja21                  │
│                                      │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ 🏆 142  │ │ 🎯 67%  │ │ 🔥 3   │ │
│  │ Points  │ │ Accuracy│ │ Streak │ │
│  └─────────┘ └─────────┘ └────────┘ │
│                                      │
│  Personal Info                       │
│  ┌────────────────────────────────┐  │
│  │ Username        @yugoja21     │  │
│  └────────────────────────────────┘  │
│                                      │
│  My Leagues                    [2]   │
│  ┌────────────────────────────────┐  │
│  │ 👥 Office Squad            >  │  │
│  │ 👥 College Gang            >  │  │
│  └────────────────────────────────┘  │
│                                      │
│  Settings                            │
│  ┌────────────────────────────────┐  │
│  │ 🔔 Notifications              >│  │
│  │ 🛡 Privacy                    >│  │
│  │ ❓ Help & Support             >│  │
│  └────────────────────────────────┘  │
│                                      │
│  [         🚪 Sign Out          ]    │
└──────────────────────────────────────┘
```

---

## 11. Admin Panel `/admin`

```
┌──────────────────────────────────────┐
│  ⚙️ Admin Panel                       │
│  Manage matches and view predictions │
│                                      │
│  ┌─────────┐ ┌─────────┐            │
│  │ ⚙️ 24   │ │ 🕐 12   │            │
│  │ Total   │ │ Sched.  │            │
│  ├─────────┤ ├─────────┤            │
│  │ ✅ 12   │ │ 📊 156  │            │
│  │ Complt. │ │ Predict.│            │
│  └─────────┘ └─────────┘            │
│                                      │
│  🕐 Scheduled Matches         [12]   │
│  ┌────────────────────────────────┐  │
│  │ IND vs SA        [3 predictions]│ │
│  │ Feb 22, 2:30 PM               │  │
│  │ [Set Lineup] [Set Result]      │  │
│  │ [     View Predictions    ]    │  │
│  └────────────────────────────────┘  │
│                                      │
│  ✅ Completed Matches          [12]  │
│  ┌────────────────────────────────┐  │
│  │ ENG vs AUS · 8 predictions    │  │
│  │                     [View ->] │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## Shared: MatchCard Component

```
┌──────────────────────────────────────┐
│ UPCOMING  Predicted  XI   🕐 2d 3h  │
│                                      │
│  🇮🇳 IND        vs        SA 🇿🇦     │
│                                      │
│  Wankhede Stadium                    │
│  Feb 22 · 02:30 PM                   │
│                                      │
│  [      Make Prediction        ]     │
│  or [    Update Prediction     ]     │
│  or (no button when Locked)          │
└──────────────────────────────────────┘
```

Badge states: UPCOMING (default) | LIVE (red pulse) | COMPLETED (muted)
Countdown: yellow timer → red "Locked" when started
Action: predict btn (upcoming, unlocked) | View Live | View Results
