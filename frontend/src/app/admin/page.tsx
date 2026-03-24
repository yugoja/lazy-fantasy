'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Settings, Clock, CheckCircle2, BarChart3, ArrowRight } from 'lucide-react';

interface AdminMatch {
  id: number;
  tournament_id: number;
  team_1: { id: number; name: string; short_name: string };
  team_2: { id: number; name: string; short_name: string };
  start_time: string;
  status: string;
  prediction_count: number;
}

export default function AdminPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [matches, setMatches] = useState<AdminMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadMatches();
    }
  }, [isAuthenticated]);

  const loadMatches = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/admin/matches`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to load matches');
      const data = await response.json();
      setMatches(data);
    } catch {
      setError('Failed to load matches');
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-6 w-40" />
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
  const scheduledMatches = matches
    .filter(m => m.status === 'SCHEDULED' && new Date(m.start_time) >= todayStart)
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  const completedMatches = matches.filter(m => m.status === 'COMPLETED');

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Settings className="h-5 w-5 text-primary" />
          <h1 className="text-xl font-bold">Admin Panel</h1>
        </div>
        <p className="text-sm text-muted-foreground">Manage matches and view predictions</p>
      </div>



      {error && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{error}</p>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Total Matches', value: matches.length, icon: Settings, color: 'text-primary' },
          { label: 'Scheduled', value: scheduledMatches.length, icon: Clock, color: 'text-yellow-400' },
          { label: 'Completed', value: completedMatches.length, icon: CheckCircle2, color: 'text-green-400' },
          { label: 'Predictions', value: matches.reduce((sum, m) => sum + m.prediction_count, 0), icon: BarChart3, color: 'text-blue-400' },
        ].map((stat) => (
          <Card key={stat.label} className="border-border bg-card">
            <CardContent className="flex flex-col items-center gap-1 p-4">
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
              <span className="text-2xl font-bold">{stat.value}</span>
              <span className="text-[10px] text-muted-foreground">{stat.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Scheduled Matches */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-yellow-400" />
          <h2 className="font-semibold text-sm">Scheduled Matches</h2>
          <Badge variant="secondary" className="ml-auto text-[10px]">
            {scheduledMatches.length}
          </Badge>
        </div>
        {scheduledMatches.length === 0 ? (
          <Card className="border-border bg-card">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground">No scheduled matches</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {scheduledMatches.map((match) => (
              <Card key={match.id} className="border-border bg-card">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-sm">
                        {match.team_1.short_name} vs {match.team_2.short_name}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {new Date(match.start_time).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      {match.prediction_count} predictions
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/admin/matches/${match.id}/lineup`} className="flex-1">
                      <Button variant="secondary" size="sm" className="w-full text-xs">
                        Set Lineup
                      </Button>
                    </Link>
                    <Link href={`/admin/matches/${match.id}/result`} className="flex-1">
                      <Button size="sm" className="w-full text-xs">
                        Set Result
                      </Button>
                    </Link>
                  </div>
                  <div>
                    <Link href={`/admin/matches/${match.id}/predictions`}>
                      <Button variant="outline" size="sm" className="w-full text-xs">
                        View Predictions
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Completed Matches */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-green-400" />
          <h2 className="font-semibold text-sm">Completed Matches</h2>
          <Badge variant="secondary" className="ml-auto text-[10px]">
            {completedMatches.length}
          </Badge>
        </div>
        {completedMatches.length === 0 ? (
          <Card className="border-border bg-card">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground">No completed matches yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {completedMatches.map((match) => (
              <Card key={match.id} className="border-border bg-card">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-sm">
                        {match.team_1.short_name} vs {match.team_2.short_name}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {new Date(match.start_time).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })}
                        {' '}&middot; {match.prediction_count} predictions
                      </p>
                    </div>
                    <Link href={`/admin/matches/${match.id}/predictions`}>
                      <Button variant="ghost" size="sm" className="text-xs gap-1">
                        View <ArrowRight className="h-3 w-3" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
