"use client"

import { useState } from "react"
import { Match, players, Player, getFlagUrl } from "@/lib/data"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Check, Trophy, Target, Crosshair, Star, ChevronLeft } from "lucide-react"
import Image from "next/image"

function PlayerSelector({
  label,
  icon: Icon,
  allPlayers,
  selectedId,
  onSelect,
}: {
  label: string
  icon: React.ComponentType<{ className?: string }>
  allPlayers: Player[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-3.5 py-2.5">
        <Icon className="h-3.5 w-3.5 text-primary" />
        <h3 className="text-xs font-semibold text-foreground">{label}</h3>
      </div>
      <div className="grid grid-cols-3 gap-2 p-2.5">
        {allPlayers.map((player) => (
          <button
            key={player.id}
            onClick={() => onSelect(player.id)}
            className={cn(
              "flex flex-col items-center gap-1 rounded-lg border p-2.5 text-center transition-all",
              selectedId === player.id
                ? "border-primary bg-primary/10"
                : "border-border bg-secondary/50 active:bg-secondary"
            )}
          >
            <div className={cn(
              "flex h-7 w-7 items-center justify-center rounded-full text-[9px] font-bold",
              selectedId === player.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
            )}>
              {player.name.split(" ").map(n => n[0]).join("")}
            </div>
            <span className={cn(
              "text-[10px] font-medium leading-tight",
              selectedId === player.id ? "text-primary" : "text-foreground"
            )}>
              {player.name.split(" ").pop()}
            </span>
            <Badge variant="outline" className="text-[8px] px-1 py-0">
              {player.role === "wicket-keeper" ? "WK" : player.role === "all-rounder" ? "AR" : player.role === "batsman" ? "BAT" : "BOWL"}
            </Badge>
            {selectedId === player.id && (
              <Check className="h-3 w-3 text-primary" />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PredictionForm({ match, onBack }: { match: Match; onBack: () => void }) {
  const [winner, setWinner] = useState<string | null>(null)
  const [topBatsman, setTopBatsman] = useState<string | null>(null)
  const [topBowler, setTopBowler] = useState<string | null>(null)
  const [motm, setMotm] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const allPlayers = [
    ...(players[match.team1Code] || []),
    ...(players[match.team2Code] || []),
  ]

  const batsmen = allPlayers.filter(p => p.role === "batsman" || p.role === "all-rounder" || p.role === "wicket-keeper")
  const bowlers = allPlayers.filter(p => p.role === "bowler" || p.role === "all-rounder")

  const isComplete = winner && topBatsman && topBowler && motm

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl border border-primary/30 bg-primary/5 px-5 py-10 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/20">
          <Check className="h-7 w-7 text-primary" />
        </div>
        <h2 className="font-display text-xl font-bold text-foreground">Prediction Submitted!</h2>
        <p className="text-xs text-muted-foreground">
          Your predictions for {match.team1} vs {match.team2} have been recorded.
        </p>
        <Button onClick={onBack} variant="outline" size="sm" className="mt-2">
          <ChevronLeft className="mr-1 h-3.5 w-3.5" />
          Back to Matches
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2.5">
        <button onClick={onBack} className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground active:bg-secondary">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="font-display text-base font-bold text-foreground">
            {match.team1} vs {match.team2}
          </h2>
          <p className="text-[10px] text-muted-foreground">{match.venue} &middot; {match.date}</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1.5">
        {[winner, topBatsman, topBowler, motm].map((val, i) => (
          <div
            key={i}
            className={cn(
              "h-1 flex-1 rounded-full transition-colors",
              val ? "bg-primary" : "bg-muted"
            )}
          />
        ))}
      </div>

      {/* Winner Prediction */}
      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border px-3.5 py-2.5">
          <Trophy className="h-3.5 w-3.5 text-primary" />
          <h3 className="text-xs font-semibold text-foreground">Match Winner</h3>
        </div>
        <div className="grid grid-cols-2 gap-2.5 p-3">
          {[
            { code: match.team1Code, name: match.team1 },
            { code: match.team2Code, name: match.team2 },
          ].map((team) => {
            const flagUrl = getFlagUrl(team.code, 160)
            return (
              <button
                key={team.code}
                onClick={() => setWinner(team.code)}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-xl border p-4 transition-all",
                  winner === team.code
                    ? "border-primary bg-primary/10"
                    : "border-border bg-secondary/50 active:bg-secondary"
                )}
              >
                {flagUrl ? (
                  <div className="overflow-hidden rounded-md">
                    <Image
                      src={flagUrl}
                      alt={`${team.name} flag`}
                      width={44}
                      height={30}
                      className="block h-[30px] w-[44px] object-cover"
                      unoptimized
                    />
                  </div>
                ) : (
                  <span className="font-display text-base font-bold text-foreground">{team.code}</span>
                )}
                <span className={cn(
                  "text-xs font-semibold",
                  winner === team.code ? "text-primary" : "text-foreground"
                )}>
                  {team.name}
                </span>
                {winner === team.code && (
                  <Check className="h-4 w-4 text-primary" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Top Batsman */}
      <PlayerSelector
        label="Top Batsman (Most Runs)"
        icon={Target}
        allPlayers={batsmen}
        selectedId={topBatsman}
        onSelect={setTopBatsman}
      />

      {/* Top Bowler */}
      <PlayerSelector
        label="Top Bowler (Most Wickets)"
        icon={Crosshair}
        allPlayers={bowlers}
        selectedId={topBowler}
        onSelect={setTopBowler}
      />

      {/* Man of the Match */}
      <PlayerSelector
        label="Man of the Match"
        icon={Star}
        allPlayers={allPlayers}
        selectedId={motm}
        onSelect={setMotm}
      />

      {/* Sticky submit bar */}
      <div className="sticky bottom-16 flex items-center gap-3 rounded-xl border border-border bg-card/95 p-3 backdrop-blur-md">
        <div className="flex-1">
          <p className="text-[10px] font-medium text-foreground">
            {isComplete ? "All predictions made!" : "Complete all 4 to submit"}
          </p>
        </div>
        <Button
          onClick={() => setSubmitted(true)}
          disabled={!isComplete}
          size="sm"
          className="bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
        >
          Submit
        </Button>
      </div>
    </div>
  )
}
