"use client"

import { Header, BottomNav } from "@/components/header"
import { StatsOverview } from "@/components/stats-overview"
import { MatchCard } from "@/components/match-card"
import { matches, leagues, leaderboard } from "@/lib/data"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ChevronRight, Crown, Users, ArrowRight } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

function QuickLeaderboard() {
  const top5 = leaderboard.slice(0, 5)
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
        <h3 className="font-display text-sm font-bold text-foreground">Top Performers</h3>
        <Link href="/leaderboard" className="text-[10px] font-medium text-primary">
          View All
        </Link>
      </div>
      <div className="divide-y divide-border">
        {top5.map((entry) => (
          <div
            key={entry.rank}
            className={cn(
              "flex items-center gap-2.5 px-3.5 py-2.5",
              entry.isCurrentUser && "bg-primary/5"
            )}
          >
            <span className="flex h-5 w-5 items-center justify-center text-[10px] font-bold text-muted-foreground">
              {entry.rank === 1 ? (
                <Crown className="h-3.5 w-3.5 text-accent" />
              ) : (
                `#${entry.rank}`
              )}
            </span>
            <Avatar className="h-6 w-6">
              <AvatarFallback className={cn(
                "text-[9px] font-bold",
                entry.isCurrentUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
              )}>
                {entry.avatar}
              </AvatarFallback>
            </Avatar>
            <span className={cn(
              "flex-1 text-xs font-medium",
              entry.isCurrentUser ? "text-primary" : "text-foreground"
            )}>
              {entry.name}
            </span>
            <span className="font-display text-xs font-bold text-foreground">{entry.points}</span>
            <span className="text-[10px] text-muted-foreground">pts</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MyLeagues() {
  const topLeagues = leagues.slice(0, 3)
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
        <h3 className="font-display text-sm font-bold text-foreground">My Leagues</h3>
        <Link href="/leagues" className="text-[10px] font-medium text-primary">
          View All
        </Link>
      </div>
      <div className="divide-y divide-border">
        {topLeagues.map((league) => (
          <div key={league.id} className="flex items-center gap-3 px-3.5 py-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary">
              <Users className="h-3.5 w-3.5 text-secondary-foreground" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-foreground">{league.name}</p>
              <p className="text-[10px] text-muted-foreground">{league.members} members</p>
            </div>
            <div className="text-right">
              <p className="font-display text-xs font-bold text-foreground">#{league.rank}</p>
              <p className="text-[10px] text-muted-foreground">{league.points} pts</p>
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-border p-2.5">
        <Link href="/leagues" className="flex items-center justify-center gap-1.5 rounded-lg border border-border py-2 text-xs font-medium text-foreground active:bg-secondary">
          Manage Leagues
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const upcomingMatches = matches.filter((m) => m.status === "upcoming" || m.status === "live")

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="px-4 pb-24 pt-5">
        <div className="mb-5">
          <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
            Welcome back, Player
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {"Here's what's happening in your cricket world."}
          </p>
        </div>

        <StatsOverview />

        <div className="mt-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-bold text-foreground">Upcoming Matches</h2>
            <Link href="/predictions">
              <Badge variant="outline" className="cursor-pointer text-[10px] text-primary">
                View All
                <ChevronRight className="ml-0.5 h-3 w-3" />
              </Badge>
            </Link>
          </div>
          <div className="flex flex-col gap-3">
            {upcomingMatches.slice(0, 3).map((match) => (
              <MatchCard key={match.id} match={match} />
            ))}
          </div>
        </div>

        <div className="mt-6">
          <QuickLeaderboard />
        </div>

        <div className="mt-4">
          <MyLeagues />
        </div>
      </main>
      <BottomNav />
    </div>
  )
}
