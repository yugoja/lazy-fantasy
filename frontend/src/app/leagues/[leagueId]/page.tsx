'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import NextImage from 'next/image';
import { useAuth } from '@/lib/auth';
import { getLeaderboard, getMyLeagues, uploadLeagueImage, LeaderboardEntry, mediaUrl } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Trophy, TrendingUp, TrendingDown, Minus, ArrowLeft, Share2, Settings, Camera, Loader2, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { shareWithCard } from '@/lib/share';

type RoundKey = 'ALL' | string;

const ROUND_LABELS: Record<string, string> = {
  GROUP_1: 'Matchday 1',
  GROUP_2: 'Matchday 2',
  GROUP_3: 'Matchday 3',
  R32: 'Round of 32',
  R16: 'Round of 16',
  QF: 'Quarter-finals',
  SF: 'Semi-finals',
  THIRD: '3rd Place',
  FINAL: 'Final',
};

function entryLabel(entry: LeaderboardEntry) {
  return entry.display_name || entry.username;
}

export default function LeagueLeaderboardPage() {
  const { isAuthenticated, username, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const leagueId = Number(params.leagueId);

  const [leagueName, setLeagueName] = useState('');
  const [leagueImageUrl, setLeagueImageUrl] = useState<string | null>(null);
  const [leagueImageVersion, setLeagueImageVersion] = useState(0);
  const [leagueOwnerId, setLeagueOwnerId] = useState<number | null>(null);
  const [inviteCode, setInviteCode] = useState('');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [availableRounds, setAvailableRounds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRound, setSelectedRound] = useState<RoundKey>('ALL');

  // Settings dialog
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [imageError, setImageError] = useState('');
  const [codeCopied, setCodeCopied] = useState(false);
  const imageInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated && leagueId) {
      loadBoard('ALL');
    }
  }, [isAuthenticated, leagueId]);

  // Revoke preview object URL on cleanup
  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  const loadBoard = async (round: RoundKey) => {
    setIsLoading(true);
    try {
      const roundParam = round === 'ALL' ? undefined : round;
      const [data, leagues] = await Promise.all([
        getLeaderboard(leagueId, roundParam),
        getMyLeagues(),
      ]);
      setLeagueName(data.league_name);
      setEntries(data.entries);
      setAvailableRounds(data.available_rounds ?? []);
      const league = leagues.find((l) => l.id === leagueId);
      if (league) {
        setInviteCode(league.invite_code);
        setLeagueImageUrl(league.image_url);
        setLeagueOwnerId(league.owner_id);
      }
    } catch {
      // empty state
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoundChange = (round: RoundKey) => {
    setSelectedRound(round);
    loadBoard(round);
  };

  const handleShare = async () => {
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
    const joinUrl = `${appUrl}/join/${inviteCode}`;
    const text = `Join my Lazy Fantasy league "${leagueName}"!\n\nTap to join: ${joinUrl}`;
    await shareWithCard({ text, title: 'Lazy Fantasy — Join League' });
  };

  const handleImageFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setImageError('Image must be under 2MB');
      return;
    }
    setImageError('');
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    e.target.value = '';
  };

  const handleImageUpload = async () => {
    if (!imageFile) return;
    setImageUploading(true);
    setImageError('');
    try {
      const updated = await uploadLeagueImage(leagueId, imageFile);
      setLeagueImageUrl(updated.image_url);
      setLeagueImageVersion(v => v + 1);
      setImageFile(null);
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
        setImagePreview(null);
      }
    } catch {
      setImageError('Failed to upload. Try again.');
    } finally {
      setImageUploading(false);
    }
  };

  const handleCopyCode = async () => {
    if (!inviteCode) return;
    await navigator.clipboard.writeText(inviteCode).catch(() => {});
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 2000);
  };

  const currentUserEntry = entries.find(e => e.username === username);
  const isOwner = leagueOwnerId !== null && currentUserEntry?.is_owner === true;
  const isRoundActive = selectedRound !== 'ALL';
  const ptsLabel = isRoundActive ? 'rnd pts' : 'pts';

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-32 w-full" />
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const topThree = entries.slice(0, 3);
  const [first, second, third] = [topThree[0], topThree[1], topThree[2]];

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <Link href="/leagues">
          <Button variant="ghost" size="sm" className="mb-3 -ml-2 text-muted-foreground">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Leagues
          </Button>
        </Link>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            {leagueImageUrl && (
              <NextImage
                src={`${mediaUrl(leagueImageUrl)}?v=${leagueImageVersion}`}
                alt={leagueName}
                width={40}
                height={40}
                className="rounded-lg object-cover shrink-0"
                unoptimized
              />
            )}
            <h1 className="text-2xl font-bold truncate">{leagueName || 'Leaderboard'}</h1>
          </div>
          <div className="flex gap-2 shrink-0">
            {isOwner && (
              <Button variant="ghost" size="sm" onClick={() => setSettingsOpen(true)}>
                <Settings className="h-4 w-4" />
              </Button>
            )}
            {inviteCode && (
              <Button variant="outline" size="sm" onClick={handleShare} className="gap-2">
                <Share2 className="h-4 w-4" />
                Invite
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* League Settings Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>League Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            {/* League image */}
            <div className="space-y-2">
              <p className="text-sm font-medium">League Image</p>
              <div className="flex items-center gap-4">
                <div
                  className="relative h-20 w-20 rounded-lg overflow-hidden bg-secondary cursor-pointer border border-border group flex-shrink-0"
                  onClick={() => imageInputRef.current?.click()}
                >
                  {imagePreview || leagueImageUrl ? (
                    <NextImage
                      src={imagePreview || `${mediaUrl(leagueImageUrl)}?v=${leagueImageVersion}`}
                      alt="League"
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center">
                      <Camera className="h-6 w-6 text-muted-foreground" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    <Camera className="h-5 w-5 text-white" />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  JPEG, PNG or WebP · Max 2MB · Best size: 512×512
                </div>
              </div>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleImageFileChange}
              />
              {imageError && <p className="text-xs text-destructive">{imageError}</p>}
              {imageFile && (
                <Button
                  size="sm"
                  onClick={handleImageUpload}
                  disabled={imageUploading}
                  className="w-full"
                >
                  {imageUploading ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Uploading…</>
                  ) : (
                    'Save Image'
                  )}
                </Button>
              )}
            </div>

            {/* Invite code */}
            {inviteCode && (
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Invite Code</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-md border border-border bg-secondary px-3 py-2 text-sm font-mono tracking-widest">
                    {inviteCode}
                  </div>
                  <Button variant="outline" size="sm" className="shrink-0" onClick={handleCopyCode}>
                    {codeCopied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Round selector */}
      {availableRounds.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground shrink-0">Round:</span>
          <Select value={selectedRound} onValueChange={handleRoundChange}>
            <SelectTrigger className="w-44 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All rounds</SelectItem>
              {availableRounds.map((key) => (
                <SelectItem key={key} value={key}>
                  {ROUND_LABELS[key] ?? key}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {entries.length === 0 ? (
        <Card className="p-8 text-center space-y-3">
          <Trophy className="h-10 w-10 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">No entries yet. Start predicting!</p>
        </Card>
      ) : (
        <>
          {/* Current User Status */}
          {currentUserEntry && (
            <Card className="p-4 bg-primary/5 border-primary/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-primary">#{currentUserEntry.rank}</div>
                  <div>
                    <div className="font-semibold">You</div>
                    <div className="text-xs text-muted-foreground">{currentUserEntry.total_points} {ptsLabel}</div>
                  </div>
                </div>
                <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
                  Top {Math.max(1, Math.round((currentUserEntry.rank / entries.length) * 100))}%
                </Badge>
              </div>
            </Card>
          )}

          {/* Top 3 Podium — hidden when a round filter is active */}
          {!isRoundActive && topThree.length >= 3 && first.rank === 1 && second.rank === 2 && third.rank === 3 && entries.filter(e => e.rank <= 3).length === 3 && (
            <div className="grid grid-cols-3 gap-2 items-end mb-6">
              {/* 2nd Place */}
              <Card className="p-3 text-center bg-gradient-to-b from-slate-700/10 to-transparent">
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🥈</div>
                  <Avatar className="h-12 w-12 mb-2 border-2 border-slate-400">
                    {second.avatar_url && <AvatarImage src={mediaUrl(second.avatar_url)!} alt={entryLabel(second)} />}
                    <AvatarFallback className="bg-slate-500 text-white font-bold">
                      {entryLabel(second).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{entryLabel(second)}</div>
                  <div className="text-sm font-bold text-primary mt-1">{second.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>

              {/* 1st Place */}
              <Card className="p-4 text-center bg-gradient-to-b from-amber-500/10 to-transparent border-amber-500/30">
                <div className="flex flex-col items-center">
                  <Trophy className="h-8 w-8 text-amber-500 mb-2" />
                  <Avatar className="h-16 w-16 mb-2 border-2 border-amber-500">
                    {first.avatar_url && <AvatarImage src={mediaUrl(first.avatar_url)!} alt={entryLabel(first)} />}
                    <AvatarFallback className="bg-amber-600 text-white font-bold text-lg">
                      {entryLabel(first).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-sm truncate w-full">{entryLabel(first)}</div>
                  <div className="text-lg font-bold text-primary mt-1">{first.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>

              {/* 3rd Place */}
              <Card className="p-3 text-center bg-gradient-to-b from-orange-700/10 to-transparent">
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🥉</div>
                  <Avatar className="h-12 w-12 mb-2 border-2 border-orange-600">
                    {third.avatar_url && <AvatarImage src={mediaUrl(third.avatar_url)!} alt={entryLabel(third)} />}
                    <AvatarFallback className="bg-orange-700 text-white font-bold">
                      {entryLabel(third).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{entryLabel(third)}</div>
                  <div className="text-sm font-bold text-primary mt-1">{third.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>
            </div>
          )}

          {/* Full Table */}
          <Card className="overflow-hidden">
            <div className="divide-y divide-border">
              {entries.map((entry) => {
                const isCurrentUser = entry.username === username;
                const delta = isRoundActive ? null : (entry.rank_delta ?? null);
                return (
                  <div
                    key={entry.user_id}
                    className={cn(
                      'p-4 flex items-center gap-4',
                      isCurrentUser && 'bg-primary/5'
                    )}
                  >
                    <div className={cn(
                      'text-lg font-bold w-8 text-center',
                      entry.rank <= 3 ? 'text-primary' : 'text-muted-foreground'
                    )}>
                      {entry.rank}
                    </div>

                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Avatar className="h-10 w-10">
                        {entry.avatar_url && <AvatarImage src={mediaUrl(entry.avatar_url)!} alt={entryLabel(entry)} />}
                        <AvatarFallback className="bg-primary/10 text-primary font-bold text-sm">
                          {entryLabel(entry).substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm truncate">{entryLabel(entry)}</div>
                        <div className="text-xs text-muted-foreground">@{entry.username}</div>
                        <div className="flex gap-1 mt-0.5 flex-wrap">
                          {isCurrentUser && (
                            <Badge variant="outline" className="text-[10px]">You</Badge>
                          )}
                          {entry.is_owner && (
                            <Badge variant="outline" className="text-[10px] border-amber-500/40 text-amber-500">Admin</Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {delta !== null && delta !== 0 && (
                        <div className={cn(
                          'flex items-center gap-0.5 text-[10px] font-medium',
                          delta > 0 ? 'text-green-500' : 'text-red-500'
                        )}>
                          {delta > 0
                            ? <TrendingUp className="h-3 w-3" />
                            : <TrendingDown className="h-3 w-3" />}
                          {Math.abs(delta)}
                        </div>
                      )}
                      {delta === 0 && (
                        <Minus className="h-3 w-3 text-muted-foreground/50" />
                      )}
                      <div className="text-right">
                        <div className="font-bold text-sm">{entry.total_points}</div>
                        <div className="text-[10px] text-muted-foreground">{ptsLabel}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
