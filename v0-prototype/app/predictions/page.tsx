"use client"

import { useState } from "react"
import { Header, BottomNav } from "@/components/header"
import { MatchCard } from "@/components/match-card"
import { PredictionForm } from "@/components/prediction-form"
import { matches } from "@/lib/data"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

function PredictionsContent() {
  const searchParams = useSearchParams()
  const matchParam = searchParams.get("match")
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(matchParam)

  const selectedMatch = matches.find((m) => m.id === selectedMatchId)

  const upcomingMatches = matches.filter((m) => m.status === "upcoming")
  const liveMatches = matches.filter((m) => m.status === "live")
  const completedMatches = matches.filter((m) => m.status === "completed")

  if (selectedMatch) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="px-4 pb-24 pt-5">
          <PredictionForm match={selectedMatch} onBack={() => setSelectedMatchId(null)} />
        </main>
        <BottomNav />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="px-4 pb-24 pt-5">
        <div className="mb-4">
          <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
            Match Predictions
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Pick a match to make your predictions.
          </p>
        </div>

        <Tabs defaultValue="upcoming" className="w-full">
          <TabsList className="mb-4 w-full gap-1 bg-secondary/50">
            <TabsTrigger value="upcoming" className="flex-1 text-xs">
              Upcoming ({upcomingMatches.length})
            </TabsTrigger>
            <TabsTrigger value="live" className="flex-1 text-xs">
              Live ({liveMatches.length})
            </TabsTrigger>
            <TabsTrigger value="completed" className="flex-1 text-xs">
              Done ({completedMatches.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upcoming">
            {upcomingMatches.length === 0 ? (
              <EmptyState message="No upcoming matches right now." />
            ) : (
              <div className="flex flex-col gap-3">
                {upcomingMatches.map((match) => (
                  <div key={match.id} onClick={() => setSelectedMatchId(match.id)} className="cursor-pointer">
                    <MatchCard match={match} />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="live">
            {liveMatches.length === 0 ? (
              <EmptyState message="No live matches at the moment." />
            ) : (
              <div className="flex flex-col gap-3">
                {liveMatches.map((match) => (
                  <div key={match.id} onClick={() => setSelectedMatchId(match.id)} className="cursor-pointer">
                    <MatchCard match={match} />
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="completed">
            {completedMatches.length === 0 ? (
              <EmptyState message="No completed matches yet." />
            ) : (
              <div className="flex flex-col gap-3">
                {completedMatches.map((match) => (
                  <MatchCard key={match.id} match={match} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
      <BottomNav />
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-12 text-center">
      <p className="text-xs text-muted-foreground">{message}</p>
    </div>
  )
}

export default function PredictionsPage() {
  return (
    <Suspense>
      <PredictionsContent />
    </Suspense>
  )
}
