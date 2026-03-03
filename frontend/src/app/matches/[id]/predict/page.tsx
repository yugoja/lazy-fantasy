'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/lib/auth';
import { getMatchPlayers, getMyPredictions, submitPrediction, ApiError } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ArrowLeft, Trophy, Target, Star, CheckCircle2 } from 'lucide-react';
import { cn, getFlagUrl } from '@/lib/utils';

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

interface MatchData {
  match_id: number;
  team_1: Team;
  team_2: Team;
  team_1_players: Player[];
  team_2_players: Player[];
  lineup_announced: boolean;
  start_time: string;
}

function getInitials(name: string) {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();
}

function formatCountdown(startTime: string): string {
  const diff = new Date(startTime).getTime() - Date.now();
  if (diff <= 0) return 'soon';
  const totalMins = Math.floor(diff / 60000);
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
  return `${mins} min`;
}

function buildShareText(team1: string, team2: string, startTime: string): string {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
  return [
    `🏏 ${team1} vs ${team2} — predictions are open!`,
    '',
    `I've locked in my call. Have you? ⏰`,
    `Closes in ${formatCountdown(startTime)} 👇`,
    `${appUrl}/predictions`,
  ].join('\n');
}

function getRoleLabel(role: string) {
  const map: Record<string, string> = {
    batsman: 'BAT',
    batter: 'BAT',
    bowler: 'BOWL',
    all_rounder: 'AR',
    allrounder: 'AR',
    wicket_keeper: 'WK',
    wicketkeeper: 'WK',
  };
  return map[role.toLowerCase()] || role.substring(0, 4).toUpperCase();
}

