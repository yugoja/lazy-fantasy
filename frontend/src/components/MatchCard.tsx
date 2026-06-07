'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, Lock, Users, Zap, Loader2, CheckCircle2, X } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';
import { autoPickFootball } from '@/lib/api';

interface Team {
  name: string;
  short_name: string;
  flag_code?: string;
}

interface MatchCardProps {
  id: number;
  team1: Team;
  team2: Team;
  startTime: string;
  status: 'UPCOMING' | 'SCHEDULED' | 'LIVE' | 'COMPLETED';
  venue?: string;
  hasPredicted?: boolean;
  pointsEarned?: number;
  lineupAnnounced?: boolean;
  className?: string;
  sport?: 'football' | 'cricket';
  onAutoPickSuccess?: (matchId: number) => void;
}

type OverlayState = 'hidden' | 'picking' | 'loading' | 'success' | 'error';

const STRATEGIES: Array<{
  key: 'safe' | 'balanced' | 'bold';
  label: string;
  description: string;
}> = [
  { key: 'safe',     label: '📊 Accountant',    description: 'Safe picks, boring wins' },
  { key: 'balanced', label: '⚖️ Diplomat',      description: 'Hedged bets, no regrets' },
  { key: 'bold',     label: '🎲 Chaos Merchant', description: 'Who even needs logic?' },
];

