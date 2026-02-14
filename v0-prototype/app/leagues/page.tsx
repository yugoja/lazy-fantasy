"use client"

import { useState } from "react"
import { Header, BottomNav } from "@/components/header"
import { leagues } from "@/lib/data"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Users,
  Plus,
  Link2,
  Copy,
  Check,
  Crown,
  ArrowRight,
  LogIn,
  Shield,
} from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

function CreateLeagueDialog() {
  const [name, setName] = useState("")
  const [maxMembers, setMaxMembers] = useState("20")
  const [created, setCreated] = useState(false)
  const [generatedCode, setGeneratedCode] = useState("")

  const handleCreate = () => {
    const code = `${name.slice(0, 3).toUpperCase()}-${Math.random().toString(36).slice(2, 5).toUpperCase()}-${Math.floor(Math.random() * 100)}`
    setGeneratedCode(code)
    setCreated(true)
  }

  return (
    <Dialog onOpenChange={() => { setCreated(false); setName(""); }}>
      <DialogTrigger asChild>
        <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Create
        </Button>
      </DialogTrigger>
      <DialogContent className="mx-4 max-w-[calc(100vw-2rem)] rounded-xl border-border bg-card text-foreground">
        <DialogHeader>
          <DialogTitle className="font-display text-foreground">
            {created ? "League Created!" : "Create a New League"}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {created
              ? "Share the code below to invite friends."
              : "Set up your league and invite friends."}
          </DialogDescription>
        </DialogHeader>

        {created ? (
          <CreatedLeagueView code={generatedCode} name={name} />
        ) : (
          <div className="flex flex-col gap-3.5 pt-1">
            <div>
              <label htmlFor="league-name" className="mb-1 block text-xs font-medium text-foreground">
                League Name
              </label>
              <Input
                id="league-name"
                placeholder="e.g., Office Champions"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-secondary border-border text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div>
              <label htmlFor="max-members" className="mb-1 block text-xs font-medium text-foreground">
                Max Members
              </label>
              <Input
                id="max-members"
                type="number"
                placeholder="20"
                value={maxMembers}
                onChange={(e) => setMaxMembers(e.target.value)}
                className="bg-secondary border-border text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <Button
              onClick={handleCreate}
              disabled={!name.trim()}
              className="mt-1 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Create League
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function CreatedLeagueView({ code, name }: { code: string; name: string }) {
  const [copied, setCopied] = useState(false)
  const inviteLink = `https://crickpredict.app/join/${code}`

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-3.5 pt-1">
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-3.5 text-center">
        <p className="text-[10px] text-muted-foreground">League Code</p>
        <p className="mt-1 font-display text-xl font-bold tracking-wider text-primary">{code}</p>
      </div>
      <div>
        <label className="mb-1 block text-[10px] font-medium text-muted-foreground">
          Invite Link
        </label>
        <div className="flex gap-2">
          <Input
            readOnly
            value={inviteLink}
            className="bg-secondary border-border text-xs text-foreground"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => handleCopy(inviteLink)}
            className="shrink-0"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-primary" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
      <p className="text-center text-[10px] text-muted-foreground">
        Share this to invite friends to <span className="font-semibold text-foreground">{name}</span>
      </p>
    </div>
  )
}

function JoinLeagueDialog() {
  const [code, setCode] = useState("")
  const [joined, setJoined] = useState(false)

  return (
    <Dialog onOpenChange={() => { setJoined(false); setCode(""); }}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <LogIn className="mr-1.5 h-3.5 w-3.5" />
          Join
        </Button>
      </DialogTrigger>
      <DialogContent className="mx-4 max-w-[calc(100vw-2rem)] rounded-xl border-border bg-card text-foreground">
        <DialogHeader>
          <DialogTitle className="font-display text-foreground">
            {joined ? "Joined!" : "Join a League"}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {joined
              ? "You are now part of the league."
              : "Enter the league code shared with you."}
          </DialogDescription>
        </DialogHeader>

        {joined ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/20">
              <Check className="h-6 w-6 text-primary" />
            </div>
            <p className="text-xs text-muted-foreground">Check the leaderboard to see your ranking.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3.5 pt-1">
            <div>
              <label htmlFor="join-code" className="mb-1 block text-xs font-medium text-foreground">
                League Code
              </label>
              <Input
                id="join-code"
                placeholder="e.g., OFC-2026-XK9"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                className="bg-secondary border-border text-center font-mono text-base tracking-wider text-foreground placeholder:text-xs placeholder:tracking-normal placeholder:font-sans"
              />
            </div>
            <Button
              onClick={() => setJoined(true)}
              disabled={!code.trim()}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Join League
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function LeagueCard({ league }: { league: typeof leagues[0] }) {
  const [showCode, setShowCode] = useState(false)

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-start gap-3 p-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary">
          <Shield className="h-5 w-5 text-secondary-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <h3 className="truncate font-display text-sm font-bold text-foreground">{league.name}</h3>
            {league.rank === 1 && (
              <Crown className="h-3.5 w-3.5 shrink-0 text-accent" />
            )}
          </div>
          <p className="mt-0.5 text-[10px] text-muted-foreground">
            by {league.createdBy}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="font-display text-lg font-bold text-foreground">#{league.rank}</p>
          <p className="text-[10px] text-muted-foreground">{league.points} pts</p>
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-border px-3.5 py-2.5">
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <Users className="h-3 w-3" />
          <span>{league.members}/{league.maxMembers}</span>
        </div>
        <button
          onClick={() => setShowCode(!showCode)}
          className="flex items-center gap-1 text-[10px] font-medium text-primary"
        >
          <Link2 className="h-3 w-3" />
          {showCode ? league.code : "Code"}
        </button>
        <div className="flex-1" />
        <Link href={`/leaderboard?league=${league.id}`}>
          <Badge variant="outline" className="text-[10px] text-primary">
            Board
            <ArrowRight className="ml-0.5 h-2.5 w-2.5" />
          </Badge>
        </Link>
      </div>
    </div>
  )
}

export default function LeaguesPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="px-4 pb-24 pt-5">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
              My Leagues
            </h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Create or join leagues to compete.
            </p>
          </div>
          <div className="flex gap-2">
            <JoinLeagueDialog />
            <CreateLeagueDialog />
          </div>
        </div>

        <div className="mb-4">
          <Badge variant="secondary" className="text-[10px]">
            {leagues.length} Leagues
          </Badge>
        </div>

        <div className="flex flex-col gap-3">
          {leagues.map((league) => (
            <LeagueCard key={league.id} league={league} />
          ))}
        </div>
      </main>
      <BottomNav />
    </div>
  )
}
