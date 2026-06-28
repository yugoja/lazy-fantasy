'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DugoutEvent, dismissDugoutEvent } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, CheckCheck, Users, X, Trophy, ArrowRight, Megaphone } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MatchVerdictCard } from '@/components/MatchVerdictCard';
import { useAuth } from '@/lib/auth';
import { analytics } from '@/lib/analytics';

// Fire a dugout_action with the event's context attached.
function trackDugoutAction(event: DugoutEvent, action: string) {
  analytics.dugoutAction({
    action,
    dugout_event_type: event.type,
    match_id: event.match_id != null ? String(event.match_id) : undefined,
    league_id: event.league_id != null ? String(event.league_id) : undefined,
  });
}

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
            <Link href={`/leagues/${event.league_id}/match/${event.match_id}`} onClick={() => trackDugoutAction(event, 'view_picks')}>
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
          <span className="text-green-400 font-semibold">{event.agreement_count}/{event.agreement_total ?? 6}</span>
          {' picks'}
        </p>
        <p className="text-[11px] text-muted-foreground">{event.league_name}</p>
      </div>
      {event.match_id && (
        <Link href={`/leagues/${event.league_id}/match/${event.match_id}`} onClick={() => trackDugoutAction(event, 'compare')}>
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
      <Link href={`/leaderboard?league=${event.league_id}`} onClick={() => trackDugoutAction(event, 'leaderboard')}>
        <Button variant="ghost" size="sm" className="h-6 text-[11px] px-2 text-muted-foreground">
          Leaderboard
        </Button>
      </Link>
      <DismissButton onDismiss={onDismiss} />
    </div>
  );
}

