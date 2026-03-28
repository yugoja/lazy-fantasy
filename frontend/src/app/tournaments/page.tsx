'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { listTournaments, getTournamentPicks, TournamentSummary, TournamentPicksResponse } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function statusInfo(window: string): { label: string; dot: string; color: string } {
  if (window === 'open' || window === 'open2') {
    return { label: 'PICKS OPEN', dot: 'bg-green-500', color: 'text-green-500' };
  }
  return { label: 'FINALIZED', dot: 'bg-muted-foreground', color: 'text-muted-foreground' };
}

export default function TournamentsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [tournaments, setTournaments] = useState<TournamentSummary[]>([]);
  const [picksByTournament, setPicksByTournament] = useState<Record<number, TournamentPicksResponse>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      const data = await listTournaments();
      setTournaments(data);

      // Fetch picks for each tournament in parallel to get user pts
      const results = await Promise.allSettled(data.map(t => getTournamentPicks(t.id)));
      const picks: Record<number, TournamentPicksResponse> = {};
      results.forEach((result, i) => {
        if (result.status === 'fulfilled') {
          picks[data[i].id] = result.value;
        }
      });
      setPicksByTournament(picks);
    } catch {
      // empty state
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-4">
      <h1 className="text-2xl font-bold">Tournaments</h1>

      {tournaments.length === 0 ? (
        <Card className="p-8 text-center space-y-3">
          <Trophy className="h-10 w-10 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">No tournaments available</p>
        </Card>
      ) : (
        <div className="space-y-5">
          {tournaments.map(tournament => {
            const status = statusInfo(tournament.picks_window);
            const picks = picksByTournament[tournament.id];
            const isOpen = tournament.picks_window === 'open' || tournament.picks_window === 'open2';

            return (
              <Link key={tournament.id} href={`/tournaments/${tournament.id}`}>
                <Card className="p-4 hover:border-primary/50 transition-colors cursor-pointer">
                  {/* Status pill */}
                  <div className="flex items-center gap-1.5 mb-3">
                    <span className={cn('h-1.5 w-1.5 rounded-full', status.dot)} />
                    <span className={cn('text-[10px] font-bold uppercase tracking-wider', status.color)}>
                      {status.label}
                    </span>
                  </div>

                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      {/* Tournament name */}
                      <p className="font-bold text-base uppercase tracking-wide truncate">
                        {tournament.name}
                      </p>
                      {/* Date range */}
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {formatDate(tournament.start_date)} – {formatDate(tournament.end_date)}
                      </p>

                      {/* Stats row */}
                      <div className="flex items-center gap-4 mt-3">
                        {picks != null && (
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Your pts</p>
                            <p className="text-base font-bold font-mono">{picks.points_earned}</p>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <Trophy className={cn('h-6 w-6', isOpen ? 'text-primary' : 'text-muted-foreground')} />
                      <div className="flex items-center gap-0.5 text-xs text-primary font-medium">
                        View <ChevronRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
