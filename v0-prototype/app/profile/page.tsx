"use client"

import { useState } from "react"
import { Header, BottomNav } from "@/components/header"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { leagues } from "@/lib/data"
import {
  Trophy,
  Target,
  Flame,
  ChevronRight,
  Pencil,
  Check,
  LogOut,
  Bell,
  Shield,
  CircleHelp,
  Users,
} from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

const userStats = {
  points: 245,
  predictions: 35,
  accuracy: 63,
  streak: 2,
  rank: 3,
  leaguesJoined: 4,
}

export default function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState("Yash Oberoi")
  const [username, setUsername] = useState("yash_cricket26")
  const [email, setEmail] = useState("yash@example.com")
  const [tempName, setTempName] = useState(name)
  const [tempUsername, setTempUsername] = useState(username)
  const [tempEmail, setTempEmail] = useState(email)

  function handleSave() {
    setName(tempName)
    setUsername(tempUsername)
    setEmail(tempEmail)
    setIsEditing(false)
  }

  function handleCancel() {
    setTempName(name)
    setTempUsername(username)
    setTempEmail(email)
    setIsEditing(false)
  }

  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  return (
    <div className="flex min-h-[100dvh] flex-col bg-background">
      <Header />

      <main className="flex-1 overflow-y-auto px-4 pb-24 pt-5">
        {/* Profile Card */}
        <div className="mb-5 flex flex-col items-center">
          <div className="relative">
            <Avatar className="h-20 w-20 border-2 border-primary">
              <AvatarFallback className="bg-primary/15 font-display text-2xl font-bold text-primary">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-accent">
              <Trophy className="h-3.5 w-3.5 text-accent-foreground" />
            </div>
          </div>
          <h1 className="mt-3 font-display text-lg font-bold text-foreground">{name}</h1>
          <p className="text-xs text-muted-foreground">@{username}</p>
        </div>

        {/* Quick Stats */}
        <div className="mb-5 grid grid-cols-3 gap-2">
          {[
            { label: "Points", value: userStats.points, icon: Trophy, color: "text-primary" },
            { label: "Accuracy", value: `${userStats.accuracy}%`, icon: Target, color: "text-accent" },
            { label: "Streak", value: userStats.streak, icon: Flame, color: "text-orange-400" },
          ].map((stat) => (
            <Card key={stat.label} className="border-border bg-card">
              <CardContent className="flex flex-col items-center gap-1 p-3">
                <stat.icon className={cn("h-4 w-4", stat.color)} />
                <span className="font-display text-lg font-bold text-foreground">{stat.value}</span>
                <span className="text-[10px] text-muted-foreground">{stat.label}</span>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Personal Info */}
        <div className="mb-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-semibold text-foreground">Personal Info</h2>
            {!isEditing ? (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1 text-xs font-medium text-primary active:text-primary/80"
              >
                <Pencil className="h-3 w-3" />
                Edit
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCancel}
                  className="text-xs font-medium text-muted-foreground active:text-foreground"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 text-xs font-medium text-primary active:text-primary/80"
                >
                  <Check className="h-3 w-3" />
                  Save
                </button>
              </div>
            )}
          </div>

          <Card className="border-border bg-card">
            <CardContent className="flex flex-col gap-4 p-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="name" className="text-[11px] text-muted-foreground">
                  Full Name
                </Label>
                {isEditing ? (
                  <Input
                    id="name"
                    value={tempName}
                    onChange={(e) => setTempName(e.target.value)}
                    className="h-9 border-border bg-secondary text-sm text-foreground"
                  />
                ) : (
                  <p className="text-sm font-medium text-foreground">{name}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="username" className="text-[11px] text-muted-foreground">
                  Username
                </Label>
                {isEditing ? (
                  <Input
                    id="username"
                    value={tempUsername}
                    onChange={(e) => setTempUsername(e.target.value)}
                    className="h-9 border-border bg-secondary text-sm text-foreground"
                  />
                ) : (
                  <p className="text-sm font-medium text-foreground">@{username}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email" className="text-[11px] text-muted-foreground">
                  Email
                </Label>
                {isEditing ? (
                  <Input
                    id="email"
                    type="email"
                    value={tempEmail}
                    onChange={(e) => setTempEmail(e.target.value)}
                    className="h-9 border-border bg-secondary text-sm text-foreground"
                  />
                ) : (
                  <p className="text-sm font-medium text-foreground">{email}</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* My Leagues */}
        <div className="mb-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-semibold text-foreground">My Leagues</h2>
            <Badge variant="secondary" className="bg-secondary text-[10px] text-muted-foreground">
              {leagues.length}
            </Badge>
          </div>
          <Card className="border-border bg-card">
            <CardContent className="divide-y divide-border p-0">
              {leagues.map((league) => (
                <Link
                  key={league.id}
                  href="/leagues"
                  className="flex items-center justify-between px-4 py-3 active:bg-secondary/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Users className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{league.name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        Rank #{league.rank} &middot; {league.members} members
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Settings Menu */}
        <div className="mb-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-foreground">Settings</h2>
          <Card className="border-border bg-card">
            <CardContent className="divide-y divide-border p-0">
              {[
                { icon: Bell, label: "Notifications", desc: "Match reminders & results" },
                { icon: Shield, label: "Privacy", desc: "Profile visibility & data" },
                { icon: CircleHelp, label: "Help & Support", desc: "FAQs and contact us" },
              ].map((item) => (
                <button
                  key={item.label}
                  className="flex w-full items-center justify-between px-4 py-3 active:bg-secondary/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary">
                      <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium text-foreground">{item.label}</p>
                      <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Sign Out */}
        <Button
          variant="outline"
          className="w-full border-destructive/30 bg-destructive/5 text-destructive active:bg-destructive/10"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </main>

      <BottomNav />
    </div>
  )
}
