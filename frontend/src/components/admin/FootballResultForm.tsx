'use client';

import { useState } from 'react';
import { API_BASE } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ChevronDown, ChevronUp, Wrench } from 'lucide-react';

interface Player {
  id: number;
  name: string;
  role: string;
}

interface Team {
  id: number;
  name: string;
  short_name: string;
}

interface PlayerEventState {
  minutes_played: number;
  goals: number;
  assists: number;
  red_card: boolean;
  own_goals: number;
  ingame_pen_saves: number;
  shootout_pen_saves: number;
  ingame_pen_misses: number;
}

function mkDefault(): PlayerEventState {
  return {
    minutes_played: 0,
    goals: 0,
    assists: 0,
    red_card: false,
    own_goals: 0,
    ingame_pen_saves: 0,
    shootout_pen_saves: 0,
    ingame_pen_misses: 0,
  };
}

interface Props {
  matchId: number;
  team1: Team;
  team2: Team;
  team1Players: Player[];
  team2Players: Player[];
  onSuccess: (predictionsProcessed: number) => void;
}

export default function FootballResultForm({
  matchId,
  team1,
  team2,
  team1Players,
  team2Players,
  onSuccess,
}: Props) {
  const [team1GoalsReg, setTeam1GoalsReg] = useState(0);
  const [team2GoalsReg, setTeam2GoalsReg] = useState(0);
  const [hasET, setHasET] = useState(false);
  const [team1GoalsET, setTeam1GoalsET] = useState(0);
  const [team2GoalsET, setTeam2GoalsET] = useState(0);
  const [hasPen, setHasPen] = useState(false);
  const [shootoutWinnerId, setShootoutWinnerId] = useState<number | null>(null);

  const allPlayers = [...team1Players, ...team2Players];
  const [events, setEvents] = useState<Record<number, PlayerEventState>>(() =>
    Object.fromEntries(allPlayers.map((p) => [p.id, mkDefault()]))
  );
  const [expandedTeam, setExpandedTeam] = useState<'team1' | 'team2' | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const updateEvent = (playerId: number, field: keyof PlayerEventState, value: number | boolean) => {
    setEvents((prev) => ({ ...prev, [playerId]: { ...prev[playerId], [field]: value } }));
  };

  const numInput = (
    playerId: number,
    field: keyof PlayerEventState,
    label: string,
    max = 20
  ) => (
    <div className="flex flex-col items-center gap-0.5 min-w-[48px]">
      <span className="text-[9px] text-muted-foreground leading-tight text-center">{label}</span>
      <Input
        type="number"
        min={0}
        max={max}
        value={(events[playerId]?.[field] as number) ?? 0}
        onChange={(e) => updateEvent(playerId, field, parseInt(e.target.value) || 0)}
        className="h-7 text-center text-xs px-1 w-full"
      />
    </div>
  );

  const renderPlayerTable = (players: Player[]) => (
    <div className="space-y-2">
      {players.map((p) => {
        const isGK = p.role?.toLowerCase().includes('goalkeeper') || p.role?.toLowerCase().includes('gk');
        return (
          <div key={p.id} className="border border-border rounded-md p-2 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium truncate max-w-[140px]">{p.name}</span>
              <span className="text-[9px] text-muted-foreground ml-1 shrink-0">{p.role}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {numInput(p.id, 'minutes_played', 'Mins', 120)}
              {numInput(p.id, 'goals', 'Goals')}
              {numInput(p.id, 'assists', 'Assists')}
              {numInput(p.id, 'own_goals', 'OG')}
              {numInput(p.id, 'ingame_pen_misses', 'Pen Miss')}
              {isGK && numInput(p.id, 'ingame_pen_saves', 'Pen Save')}
              {isGK && numInput(p.id, 'shootout_pen_saves', 'SO Save')}
              <div className="flex flex-col items-center gap-0.5 min-w-[48px]">
                <span className="text-[9px] text-muted-foreground leading-tight text-center">Red</span>
                <input
                  type="checkbox"
                  checked={!!events[p.id]?.red_card}
                  onChange={(e) => updateEvent(p.id, 'red_card', e.target.checked)}
                  className="mt-1.5 h-4 w-4 rounded"
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );

  const handleSubmit = async () => {
    setError('');
    setIsSubmitting(true);

    const activeEvents = allPlayers
      .filter((p) => {
        const ev = events[p.id];
        return (
          ev.minutes_played > 0 ||
          ev.goals > 0 ||
          ev.assists > 0 ||
          ev.red_card ||
          ev.own_goals > 0 ||
          ev.ingame_pen_saves > 0 ||
          ev.shootout_pen_saves > 0 ||
          ev.ingame_pen_misses > 0
        );
      })
      .map((p) => ({ player_id: p.id, ...events[p.id] }));

    const body: Record<string, unknown> = {
      team1_goals_reg: team1GoalsReg,
      team2_goals_reg: team2GoalsReg,
      player_events: activeEvents,
    };
    if (hasET) {
      body.team1_goals_et = team1GoalsET;
      body.team2_goals_et = team2GoalsET;
    }
    if (hasPen && shootoutWinnerId) {
      body.shootout_winner_id = shootoutWinnerId;
    }

    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`${API_BASE}/admin/matches/${matchId}/result/football`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || 'Failed to submit result');
      }
      const data = await resp.json();
      onSuccess(data.predictions_processed ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit result');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Wrench className="h-4 w-4 text-muted-foreground" />
          Manual Override
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scoreline */}
        <div className="space-y-2">
          <Label className="text-xs font-semibold">Regulation Score</Label>
          <div className="flex items-center gap-3">
            <div className="flex-1 space-y-1">
              <p className="text-[10px] text-muted-foreground">{team1.short_name}</p>
              <Input
                type="number"
                min={0}
                value={team1GoalsReg}
                onChange={(e) => setTeam1GoalsReg(parseInt(e.target.value) || 0)}
                className="text-center font-bold text-lg h-10"
              />
            </div>
            <span className="text-muted-foreground font-bold text-lg">–</span>
            <div className="flex-1 space-y-1">
              <p className="text-[10px] text-muted-foreground">{team2.short_name}</p>
              <Input
                type="number"
                min={0}
                value={team2GoalsReg}
                onChange={(e) => setTeam2GoalsReg(parseInt(e.target.value) || 0)}
                className="text-center font-bold text-lg h-10"
              />
            </div>
          </div>
        </div>

        {/* Extra Time toggle */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="has-et"
            checked={hasET}
            onChange={(e) => setHasET(e.target.checked)}
            className="h-4 w-4 rounded"
          />
          <Label htmlFor="has-et" className="text-xs cursor-pointer">Extra Time played</Label>
        </div>
        {hasET && (
          <div className="flex items-center gap-3 pl-6">
            <div className="flex-1 space-y-1">
              <p className="text-[10px] text-muted-foreground">{team1.short_name} (AET)</p>
              <Input
                type="number"
                min={0}
                value={team1GoalsET}
                onChange={(e) => setTeam1GoalsET(parseInt(e.target.value) || 0)}
                className="text-center h-8"
              />
            </div>
            <span className="text-muted-foreground">–</span>
            <div className="flex-1 space-y-1">
              <p className="text-[10px] text-muted-foreground">{team2.short_name} (AET)</p>
              <Input
                type="number"
                min={0}
                value={team2GoalsET}
                onChange={(e) => setTeam2GoalsET(parseInt(e.target.value) || 0)}
                className="text-center h-8"
              />
            </div>
          </div>
        )}

        {/* Penalty Shootout toggle */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="has-pen"
            checked={hasPen}
            onChange={(e) => setHasPen(e.target.checked)}
            className="h-4 w-4 rounded"
          />
          <Label htmlFor="has-pen" className="text-xs cursor-pointer">Penalty Shootout</Label>
        </div>
        {hasPen && (
          <div className="pl-6 flex gap-4">
            {[team1, team2].map((team) => (
              <label key={team.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="shootout-winner"
                  value={team.id}
                  checked={shootoutWinnerId === team.id}
                  onChange={() => setShootoutWinnerId(team.id)}
                  className="h-4 w-4"
                />
                <span className="text-xs font-medium">{team.short_name} wins</span>
              </label>
            ))}
          </div>
        )}

        {/* Player Events — collapsible per team */}
        {[
          { label: team1.short_name, players: team1Players, key: 'team1' as const },
          { label: team2.short_name, players: team2Players, key: 'team2' as const },
        ].map(({ label, players, key }) => (
          <div key={key} className="space-y-2">
            <button
              type="button"
              onClick={() => setExpandedTeam(expandedTeam === key ? null : key)}
              className="flex w-full items-center justify-between text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>{label} Player Events</span>
              {expandedTeam === key ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {expandedTeam === key && renderPlayerTable(players)}
          </div>
        ))}

        {error && (
          <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">{error}</p>
        )}

        <Button onClick={handleSubmit} disabled={isSubmitting} className="w-full" size="sm">
          {isSubmitting ? 'Submitting...' : 'Submit Manual Result'}
        </Button>
      </CardContent>
    </Card>
  );
}