function useCountdown(targetDate: string) {
  const [timeLeft, setTimeLeft] = useState('');
  const [isUrgent, setIsUrgent] = useState(false);

  useEffect(() => {
    const calc = () => {
      const now = new Date().getTime();
      const target = new Date(targetDate).getTime();
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft('Locked');
        setIsUrgent(false);
        return;
      }

      setIsUrgent(diff < 2 * 60 * 60 * 1000);

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 0) {
        setTimeLeft(`${days}d ${hours}h`);
      } else if (hours > 0) {
        setTimeLeft(`${hours}h ${minutes}m`);
      } else {
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        setTimeLeft(`${minutes}m ${seconds}s`);
      }
    };

    calc();
    const interval = setInterval(calc, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  return { timeLeft, isUrgent };
}

export function MatchCard({
  id,
  team1,
  team2,
  startTime,
  status,
  venue,
  hasPredicted,
  pointsEarned,
  lineupAnnounced,
  className,
  sport,
  onAutoPickSuccess,
}: MatchCardProps) {
  const isLive = status === 'LIVE';
  const isCompleted = status === 'COMPLETED';
  const isUpcoming = status === 'UPCOMING' || status === 'SCHEDULED';
  const { timeLeft: countdown, isUrgent } = useCountdown(startTime);
  const isLocked = countdown === 'Locked';
  const isTbd = team1.short_name === 'TBD' || team2.short_name === 'TBD';

  const [overlayState, setOverlayState] = useState<OverlayState>('hidden');
  const [overlayError, setOverlayError] = useState('');
  const [localHasPredicted, setLocalHasPredicted] = useState(hasPredicted ?? false);

  useEffect(() => {
    setLocalHasPredicted(hasPredicted ?? false);
  }, [hasPredicted]);

  const handleStrategyPick = async (strategy: 'safe' | 'balanced' | 'bold') => {
    setOverlayState('loading');
    setOverlayError('');
    try {
      await autoPickFootball(id, strategy);
      setOverlayState('success');
      setLocalHasPredicted(true);
      onAutoPickSuccess?.(id);
      setTimeout(() => setOverlayState('hidden'), 1400);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong. Try again.';
      setOverlayError(message);
      setOverlayState('error');
    }
  };

  const closeOverlay = () => {
    setOverlayState('hidden');
    setOverlayError('');
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
    };
  };

  const { date, time } = formatDateTime(startTime);

  const flagUrl1 = getTeamLogoUrl(team1.short_name);
  const flagUrl2 = getTeamLogoUrl(team2.short_name);

  return (
    <Card className={cn('relative overflow-hidden p-4 hover:border-primary/50 transition-colors', className)}>
      <div className="flex flex-col gap-3">
        {/* Status Badge + Predicted + Countdown */}
        <div className="flex items-center gap-2">
          <Badge
            variant={isLive ? 'destructive' : isCompleted ? 'secondary' : 'default'}
            className={cn(
              'text-[10px] font-semibold uppercase',
              isLive && 'bg-destructive/10 text-destructive border-destructive/20'
            )}
          >
            {isLive && <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-destructive animate-pulse-dot" />}
            {isUpcoming ? 'UPCOMING' : status}
          </Badge>

          {pointsEarned !== undefined && (
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 text-[10px]">
              +{pointsEarned} pts
            </Badge>
          )}

          {localHasPredicted && pointsEarned === undefined && (
            <Badge variant="outline" className="text-[10px]">
              Predicted
            </Badge>
          )}

          {lineupAnnounced && isUpcoming && (
            <Badge variant="outline" className="bg-green-600/10 text-green-400 border-green-600/30 text-[10px]">
              <Users className="h-2.5 w-2.5 mr-1" />
              XI
            </Badge>
          )}

          {isUpcoming && countdown && (
            <div className={cn(
              'flex items-center gap-1.5 text-xs font-medium rounded-full px-2.5 py-1 ml-auto',
              countdown === 'Locked'
                ? 'text-red-400 bg-red-400/10'
                : isUrgent
                  ? 'text-orange-400 bg-orange-400/10'
                  : 'text-yellow-400 bg-yellow-400/10'
            )}>
              {countdown === 'Locked' ? <Lock className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
              <span>{countdown}</span>
            </div>
          )}
        </div>

        {/* Teams */}
        <div className="flex items-center justify-between gap-2">
          {/* Team 1 */}
          <div className="flex items-center gap-2 flex-1">
            {flagUrl1 && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={flagUrl1}
                alt={team1.name}
                width={32}
                height={32}
                className="h-8 w-8 object-contain"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            )}
            <span className="font-bold text-lg truncate leading-tight">{team1.name}</span>
          </div>

          {/* VS */}
          <span className="text-xs text-muted-foreground font-medium px-2">vs</span>

          {/* Team 2 */}
          <div className="flex items-center gap-2 flex-1 justify-end">
            <span className="font-bold text-lg truncate leading-tight text-right">{team2.name}</span>
            {flagUrl2 && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={flagUrl2}
                alt={team2.name}
                width={32}
                height={32}
                className="h-8 w-8 object-contain"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            )}
          </div>
        </div>

        {/* Venue & Time */}
        <div className="text-xs text-muted-foreground">
          {venue && <div className="truncate">{venue}</div>}
          <div>
            {date} • {time}
          </div>
        </div>

        {/* Action Buttons */}
        {isUpcoming && isTbd && (
          <div className="w-full text-center text-xs text-muted-foreground rounded-md border border-dashed border-border py-2">
            Teams to be decided
          </div>
        )}

        {isUpcoming && !isLocked && !isTbd && (
          <div className="flex gap-2">
            <Link href={`/matches/${id}/predict`} className="flex-1">
              <Button
                className={cn('w-full', localHasPredicted && 'border-primary text-primary bg-primary/8')}
                size="default"
                variant={localHasPredicted ? 'outline' : 'default'}
              >
                {localHasPredicted ? 'Update Prediction' : 'Make Prediction'}
              </Button>
            </Link>

            {sport === 'football' && (
              <Button
                size="default"
                variant="outline"
                className="border-primary/40 text-primary hover:bg-primary/10 px-3 shrink-0"
                onClick={() => setOverlayState('picking')}
                aria-label="Auto Pick"
              >
                <Zap className="h-4 w-4 mr-1" />
                Auto
              </Button>
            )}
          </div>
        )}

        {isLive && (
          <Link href={`/matches/${id}`}>
            <Button className="w-full" size="sm" variant="outline">
              View Live
            </Button>
          </Link>
        )}

        {isCompleted && (
          <Link href={`/matches/${id}`}>
            <Button className="w-full" size="sm" variant="secondary">
              View Results
            </Button>
          </Link>
        )}
      </div>

      {/* Strategy Picker Overlay */}
      {overlayState !== 'hidden' && (
        <div className="absolute inset-0 z-10 flex flex-col rounded-[inherit] bg-card/95 backdrop-blur-sm p-4">

          {overlayState === 'loading' && (
            <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Picking your squad…
            </div>
          )}

          {overlayState === 'success' && (
            <div className="flex flex-1 items-center justify-center gap-2 text-sm font-semibold text-primary">
              <CheckCircle2 className="h-5 w-5" />
              Prediction saved!
            </div>
          )}

          {(overlayState === 'picking' || overlayState === 'error') && (
            <div className="flex flex-col flex-1 justify-center gap-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Auto Pick Strategy</span>
                <button
                  onClick={closeOverlay}
                  className="text-muted-foreground hover:text-foreground transition-colors p-0.5"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {overlayError && (
                <p className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                  {overlayError}
                </p>
              )}

              <div className="flex gap-2">
                {STRATEGIES.map(({ key, label, description }) => (
                  <button
                    key={key}
                    onClick={() => handleStrategyPick(key)}
                    className="flex flex-col items-center justify-center flex-1 rounded-2xl border border-border bg-background py-3 px-2 text-center hover:border-primary/60 hover:bg-primary/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    <span className="text-xs font-semibold leading-tight">{label}</span>
                    <span className="text-[10px] text-muted-foreground leading-tight mt-0.5">{description}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
