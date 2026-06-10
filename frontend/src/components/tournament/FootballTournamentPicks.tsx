'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    submitTournamentPicks,
    TournamentPicksResponse,
    TeamPickOption,
    PlayerPickOption,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Trophy, Star, Footprints, Hand, Search } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';

const SF_POINTS = 25;
const AWARD_POINTS = 50;

type Award = 'ball' | 'boot' | 'glove';

const AWARD_META: Record<Award, { title: string; hint: string; icon: typeof Star }> = {
    boot: { title: 'Golden Boot', hint: 'Top scorer', icon: Footprints },
    ball: { title: 'Golden Ball', hint: 'Best player', icon: Star },
    glove: { title: 'Golden Glove', hint: 'Best goalkeeper', icon: Hand },
};

function formatCountdown(ms: number): string {
    if (ms <= 0) return 'closed';
    const totalSec = Math.floor(ms / 1000);
    const days = Math.floor(totalSec / 86400);
    const hours = Math.floor((totalSec % 86400) / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    const secs = totalSec % 60;
    return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export default function FootballTournamentPicks({
    picks,
    teams,
    players,
    tournamentId,
}: {
    picks: TournamentPicksResponse;
    teams: TeamPickOption[];
    players: PlayerPickOption[];
    tournamentId: number;
}) {
    const router = useRouter();

    const [selectedSemis, setSelectedSemis] = useState<number[]>(
        picks.top4_team_ids.filter((id): id is number => id !== null),
    );
    const [ball, setBall] = useState<number | null>(picks.golden_ball_player_id);
    const [boot, setBoot] = useState<number | null>(picks.golden_boot_player_id);
    const [glove, setGlove] = useState<number | null>(picks.golden_glove_player_id);
    const [playerSearch, setPlayerSearch] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [now, setNow] = useState(Date.now());

    useEffect(() => {
        const t = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(t);
    }, []);

    const lockMs = picks.locks_at ? new Date(picks.locks_at).getTime() - now : null;
    const isOpen = picks.is_open && (lockMs === null || lockMs > 0);

    const playerById = useMemo(
        () => new Map(players.map(p => [p.id, p])),
        [players],
    );

    const filtered = players.filter(p =>
        playerSearch === '' ||
        p.name.toLowerCase().includes(playerSearch.toLowerCase()) ||
        (p.team_name ?? '').toLowerCase().includes(playerSearch.toLowerCase()),
    );
    const keepers = filtered.filter(p => p.role === 'Goalkeeper');

    const toggleSemi = (teamId: number) => {
        setSelectedSemis(prev => {
            if (prev.includes(teamId)) return prev.filter(id => id !== teamId);
            if (prev.length >= 4) return prev;
            return [...prev, teamId];
        });
    };

    const awardValue: Record<Award, number | null> = { ball, boot, glove };
    const awardSetter: Record<Award, (v: number | null) => void> = {
        ball: setBall, boot: setBoot, glove: setGlove,
    };

    const handleSubmit = async () => {
        setError('');
        setIsSubmitting(true);
        try {
            await submitTournamentPicks(tournamentId, {
                top4_team_ids: selectedSemis,
                golden_ball_player_id: ball,
                golden_boot_player_id: boot,
                golden_glove_player_id: glove,
            });
            router.push(`/tournaments/${tournamentId}`);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : 'Failed to save picks');
        } finally {
            setIsSubmitting(false);
        }
    };

    const hasAny = selectedSemis.length > 0 || ball || boot || glove;

    const renderPlayerList = (award: Award, pool: PlayerPickOption[]) => {
        const selected = awardValue[award];
        const set = awardSetter[award];
        const meta = AWARD_META[award];
        const Icon = meta.icon;
        return (
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Icon className="w-4 h-4" />
                        {meta.title}
                        <span className="text-xs font-normal text-muted-foreground">· {meta.hint}</span>
                        {selected && (
                            <Badge variant="secondary" className="ml-auto text-xs">
                                {playerById.get(selected)?.name ?? '—'}
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-1 max-h-64 overflow-y-auto">
                        {pool.length === 0 && (
                            <p className="text-sm text-muted-foreground text-center py-4">No players found</p>
                        )}
                        {pool.map(player => {
                            const isSelected = selected === player.id;
                            return (
                                <button
                                    key={player.id}
                                    disabled={!isOpen}
                                    onClick={() => set(isSelected ? null : player.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors text-left',
                                        isSelected ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted',
                                        !isOpen && 'cursor-default',
                                    )}
                                >
                                    <div>
                                        <span>{player.name}</span>
                                        <span className="text-xs text-muted-foreground ml-2">{player.team_name}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground">{player.role}</span>
                                        {isSelected && <Check className="w-3 h-3 text-primary" />}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>
        );
    };

    return (
        <div className="container-mobile py-6 space-y-6 pb-48">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold">{picks.tournament_name}</h1>
                <p className="text-muted-foreground text-sm mt-1">Tournament picks — up to 250 pts</p>
            </div>

            {/* Window status */}
            <div
                className={cn(
                    'rounded-lg px-4 py-2 text-sm font-medium inline-flex items-center gap-2',
                    isOpen ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800',
                )}
            >
                {isOpen ? (
                    <>
                        Picks Open
                        {lockMs !== null && (
                            <span className="font-normal">· locks in {formatCountdown(lockMs)}</span>
                        )}
                    </>
                ) : (
                    'Picks Locked — knockouts have begun'
                )}
            </div>
            {isOpen && (
                <p className="text-xs text-muted-foreground -mt-3">
                    Edit freely until the first knockout match kicks off.
                </p>
            )}

            {/* Current picks summary */}
            {hasAny && (
                <Card>
                    <CardContent className="pt-4 space-y-3">
                        <div>
                            <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Semi-Finalists</p>
                            <div className="flex flex-wrap gap-2">
                                {selectedSemis.map(teamId => {
                                    const team = teams.find(t => t.id === teamId);
                                    const logoSrc = team ? getTeamLogoUrl(team.short_name) : null;
                                    return team ? (
                                        <div key={teamId} className="flex items-center gap-1.5 bg-primary/10 text-primary rounded-full px-3 py-1 text-xs font-medium">
                                            {logoSrc && (
                                                // eslint-disable-next-line @next/next/no-img-element
                                                <img src={logoSrc} alt={team.short_name} width={14} height={14}
                                                    className="h-3.5 w-3.5 object-contain"
                                                    onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                            )}
                                            {team.short_name}
                                        </div>
                                    ) : null;
                                })}
                                {Array.from({ length: 4 - selectedSemis.length }).map((_, i) => (
                                    <div key={`empty-${i}`} className="border border-dashed border-border rounded-full px-3 py-1 text-xs text-muted-foreground">—</div>
                                ))}
                            </div>
                        </div>
                        <div className="flex gap-3 pt-1 border-t border-border">
                            {(['boot', 'ball', 'glove'] as Award[]).map(a => (
                                <div key={a} className="flex-1">
                                    <p className="text-xs text-muted-foreground mb-0.5">{AWARD_META[a].title}</p>
                                    <p className={cn('text-sm font-medium', awardValue[a] ? 'text-foreground' : 'text-muted-foreground/50')}>
                                        {awardValue[a] ? (playerById.get(awardValue[a]!)?.name ?? '—') : '—'}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Points breakdown */}
            {isOpen && (
                <Card>
                    <CardContent className="pt-4 text-sm text-muted-foreground space-y-1">
                        <div className="flex justify-between">
                            <span>Each correct semi-finalist</span>
                            <span className="font-semibold text-foreground">{SF_POINTS} pts</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Golden Boot / Ball / Glove</span>
                            <span className="font-semibold text-foreground">{AWARD_POINTS} pts each</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Points earned (after finalized) */}
            {picks.is_processed && (
                <Card className="border-green-200 bg-green-50">
                    <CardContent className="pt-4">
                        <div className="text-center">
                            <Trophy className="w-8 h-8 text-green-600 mx-auto mb-1" />
                            <p className="text-2xl font-bold text-green-700">{picks.points_earned} pts</p>
                            <p className="text-sm text-green-600">Tournament picks points earned</p>
                        </div>
                    </CardContent>
                </Card>
            )}

            {error && <p className="text-red-500 text-sm">{error}</p>}

            {/* Semi-finalists */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Trophy className="w-4 h-4" />
                        Semi-Final Teams
                        <Badge variant="outline" className="ml-auto text-xs">
                            {selectedSemis.length}/4 selected
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-2">
                        {teams.map(team => {
                            const isSelected = selectedSemis.includes(team.id);
                            const canAdd = selectedSemis.length < 4 || isSelected;
                            const disabled = !isOpen || (!canAdd && !isSelected);
                            const logoSrc = getTeamLogoUrl(team.short_name);
                            return (
                                <button
                                    key={team.id}
                                    disabled={disabled}
                                    onClick={() => toggleSemi(team.id)}
                                    className={cn(
                                        'relative flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                                        isSelected
                                            ? 'border-primary bg-primary/10 text-primary font-medium'
                                            : 'border-border bg-background hover:bg-muted',
                                        disabled && 'opacity-50 cursor-not-allowed',
                                    )}
                                >
                                    {logoSrc ? (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img src={logoSrc} alt={team.short_name} width={20} height={20}
                                            className="h-5 w-5 object-contain shrink-0"
                                            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                                    ) : isSelected ? (
                                        <Check className="w-3 h-3 shrink-0" />
                                    ) : null}
                                    <span className="truncate">{team.short_name}</span>
                                    {isSelected && logoSrc && <Check className="w-3 h-3 shrink-0 ml-auto" />}
                                </button>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Player search */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                    type="text"
                    placeholder="Search players..."
                    value={playerSearch}
                    onChange={e => setPlayerSearch(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={!isOpen}
                />
            </div>

            {renderPlayerList('boot', filtered)}
            {renderPlayerList('ball', filtered)}
            {renderPlayerList('glove', keepers)}

            {/* Sticky submit */}
            {isOpen && (
                <div className="fixed bottom-16 left-0 right-0 z-10 bg-background border-t border-border px-4 py-3">
                    <div className="container-mobile">
                        <div className="flex items-center justify-between mb-2 text-xs text-muted-foreground">
                            <span>{selectedSemis.length}/4 semis</span>
                            <span>{boot ? '✓' : '–'} Boot · {ball ? '✓' : '–'} Ball · {glove ? '✓' : '–'} Glove</span>
                        </div>
                        <Button
                            className="w-full"
                            onClick={handleSubmit}
                            disabled={isSubmitting || !hasAny}
                        >
                            {isSubmitting ? 'Saving...' : 'Save Picks'}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
