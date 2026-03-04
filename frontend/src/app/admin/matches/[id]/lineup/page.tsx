'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Users, CheckCircle2, History } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Player {
  id: number;
  name: string;
  team_id: number;
  role: string;
}

interface Team {
  id: number;
  name: string;
  short_name: string;
}

interface SquadData {
  match_id: number;
  team_1: Team;
  team_2: Team;
  team_1_players: Player[];
  team_2_players: Player[];
}

function getRoleLabel(role: string) {
  const map: Record<string, string> = {
    batsman: 'BAT', batter: 'BAT', bowler: 'BOWL',
    all_rounder: 'AR', allrounder: 'AR',
    wicket_keeper: 'WK', wicketkeeper: 'WK',
  };
  return map[role.toLowerCase()] || role.substring(0, 4).toUpperCase();
}

export default function SetLineupPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const matchId = Number(params.id);

  const [squadData, setSquadData] = useState<SquadData | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [prefilledFromPrev, setPrefilledFromPrev] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (matchId && isAuthenticated) {
      loadData();
    }
  }, [matchId, isAuthenticated]);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [squadRes, lineupRes] = await Promise.all([
        fetch(`${API_BASE}/admin/matches/${matchId}/squad`, { headers }),
        fetch(`${API_BASE}/admin/matches/${matchId}/lineup`, { headers }),
      ]);

      if (!squadRes.ok) throw new Error('Failed to load squad');
      const squad: SquadData = await squadRes.json();
      setSquadData(squad);

      if (lineupRes.ok) {
        const lineup: { player_ids: number[] } = await lineupRes.json();
        if (lineup.player_ids.length > 0) {
          setSelectedIds(new Set(lineup.player_ids));
        } else {
          // No lineup yet — try to pre-fill from previous match
          const prevRes = await fetch(`${API_BASE}/admin/matches/${matchId}/previous-lineup`, { headers });
          if (prevRes.ok) {
            const prev: { player_ids: number[] } = await prevRes.json();
            if (prev.player_ids.length > 0) {
              setSelectedIds(new Set(prev.player_ids));
              setPrefilledFromPrev(true);
            }
          }
        }
      }
    } catch {
      setError('Failed to load match data');
    } finally {
      setIsLoading(false);
    }
  };

  const togglePlayer = (playerId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(playerId)) {
        next.delete(playerId);
      } else {
        next.add(playerId);
      }
      return next;
    });
  };

  const team1Count = squadData
    ? squadData.team_1_players.filter((p) => selectedIds.has(p.id)).length
    : 0;
  const team2Count = squadData
    ? squadData.team_2_players.filter((p) => selectedIds.has(p.id)).length
    : 0;

  const handleSubmit = async () => {
    setError('');
    setSuccess('');

    if (team1Count !== 11 || team2Count !== 11) {
      setError(`Select exactly 11 per team. Currently: ${team1Count} and ${team2Count}`);
      return;
    }

    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/admin/matches/${matchId}/lineup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ player_ids: Array.from(selectedIds) }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to set lineup');
      }

      setSuccess('Lineup saved successfully!');
      setTimeout(() => router.push('/admin'), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set lineup');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!squadData) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Card className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error || 'Match not found'}</p>
          <Link href="/admin">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Admin
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const renderTeamSection = (team: Team, players: Player[], count: number) => (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <Users className="h-4 w-4 text-primary" />
        <h2 className="font-semibold text-sm">{team.name}</h2>
        <Badge
          variant={count === 11 ? 'default' : 'outline'}
          className={cn('ml-auto text-[10px]', count === 11 && 'bg-green-600')}
        >
          {count}/11 selected
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {players.map((player) => {
          const isSelected = selectedIds.has(player.id);
          const teamFull = count >= 11 && !isSelected;
          return (
            <button
              key={player.id}
              type="button"
              disabled={teamFull}
              onClick={() => togglePlayer(player.id)}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border transition-all text-left',
                'hover:border-primary/50',
                isSelected
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-card',
                teamFull && 'opacity-40 cursor-not-allowed'
              )}
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{player.name}</p>
                <p className="text-[10px] text-muted-foreground">{getRoleLabel(player.role)}</p>
              </div>
              {isSelected && <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />}
            </button>
          );
        })}
      </div>
    </section>
  );

  return (
    <div className="container-mobile py-6 space-y-5">
      <Link
        href="/admin"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Admin
      </Link>

      <div>
        <h1 className="text-xl font-bold">Set Playing XI</h1>
        <p className="text-xs text-muted-foreground mt-1">
          {squadData.team_1.name} vs {squadData.team_2.name}
        </p>
      </div>

      {prefilledFromPrev && (
        <Card className="p-3 border-blue-500/30 bg-blue-500/10 flex items-center gap-2">
          <History className="h-4 w-4 text-blue-400 shrink-0" />
          <p className="text-sm text-blue-400">Pre-filled from last match — adjust as needed</p>
        </Card>
      )}

      {error && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{error}</p>
        </Card>
      )}

      {success && (
        <Card className="p-3 border-green-500/50 bg-green-500/10">
          <p className="text-sm text-green-400">{success}</p>
        </Card>
      )}

      {renderTeamSection(squadData.team_1, squadData.team_1_players, team1Count)}
      {renderTeamSection(squadData.team_2, squadData.team_2_players, team2Count)}

      <div className="sticky bottom-20 bg-background/95 backdrop-blur-sm py-4 border-t border-border -mx-4 px-4">
        <Button
          onClick={handleSubmit}
          disabled={team1Count !== 11 || team2Count !== 11 || isSubmitting}
          size="lg"
          className="w-full"
        >
          {isSubmitting ? 'Saving...' : 'Save Playing XI'}
        </Button>
      </div>
    </div>
  );
}
