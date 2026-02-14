"use client"

import { Trophy, Target, TrendingUp, Flame } from "lucide-react"

const stats = [
  {
    label: "Points",
    value: "245",
    icon: Trophy,
    change: "+12 this week",
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    label: "Accuracy",
    value: "63%",
    icon: Target,
    change: "22 of 35",
    color: "text-accent",
    bg: "bg-accent/10",
  },
  {
    label: "Best Rank",
    value: "#1",
    icon: TrendingUp,
    change: "Cricket Fanatics",
    color: "text-chart-3",
    bg: "bg-chart-3/10",
  },
  {
    label: "Streak",
    value: "2",
    icon: Flame,
    change: "Keep going!",
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
]

export function StatsOverview() {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {stats.map((stat) => {
        const Icon = stat.icon
        return (
          <div
            key={stat.label}
            className="rounded-xl border border-border bg-card p-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                {stat.label}
              </span>
              <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${stat.bg}`}>
                <Icon className={`h-3.5 w-3.5 ${stat.color}`} />
              </div>
            </div>
            <p className="mt-1.5 font-display text-xl font-bold text-foreground">
              {stat.value}
            </p>
            <p className="mt-0.5 text-[10px] text-muted-foreground">{stat.change}</p>
          </div>
        )
      })}
    </div>
  )
}
