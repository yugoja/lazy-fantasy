'use client';

import { useState } from 'react';
import Link from 'next/link';
import { DugoutEvent, dismissDugoutEvent } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, CheckCheck, Users, X } from 'lucide-react';
import { cn } from '@/lib/utils';

function getInitials(name: string) {
  return name.substring(0, 2).toUpperCase();
}

function eventLabel(event: DugoutEvent) {
  return event.display_name || event.username;
}

function Avatar({ event }: { event: DugoutEvent }) {
  return (
    <div className={cn(
      'h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
      event.is_me ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
    )}>
      {getInitials(eventLabel(event))}
    </div>
  );
}

function DismissButton({ onDismiss }: { onDismiss: () => void }) {
  return (
    <button
      onClick={onDismiss}
      className="h-6 w-6 rounded-full flex items-center justify-center text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted transition-colors shrink-0"
      aria-label="Dismiss"
    >
      <X className="h-3 w-3" />
    </button>
  );
}

function ContrарianCard({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  return (
    <Card className="border-border/60 bg-muted/40">
      <CardContent className="p-3">
        <div className="flex items-center gap-2.5">
          <Avatar event={event} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-sm">{event.is_me ? 'You' : eventLabel(event)}</span>
              <Badge className="text-[10px] px-1.5 py-0 bg-orange-500/20 text-orange-400 border-orange-500/30 hover:bg-orange-500/20">
                Lone Wolf
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {event.is_me ? 'You picked' : 'Picked'}{' '}
              <span className="font-medium text-foreground">{event.team_short_name}</span>
              {' '}— only one in{' '}
              <span className="font-medium">{event.league_name}</span>
            </p>
          </div>
          <DismissButton onDismiss={onDismiss} />
        </div>
        {event.match_id && (
          <div className="mt-2 flex justify-end">
            <Link href={`/leagues/${event.league_id}/match/${event.match_id}`}>
              <Button variant="ghost" size="sm" className="h-6 text-[11px] text-orange-400 hover:text-orange-300 px-2">
                See all picks →
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AgreementRow({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  return (
    <div className="flex items-center gap-2.5 py-2 px-1">
      <div className="h-7 w-7 rounded-full bg-green-500/10 flex items-center justify-center shrink-0">
        <CheckCheck className="h-3.5 w-3.5 text-green-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="font-semibold">You</span>
          {' and '}
          <span className="font-semibold">{eventLabel(event)}</span>
          {' agree on '}
          <span className="text-green-400 font-semibold">{event.agreement_count}/6</span>
          {' picks'}
        </p>
        <p className="text-[11px] text-muted-foreground">{event.league_name}</p>
      </div>
      {event.match_id && (
        <Link href={`/leagues/${event.league_id}/match/${event.match_id}`}>
          <Button variant="ghost" size="sm" className="h-6 text-[11px] px-2 text-muted-foreground">
            Compare
          </Button>
        </Link>
      )}
      <DismissButton onDismiss={onDismiss} />
    </div>
  );
}

function StreakCard({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  const flames = Math.min(event.streak_count ?? 3, 5);
  return (
    <Card className="border-border/60 bg-muted/40">
      <CardContent className="p-3">
        <div className="flex items-center gap-2.5">
          <Avatar event={event} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-sm">{event.is_me ? 'You' : eventLabel(event)}</span>
              <Badge className="text-[10px] px-1.5 py-0 bg-purple-500/20 text-purple-400 border-purple-500/30 hover:bg-purple-500/20">
                Oracle
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              <span className="font-medium text-yellow-400">{event.streak_count}-match</span>
              {' winning streak in '}
              <span className="font-medium">{event.league_name}</span>
              {' '}{'🔥'.repeat(flames)}
            </p>
          </div>
          <DismissButton onDismiss={onDismiss} />
        </div>
      </CardContent>
    </Card>
  );
}

function RankShiftRow({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  const movedUp = (event.rank_delta ?? 0) > 0;
  return (
    <div className="flex items-center gap-2.5 py-2 px-1">
      <div className={cn(
        'h-7 w-7 rounded-full flex items-center justify-center shrink-0',
        movedUp ? 'bg-green-500/10' : 'bg-red-500/10'
      )}>
        {movedUp
          ? <TrendingUp className="h-3.5 w-3.5 text-green-500" />
          : <TrendingDown className="h-3.5 w-3.5 text-red-400" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          {'You '}
          <span className={cn('font-semibold', movedUp ? 'text-green-400' : 'text-red-400')}>
            {movedUp ? `moved up to #${event.rank}` : `dropped to #${event.rank}`}
          </span>
        </p>
        <p className="text-[11px] text-muted-foreground">{event.league_name}</p>
      </div>
      <Link href={`/leaderboard?league=${event.league_id}`}>
        <Button variant="ghost" size="sm" className="h-6 text-[11px] px-2 text-muted-foreground">
          Leaderboard
        </Button>
      </Link>
      <DismissButton onDismiss={onDismiss} />
    </div>
  );
}

function eventKey(e: DugoutEvent) {
  return `${e.type}:${e.league_id}:${e.match_id}:${e.username}`;
}

export function DugoutFeed({ events: initialEvents }: { events: DugoutEvent[] }) {
  const [events, setEvents] = useState(initialEvents);

  const handleDismiss = async (event: DugoutEvent) => {
    // Optimistic removal
    setEvents(prev => prev.filter(e => eventKey(e) !== eventKey(event)));
    try {
      await dismissDugoutEvent(event);
    } catch {
      // Restore on failure
      setEvents(prev => [...prev, event]);
    }
  };

  if (events.length === 0) {
    return (
      <section>
        <div className="flex items-center gap-2 mb-3">
          <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <h2 className="text-lg font-bold">The Dugout</h2>
        </div>
        <Card className="p-6 text-center">
          <div className="flex flex-col items-center gap-2">
            <Users className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">Nothing here yet — join a league and start predicting to see what your crew is up to</p>
            <Link href="/leagues">
              <Button size="sm" variant="outline" className="mt-1">Browse Leagues</Button>
            </Link>
          </div>
        </Card>
      </section>
    );
  }

  const cardEvents = events.filter(e => e.type === 'contrarian' || e.type === 'streak');
  const rowEvents = events.filter(e => e.type === 'agreement' || e.type === 'rank_shift');

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        <h2 className="text-lg font-bold">The Dugout</h2>
        <span className="text-xs text-muted-foreground ml-auto">{events.length} updates</span>
      </div>

      <div className="space-y-2">
        {rowEvents.length > 0 && (
          <Card className="border-border/50">
            <CardContent className="p-1 divide-y divide-border/50">
              {rowEvents.map((event) => (
                event.type === 'rank_shift'
                  ? <RankShiftRow key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
                  : <AgreementRow key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
              ))}
            </CardContent>
          </Card>
        )}

        {cardEvents.map((event) => (
          event.type === 'contrarian'
            ? <ContrарianCard key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
            : <StreakCard key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
        ))}
      </div>
    </section>
  );
}