function formatLockCountdown(iso: string, nowMs: number): string | null {
  const diff = new Date(iso).getTime() - nowMs;
  if (diff <= 0) return null;
  const totalSec = Math.floor(diff / 1000);
  const d = Math.floor(totalSec / 86400);
  const h = Math.floor((totalSec % 86400) / 3600);
  if (d > 0) return `${d}d ${h}h`;
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

// The marquee CTA in the dugout: claim your tournament-long picks before the
// group stage ends. Green-tinted so it reads as an action, not a social signal.
function TournamentPicksCard({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (!event.picks_lock_at) return;
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [event.picks_lock_at]);

  const countdown = event.picks_lock_at ? formatLockCountdown(event.picks_lock_at, nowMs) : null;
  const hasPicks = !!event.has_picks;

  return (
    <Card className="relative overflow-hidden border-primary/30 bg-primary/[0.06]">
      {/* Trophy watermark — clipped into the corner for a tournament-prize feel */}
      <Trophy className="pointer-events-none absolute -bottom-5 -right-4 h-28 w-28 rotate-12 text-primary/10" aria-hidden />
      <CardContent className="relative p-4">
        <div className="flex items-start justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-amber-400">
            <Trophy className="h-3 w-3" /> Mega Picks
          </span>
          <DismissButton onDismiss={onDismiss} />
        </div>

        <h3 className="mt-2 font-heading text-[19px] font-bold leading-tight">
          {hasPicks ? 'Final four locked — tweak ’em anytime.' : 'Who lifts it? Call your final four.'}
        </h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Your 4 semi-finalists plus Golden{' '}
          <span className="font-medium text-foreground">Boot</span>,{' '}
          <span className="font-medium text-foreground">Ball</span> &{' '}
          <span className="font-medium text-foreground">Glove</span>.
        </p>

        <div className="mt-3 flex items-center gap-1.5 text-[11px]">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
          <span className="font-semibold text-amber-400">Open till the group stage ends</span>
          {countdown && <span className="text-muted-foreground">· closes in {countdown}</span>}
        </div>

        <Link href={`/tournaments/${event.tournament_id}/picks`} className="mt-3.5 block" onClick={() => trackDugoutAction(event, 'tournament_picks')}>
          <Button className="w-full font-heading font-bold">
            {hasPicks ? 'Tweak your picks' : 'Make your picks'}
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

// A one-off system message (e.g. a scoring correction). When an announcement
// carries a link + expiry it renders as an urgent CTA with a live countdown;
// otherwise it falls back to a plain informational card.
function AnnouncementCard({ event, onDismiss }: { event: DugoutEvent; onDismiss: () => void }) {
  const hasAction = !!event.announcement_link && !!event.announcement_expires_at;
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!hasAction) return;
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [hasAction]);

  const countdown = hasAction ? formatLockCountdown(event.announcement_expires_at!, nowMs) : null;

  if (hasAction) {
    return (
      <Card className="relative overflow-hidden border-amber-500/40 bg-amber-500/[0.07]">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-amber-400">
              <Megaphone className="h-3 w-3" /> Picks closing
            </span>
            <DismissButton onDismiss={onDismiss} />
          </div>

          <h3 className="font-heading text-[17px] font-bold leading-tight">
            {event.announcement_title ?? 'Announcement'}
          </h3>
          {event.announcement_body && (
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{event.announcement_body}</p>
          )}

          {countdown && (
            <div className="mt-3 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse shrink-0" />
              <span className="font-mono text-sm font-bold text-amber-400 tabular-nums">{countdown}</span>
              <span className="text-xs text-muted-foreground">left</span>
            </div>
          )}

          <Link href={event.announcement_link!} className="mt-3 block" onClick={() => trackDugoutAction(event, 'announcement_cta')}>
            <Button className="w-full bg-amber-500 hover:bg-amber-400 text-black font-bold">
              Make your picks <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-amber-500/30 bg-amber-500/[0.06]">
      <CardContent className="p-3">
        <div className="flex items-start gap-2.5">
          <div className="h-8 w-8 rounded-full bg-amber-500/15 flex items-center justify-center shrink-0">
            <Megaphone className="h-4 w-4 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm">{event.announcement_title ?? 'Announcement'}</p>
            {event.announcement_body && (
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{event.announcement_body}</p>
            )}
          </div>
          <DismissButton onDismiss={onDismiss} />
        </div>
      </CardContent>
    </Card>
  );
}

function eventKey(e: DugoutEvent) {
  return `${e.type}:${e.league_id}:${e.match_id}:${e.username}`;
}

export function DugoutFeed({ events: initialEvents }: { events: DugoutEvent[] }) {
  const [events, setEvents] = useState(initialEvents);
  const { username } = useAuth();

  // Fire dugout_opened once per mount when the feed surfaces at least one event.
  useEffect(() => {
    if (initialEvents.length > 0) {
      analytics.dugoutOpened({ event_count: initialEvents.length });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDismiss = async (event: DugoutEvent) => {
    trackDugoutAction(event, 'dismiss');
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
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
          <h2 className="text-lg font-bold">The Dugout</h2>
        </div>
        <div className="py-6 text-center">
          <p className="text-sm text-muted-foreground">Nothing here yet — predict a match to see what your crew is up to</p>
          <Link href="/leagues">
            <Button size="sm" variant="outline" className="mt-3">Browse Leagues</Button>
          </Link>
        </div>
      </section>
    );
  }

  const announcementEvents = events.filter(e => e.type === 'announcement');
  const pickEvents = events.filter(e => e.type === 'tournament_picks');
  const verdictEvents = events.filter(e => e.type === 'match_verdict');
  const cardEvents = events.filter(e => e.type === 'contrarian' || e.type === 'streak');
  const rowEvents = events.filter(e => e.type === 'agreement' || e.type === 'rank_shift');

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
        <h2 className="text-lg font-bold">The Dugout</h2>
        <span className="text-[11px] text-muted-foreground ml-auto">{events.length} updates</span>
      </div>

      <div className="space-y-2">
        {/* System announcements — lead the feed */}
        {announcementEvents.map((event) => (
          <AnnouncementCard key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
        ))}

        {/* Tournament-picks CTA — marquee item, surfaces first */}
        {pickEvents.map((event) => (
          <TournamentPicksCard key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
        ))}

        {/* Verdict cards — full-width, own row */}
        {verdictEvents.map((event) => (
          <MatchVerdictCard
            key={eventKey(event)}
            event={event}
            currentUsername={username ?? null}
            onDismiss={() => handleDismiss(event)}
          />
        ))}

        {/* Row events — borderless, just dividers */}
        {rowEvents.length > 0 && (
          <div className="divide-y divide-border/40">
            {rowEvents.map((event) => (
              event.type === 'rank_shift'
                ? <RankShiftRow key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
                : <AgreementRow key={eventKey(event)} event={event} onDismiss={() => handleDismiss(event)} />
            ))}
          </div>
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
