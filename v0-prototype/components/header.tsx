"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Trophy, LayoutDashboard, Target, Users } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

const navItems = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/predictions", label: "Predict", icon: Target },
  { href: "/leagues", label: "Leagues", icon: Users },
  { href: "/leaderboard", label: "Board", icon: Trophy },
]

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/80 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Trophy className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-foreground">
            CrickPredict
          </span>
        </Link>
        <Avatar className="h-8 w-8 border border-border">
          <AvatarFallback className="bg-secondary text-xs font-semibold text-secondary-foreground">YO</AvatarFallback>
        </Avatar>
      </div>
    </header>
  )
}

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card/95 backdrop-blur-xl"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex items-stretch justify-around">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 pb-2 pt-2.5 text-[10px] font-medium transition-colors",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground active:text-foreground"
              )}
            >
              <div className={cn(
                "flex h-7 w-7 items-center justify-center rounded-lg transition-colors",
                isActive && "bg-primary/15"
              )}>
                <Icon className={cn("h-[18px] w-[18px]", isActive && "text-primary")} />
              </div>
              {item.label}
            </Link>
          )
        })}
      </div>
      {/* Safe area spacer for notched devices */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}
