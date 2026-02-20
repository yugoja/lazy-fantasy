'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock } from 'lucide-react';
import { cn, getFlagUrl } from '@/lib/utils';

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
  className?: string;
}

function useCountdown(targetDate: string) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    const calc = () => {
      const now = new Date().getTime();
      const target = new Date(targetDate).getTime();
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft('Starting soon');
        return;
      }

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

  return timeLeft;
}

export function MatchCard({
  id,
  team1,
  team2,
  startTime,
  status,
  venue,
  hasPredicted,
  className,
}: MatchCardProps) {
  const isLive = status === 'LIVE';
  const isCompleted = status === 'COMPLETED';
  const isUpcoming = status === 'UPCOMING' || status === 'SCHEDULED';
  const countdown = useCountdown(startTime);

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
    };
  };

  const { date, time } = formatDateTime(startTime);

  const flagUrl1 = getFlagUrl(team1.short_name);
  const flagUrl2 = getFlagUrl(team2.short_name);

  return (
    <Card className={cn('p-4 hover:border-primary/50 transition-colors', className)}>
      <div className="flex flex-col gap-3">
        {/* Status Badge + Countdown */}
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

          {isUpcoming && countdown && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-yellow-400 bg-yellow-400/10 rounded-full px-2.5 py-1 ml-auto">
              <Clock className="h-3 w-3" />
              <span>{countdown}</span>
            </div>
          )}
        </div>

        {/* Teams */}
        <div className="flex items-center justify-between gap-2">
          {/* Team 1 */}
          <div className="flex items-center gap-2 flex-1">
            {flagUrl1 && (
              <Image
                src={flagUrl1}
                alt={`${team1.name} flag`}
                width={32}
                height={24}
                className="h-6 w-8 object-cover rounded-sm"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            )}
            <span className="font-semibold text-sm truncate">{team1.short_name}</span>
          </div>

          {/* VS */}
          <span className="text-xs text-muted-foreground font-medium px-2">vs</span>

          {/* Team 2 */}
          <div className="flex items-center gap-2 flex-1 justify-end">
            <span className="font-semibold text-sm truncate">{team2.short_name}</span>
            {flagUrl2 && (
              <Image
                src={flagUrl2}
                alt={`${team2.name} flag`}
                width={32}
                height={24}
                className="h-6 w-8 object-cover rounded-sm"
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

        {/* Action Button */}
        {isUpcoming && (
          <Link href={`/matches/${id}/predict`}>
            <Button className={cn('w-full', hasPredicted && 'border-primary text-primary')} size="sm" variant={hasPredicted ? 'outline' : 'default'}>
              {hasPredicted ? 'Update Prediction' : 'Make Prediction'}
            </Button>
          </Link>
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
    </Card>
  );
}
