import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Users } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Team {
  name: string;
  short_name: string;
  flag_code?: string; // e.g., 'ind', 'aus', 'eng'
}

interface MatchCardProps {
  id: number;
  team1: Team;
  team2: Team;
  startTime: string;
  status: 'UPCOMING' | 'LIVE' | 'COMPLETED';
  venue?: string;
  participantCount?: number;
  onPredict?: () => void;
  className?: string;
}

export function MatchCard({
  id,
  team1,
  team2,
  startTime,
  status,
  venue,
  participantCount,
  onPredict,
  className,
}: MatchCardProps) {
  const isLive = status === 'LIVE';
  const isCompleted = status === 'COMPLETED';
  const isUpcoming = status === 'UPCOMING';

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
    };
  };

  const { date, time } = formatDateTime(startTime);

  // Get flag URL from flagcdn API
  const getFlagUrl = (flagCode: string) => {
    return `https://flagcdn.com/48x36/${flagCode}.png`;
  };

  return (
    <Card className={cn('p-4 hover:border-primary/50 transition-colors', className)}>
      <div className="flex flex-col gap-3">
        {/* Status Badge */}
        <div className="flex items-center justify-between">
          <Badge
            variant={isLive ? 'destructive' : isCompleted ? 'secondary' : 'default'}
            className={cn(
              'text-[10px] font-semibold uppercase',
              isLive && 'bg-destructive/10 text-destructive border-destructive/20'
            )}
          >
            {isLive && <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-destructive animate-pulse-dot" />}
            {status}
          </Badge>

          {participantCount && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Users className="h-3 w-3" />
              <span>{participantCount}</span>
            </div>
          )}
        </div>

        {/* Teams */}
        <div className="flex items-center justify-between gap-2">
          {/* Team 1 */}
          <div className="flex items-center gap-2 flex-1">
            {team1.flag_code && (
              <img
                src={getFlagUrl(team1.flag_code)}
                alt={`${team1.name} flag`}
                className="h-6 w-8 object-cover rounded-sm"
              />
            )}
            <span className="font-semibold text-sm truncate">{team1.short_name}</span>
          </div>

          {/* VS */}
          <span className="text-xs text-muted-foreground font-medium px-2">vs</span>

          {/* Team 2 */}
          <div className="flex items-center gap-2 flex-1 justify-end">
            <span className="font-semibold text-sm truncate">{team2.short_name}</span>
            {team2.flag_code && (
              <img
                src={getFlagUrl(team2.flag_code)}
                alt={`${team2.name} flag`}
                className="h-6 w-8 object-cover rounded-sm"
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
            <Button className="w-full" size="sm">
              Make Prediction
            </Button>
          </Link>
        )}

        {isLive && (
          <Button className="w-full" size="sm" variant="outline">
            View Live
          </Button>
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