export default function PredictPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const matchId = Number(params.id);

  const [matchData, setMatchData] = useState<MatchData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Form state
  const [winnerId, setWinnerId] = useState<number | null>(null);
  const [mostRunsId, setMostRunsId] = useState<number | null>(null);
  const [mostWicketsId, setMostWicketsId] = useState<number | null>(null);
  const [pomId, setPomId] = useState<number | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (matchId && isAuthenticated) {
      loadMatchData();
    }
  }, [matchId, isAuthenticated]);

  const loadMatchData = async () => {
    try {
      const [matchResult, predictionsResult] = await Promise.allSettled([
        getMatchPlayers(matchId),
        getMyPredictions(),
      ]);

      if (matchResult.status === 'fulfilled') {
        const data = matchResult.value;
        if (new Date(data.start_time) <= new Date()) {
          router.push('/predictions');
          return;
        }
        setMatchData(data);
      } else {
        setError('Failed to load match data');
      }

      // Pre-fill form if user already predicted this match
      if (predictionsResult.status === 'fulfilled') {
        const existing = predictionsResult.value.find(p => p.match_id === matchId);
        if (existing) {
          setWinnerId(existing.predicted_winner_id);
          setMostRunsId(existing.predicted_most_runs_player_id);
          setMostWicketsId(existing.predicted_most_wickets_player_id);
          setPomId(existing.predicted_pom_player_id);
          setIsEditing(true);
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load match data');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const filledCount = [winnerId, mostRunsId, mostWicketsId, pomId].filter(Boolean).length;
  const progressPercent = (filledCount / 4) * 100;

  const handleSubmit = async () => {
    setError('');

    if (!winnerId || !mostRunsId || !mostWicketsId || !pomId) {
      setError('Please fill in all predictions');
      return;
    }

    setIsSubmitting(true);

    try {
      await submitPrediction({
        match_id: matchId,
        predicted_winner_id: winnerId,
        predicted_most_runs_player_id: mostRunsId,
        predicted_most_wickets_player_id: mostWicketsId,
        predicted_pom_player_id: pomId,
      });
      setShowSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to submit prediction');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!matchData) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Card className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error || 'Match not found'}</p>
          <Link href="/predictions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Matches
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const allPlayers = [...matchData.team_1_players, ...matchData.team_2_players];

  const renderPlayerGrid = (
    selectedId: number | null,
    onSelect: (id: number) => void,
    filterPlayers?: Player[]
  ) => {
    const players = filterPlayers || allPlayers;
    return (
      <div className="grid grid-cols-3 gap-2">
        {players.map((player) => {
          const isSelected = selectedId === player.id;
          return (
            <button
              key={player.id}
              type="button"
              onClick={() => onSelect(player.id)}
              className={cn(
                'flex flex-col items-center gap-1 p-3 rounded-lg border transition-all',
                'hover:border-primary/50',
                isSelected
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-card'
              )}
            >
              <div
                className={cn(
                  'h-10 w-10 rounded-full flex items-center justify-center text-xs font-bold',
                  isSelected
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {getInitials(player.name)}
              </div>
              <span className="text-xs font-medium truncate w-full text-center">
                {player.name.split(' ').pop()}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {getRoleLabel(player.role)}
              </span>
              {isSelected && (
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
              )}
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div className="container-mobile py-6 space-y-5">
      {/* Back navigation */}
      <Link
        href="/predictions"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>

      {/* Match Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold">
            {matchData.team_1.name} vs {matchData.team_2.name}
          </h1>
          {matchData.lineup_announced && (
            <Badge className="bg-green-600 text-[10px]">Playing XI</Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {new Date(matchData.start_time).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
          {' '}&middot; {new Date(matchData.start_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })}
        </p>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <Progress value={progressPercent} className="h-2" />
        <div className="flex justify-between">
          {['Winner', 'Runs', 'Wickets', 'POM'].map((label, i) => {
            const filled = [winnerId, mostRunsId, mostWicketsId, pomId][i] !== null;
            return (
              <div
                key={label}
                className={cn(
                  'h-2 w-2 rounded-full',
                  filled ? 'bg-primary' : 'bg-muted'
                )}
              />
            );
          })}
        </div>
      </div>

      {error && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{error}</p>
        </Card>
      )}

      {/* Section: Match Winner */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4 text-primary" />
          <h2 className="font-semibold text-sm">Match Winner</h2>
          <Badge variant="outline" className="ml-auto text-[10px]">+10 pts</Badge>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[matchData.team_1, matchData.team_2].map((team) => {
            const isSelected = winnerId === team.id;
            const flagSrc = getFlagUrl(team.short_name);
            return (
              <button
                key={team.id}
                type="button"
                onClick={() => setWinnerId(team.id)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-lg border transition-all',
                  'hover:border-primary/50',
                  isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border bg-card'
                )}
              >
                {flagSrc && (
                  <Image
                    src={flagSrc}
                    alt={`${team.name} flag`}
                    width={32}
                    height={24}
                    className="h-6 w-8 object-cover rounded-sm"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                )}
                <span className="font-semibold text-sm">{team.short_name}</span>
                <span className="text-xs text-muted-foreground">{team.name}</span>
                {isSelected && (
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* Section: Top Batsman (Most Runs) */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          <h2 className="font-semibold text-sm">Top Batsman (Most Runs)</h2>
          <Badge variant="outline" className="ml-auto text-[10px]">+20 pts</Badge>
        </div>
        {renderPlayerGrid(mostRunsId, setMostRunsId)}
      </section>

      {/* Section: Top Bowler (Most Wickets) */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          <h2 className="font-semibold text-sm">Top Bowler (Most Wickets)</h2>
          <Badge variant="outline" className="ml-auto text-[10px]">+20 pts</Badge>
        </div>
        {renderPlayerGrid(mostWicketsId, setMostWicketsId)}
      </section>

      {/* Section: Man of the Match */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Star className="h-4 w-4 text-primary" />
          <h2 className="font-semibold text-sm">Man of the Match</h2>
          <Badge variant="outline" className="ml-auto text-[10px]">+50 pts</Badge>
        </div>
        {renderPlayerGrid(pomId, setPomId)}
      </section>

      {/* Submit Area */}
      <div className="sticky bottom-20 bg-background/95 backdrop-blur-sm py-4 border-t border-border -mx-4 px-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {filledCount < 4
              ? `${filledCount} of 4 predictions made`
              : 'All predictions made!'}
          </p>
          <Button
            onClick={handleSubmit}
            disabled={filledCount < 4 || isSubmitting}
            size="lg"
          >
            {isSubmitting ? 'Submitting...' : isEditing ? 'Update Prediction' : 'Submit'}
          </Button>
        </div>
      </div>

      {/* Success Dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent className="sm:max-w-md">
          {/* Animated icon */}
          <div className="flex justify-center mt-2 mb-1">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
              <div className="relative h-16 w-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
            </div>
          </div>

          <DialogHeader className="items-center text-center pb-0">
            <DialogTitle className="text-xl">
              {isEditing ? 'Prediction Updated!' : "You're locked in!"}
            </DialogTitle>
            <DialogDescription>
              {matchData.team_1.short_name} vs {matchData.team_2.short_name}
            </DialogDescription>
          </DialogHeader>

          {/* Summary card */}
          <div className="rounded-lg border border-border bg-muted/30 divide-y divide-border text-sm">
            {(() => {
              const winnerTeam = winnerId === matchData.team_1.id ? matchData.team_1 : matchData.team_2;
              const runsPlayer = allPlayers.find(p => p.id === mostRunsId);
              const wicketsPlayer = allPlayers.find(p => p.id === mostWicketsId);
              const pomPlayer = allPlayers.find(p => p.id === pomId);
              const rows = [
                { icon: <Trophy className="h-3.5 w-3.5 text-primary" />, label: 'Winner', value: winnerTeam?.short_name, pts: 10 },
                { icon: <Target className="h-3.5 w-3.5 text-primary" />, label: 'Top Bat', value: runsPlayer?.name.split(' ').pop(), pts: 20 },
                { icon: <Target className="h-3.5 w-3.5 text-primary" />, label: 'Top Bowl', value: wicketsPlayer?.name.split(' ').pop(), pts: 20 },
                { icon: <Star className="h-3.5 w-3.5 text-primary" />, label: 'MOTM', value: pomPlayer?.name.split(' ').pop(), pts: 50 },
              ];
              return rows.map((row) => (
                <div key={row.label} className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    {row.icon}
                    <span className="text-xs">{row.label}</span>
                  </div>
                  <span className="font-medium">{row.value}</span>
                  <span className="text-xs text-muted-foreground">+{row.pts} pts</span>
                </div>
              ));
            })()}
            <div className="flex items-center justify-between px-4 py-2.5 bg-primary/5">
              <span className="text-xs text-muted-foreground">Potential total</span>
              <span className="font-bold text-primary">Up to 100 pts</span>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(buildShareText(matchData.team_1.short_name, matchData.team_2.short_name, matchData.start_time))}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg border border-[#25D366]/30 bg-[#25D366]/5 text-[#25D366] text-sm font-medium"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>
              Nudge your group
            </a>
            <Link href="/predictions" className="w-full">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Matches
              </Button>
            </Link>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
