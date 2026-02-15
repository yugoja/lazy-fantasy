"use client"

import { useState, Suspense } from "react"
import { Header, BottomNav } from "@/components/header"
import { leaderboard, leagues, type LeaderboardEntry } from "@/lib/data"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Crown, Medal, Flame, TrendingUp, ChevronUp, ChevronDown, Minus } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSearchParams } from "next/navigation"

function PodiumCard({ entry, position }: { entry: LeaderboardEntry; position: 1 | 2 | 3 }) {
  const config = {
    1: {
      size: "h-14 w-14",
      textSize: "text-xl",
      ring: "ring-accent",
      bg: "bg-accent/10 border-accent/30",
      icon: <Crown className="h-5 w-5 text-accent" />,
    },
    2: {
      size: "h-11 w-11",
      textSize: "text-lg",
      ring: "ring-muted-foreground",
      bg: "bg-secondary border-border",
      icon: <Medal className="h-4 w-4 text-muted-foreground" />,
    },
    3: {
      size: "h-10 w-10",
      textSize: "text-base",
      ring: "ring-chart-3",
      bg: "bg-chart-3/10 border-chart-3/30",
      icon: <Medal className="h-4 w-4 text-chart-3" />,
    },
  }[position]

  return (
    <div className={cn(
      "flex flex-col items-center gap-1.5 rounded-xl border p-3 text-center",
      config.bg,
      position === 1 && "order-2",
      position === 2 && "order-1 mt-4",
      position === 3 && "order-3 mt-4"
    )}>
      {config.icon}
      <Avatar className={cn(config.size, "ring-2", config.ring)}>
        <AvatarFallback className={cn(
          "font-bold",
          entry.isCurrentUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground",
          position === 1 ? "text-base" : "text-xs"
        )}>
          {entry.avatar}
        </AvatarFallback>
      </Avatar>
      <p className={cn(
        "font-display font-bold text-foreground",
        position === 1 ? "text-xs" : "text-[10px]"
      )}>
        {entry.name}
      </p>
      <p className={cn("font-display font-bold text-primary", config.textSize)}>
        {entry.points}
      </p>
      <p className="text-[9px] text-muted-foreground">points</p>
      {entry.streak > 0 && (
        <Badge variant="outline" className="text-[8px] px-1 py-0 text-accent">
          <Flame className="mr-0.5 h-2.5 w-2.5" />
          {entry.streak}
        </Badge>
      )}
    </div>
  )
}

function RankChange() {
  const changes = [1, -1, 0, 2, -2]
  const change = changes[Math.floor(Math.random() * changes.length)]
  if (change > 0) return <ChevronUp className="h-3 w-3 text-primary" />
  if (change < 0) return <ChevronDown className="h-3 w-3 text-destructive" />
  return <Minus className="h-3 w-3 text-muted-foreground" />
}

function LeaderboardList({ entries }: { entries: LeaderboardEntry[] }) {
  const remaining = entries.slice(3)

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border bg-secondary/50 px-3.5 py-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        <span className="w-8">Rank</span>
        <span className="flex-1">Player</span>
        <span className="w-10 text-center">Pts</span>
        <span className="w-8 text-center">Win</span>
        <span className="w-6 text-center"></span>
      </div>
      <div className="divide-y divide-border">
        {remaining.map((entry) => (
          <div
            key={entry.rank}
            className={cn(
              "flex items-center gap-2 px-3.5 py-2.5",
              entry.isCurrentUser && "bg-primary/5"
            )}
          >
            <span className="w-8 font-display text-xs font-bold text-muted-foreground">
              #{entry.rank}
            </span>
            <div className="flex flex-1 items-center gap-2">
              <Avatar className="h-7 w-7">
                <AvatarFallback className={cn(
                  "text-[9px] font-bold",
                  entry.isCurrentUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
                )}>
                  {entry.avatar}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <span className={cn(
                  "block truncate text-xs font-medium",
                  entry.isCurrentUser ? "text-primary" : "text-foreground"
                )}>
                  {entry.name}
                  {entry.isCurrentUser && <span className="ml-1 text-[10px] text-muted-foreground">(You)</span>}
                </span>
              </div>
            </div>
            <span className="w-10 text-center font-display text-xs font-bold text-foreground">
              {entry.points}
            </span>
            <div className="flex w-8 items-center justify-center gap-0.5">
              {entry.streak > 0 ? (
                <>
                  <Flame className="h-3 w-3 text-accent" />
                  <span className="text-[10px] font-semibold text-accent">{entry.streak}</span>
                </>
              ) : (
                <span className="text-[10px] text-muted-foreground">--</span>
              )}
            </div>
            <div className="flex w-6 justify-center">
              <RankChange />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function LeaderboardContent() {
  const searchParams = useSearchParams()
  const leagueParam = searchParams.get("league")
  const [selectedLeague, setSelectedLeague] = useState(leagueParam || leagues[0]?.id || "")

  const top3 = leaderboard.slice(0, 3)
  const currentUser = leaderboard.find((e) => e.isCurrentUser)

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="px-4 pb-24 pt-5">
        <div className="mb-4">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
                Leaderboard
              </h1>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Top prediction performers.
              </p>
            </div>
            <Select value={selectedLeague} onValueChange={setSelectedLeague}>
              <SelectTrigger className="w-auto max-w-[140px] shrink-0 bg-secondary border-border text-foreground text-xs h-8 gap-1.5 px-2.5">
                <SelectValue placeholder="League" />
              </SelectTrigger>
              <SelectContent align="end" className="border-border bg-card text-foreground">
                {leagues.map((league) => (
                  <SelectItem key={league.id} value={league.id} className="text-xs">
                    {league.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Your stats bar */}
        {currentUser && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 px-3.5 py-2.5">
            <TrendingUp className="h-4 w-4 shrink-0 text-primary" />
            <span className="text-xs font-medium text-foreground">You</span>
            <Badge className="bg-primary/20 text-primary font-display text-[10px] font-bold">
              #{currentUser.rank}
            </Badge>
            <div className="flex-1" />
            <span className="font-display text-sm font-bold text-primary">{currentUser.points} pts</span>
          </div>
        )}

        {/* Top 3 podium */}
        <div className="mb-5 grid grid-cols-3 gap-2">
          {top3[1] && <PodiumCard entry={top3[1]} position={2} />}
          {top3[0] && <PodiumCard entry={top3[0]} position={1} />}
          {top3[2] && <PodiumCard entry={top3[2]} position={3} />}
        </div>

        {/* Full list */}
        <LeaderboardList entries={leaderboard} />
      </main>
      <BottomNav />
    </div>
  )
}

export default function LeaderboardPage() {
  return (
    <Suspense>
      <LeaderboardContent />
    </Suspense>
  )
}
