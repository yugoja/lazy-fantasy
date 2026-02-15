'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
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
}

function getInitials(name: string) {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();
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
        setMatchData(matchResult.value);
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
        href="/matches"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>

      {/* Match Header */}
      <div>
        <h1 className="text-xl font-bold">
          {matchData.team_1.name} vs {matchData.team_2.name}
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          {new Date(Date.now()).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
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
                  <img
                    src={flagSrc}
                    alt={`${team.name} flag`}
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
          <DialogHeader className="items-center text-center">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
              <CheckCircle2 className="h-8 w-8 text-primary" />
            </div>
            <DialogTitle className="text-xl">{isEditing ? 'Prediction Updated!' : 'Prediction Submitted!'}</DialogTitle>
            <DialogDescription>
              Your predictions for {matchData.team_1.short_name} vs {matchData.team_2.short_name} have been {isEditing ? 'updated' : 'recorded'}.
            </DialogDescription>
          </DialogHeader>
          <Link href="/predictions" className="w-full">
            <Button variant="outline" className="w-full">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Matches
            </Button>
          </Link>
        </DialogContent>
      </Dialog>
    </div>
  );
}
