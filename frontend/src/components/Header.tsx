'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Trophy, Target, Users, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Header() {
  const { isAuthenticated, username } = useAuth();
  const pathname = usePathname();

  // Don't show header on landing page if not authenticated
  if (!isAuthenticated && pathname === '/') {
    return null;
  }

  const navItems = [
    { href: '/dashboard', label: 'Home', icon: Trophy },
    { href: '/predictions', label: 'Predict', icon: Target },
    { href: '/leagues', label: 'Leagues', icon: Users },
    { href: '/leaderboard', label: 'Board', icon: TrendingUp },
  ];

  return (
    <>
      {/* Top Header */}
      <header className="sticky top-0 z-50 bg-background border-b border-border safe-top">
        <div className="container-mobile h-14 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <Trophy className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg font-['Space_Grotesk']">CrickPredict</span>
          </Link>

          {isAuthenticated && username && (
            <Link href="/profile">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-sm font-semibold">
                  {username.substring(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </Link>
          )}
        </div>
      </header>

      {/* Bottom Navigation - Only show when authenticated */}
      {isAuthenticated && (
        <nav className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border safe-bottom">
          <div className="container-mobile h-16 flex items-center justify-around">
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-lg transition-colors min-w-[60px]',
                    isActive
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-[10px] font-medium">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </>
  );
}
