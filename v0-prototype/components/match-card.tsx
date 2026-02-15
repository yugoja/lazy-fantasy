"use client"

import { Match, getFlagUrl } from "@/lib/data"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MapPin, Clock, Users, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"
import Image from "next/image"

const teamBgColors: Record<string, string> = {
  IND: "bg-blue-900/40",
  AUS: "bg-yellow-900/40",
  ENG: "bg-red-900/40",
  SA: "bg-green-900/40",
  PAK: "bg-emerald-900/40",
  NZ: "bg-slate-700/40",
  WI: "bg-amber-900/40",
  SL: "bg-blue-900/40",
  BAN: "bg-green-900/40",
  AFG: "bg-blue-900/40",
}

export function TeamFlag({ code, name }: { code: string; name: string }) {
  const flagUrl = getFlagUrl(code, 160)

  return (
    <div className="flex flex-col items-center gap-1.5">
      {flagUrl ? (
        <div className="overflow-hidden rounded-lg shadow-lg">
          <Image
            src={flagUrl}
            alt={`${name} flag`}
            width={48}
            height={32}
            className="block h-8 w-12 object-cover"
            unoptimized
          />
        </div>
      ) : (
        <div
          className={cn(
            "flex h-8 w-12 items-center justify-center rounded-lg shadow-lg",
            teamBgColors[code] || "bg-secondary"
          )}
        >
          <span className="font-display text-sm font-bold text-foreground">{code}</span>
        </div>
      )}
      <span className="text-xs font-medium text-foreground">{name}</span>
    </div>
  )
}

export function MatchCard({ match }: { match: Match }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2">
        <div className="flex items-center gap-2">
          {match.status === "live" && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
            </span>
          )}
          <Badge
            variant="outline"
            className={cn(
              "text-[10px] font-semibold uppercase tracking-wider",
              match.status === "live" && "border-red-500/50 text-red-400",
              match.status === "upcoming" && "border-primary/50 text-primary",
              match.status === "completed" && "border-muted-foreground/50 text-muted-foreground"
            )}
          >
            {match.status}
          </Badge>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <Users className="h-3 w-3" />
          <span>{match.predictionsCount.toLocaleString()}</span>
        </div>
      </div>

      <div className="flex items-center justify-center gap-6 px-4 py-5">
        <TeamFlag code={match.team1Code} name={match.team1} />
        <span className="font-display text-base font-bold text-muted-foreground">VS</span>
        <TeamFlag code={match.team2Code} name={match.team2} />
      </div>

      <div className="flex items-center gap-3 border-t border-border px-3.5 py-2.5">
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <MapPin className="h-3 w-3 shrink-0" />
          <span className="truncate">{match.venue}</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 px-3.5 pb-2.5 text-[10px] text-muted-foreground">
        <Clock className="h-3 w-3 shrink-0" />
        <span>{match.date} &middot; {match.time}</span>
      </div>

      {match.status !== "completed" && (
        <div className="border-t border-border px-3.5 py-2.5">
          <Link href={`/predictions?match=${match.id}`}>
            <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90" size="sm">
              {match.status === "live" ? "View Predictions" : "Make Prediction"}
              <ChevronRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      )}
    </div>
  )
}
