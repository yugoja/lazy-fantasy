'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMe, getMyLeagues, getMyPredictionsDetailed, PredictionDetail, FootballPredictionDetail, updateProfile, uploadAvatar, mediaUrl } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Trophy,
  Target,
  Flame,
  ChevronRight,
  LogOut,
  Bell,
  Shield,
  CircleHelp,
  Users,
  Pencil,
  Check,
  X,
  Camera,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
}

export default function ProfilePage() {
  const { isAuthenticated, isLoading: authLoading, username, displayName, logout, setDisplayName, setAvatarUrl: setAuthAvatarUrl } = useAuth();
  const router = useRouter();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [predictions, setPredictions] = useState<Array<PredictionDetail | FootballPredictionDetail>>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Avatar
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [avatarVersion, setAvatarVersion] = useState(0);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState('');
  const avatarInputRef = useRef<HTMLInputElement>(null);

  // Display name editing
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      const [meData, leaguesData, predictionsData] = await Promise.allSettled([
        getMe(),
        getMyLeagues(),
        getMyPredictionsDetailed(),
      ]);
      if (meData.status === 'fulfilled') {
        setAvatarUrl(meData.value.avatar_url);
        setAuthAvatarUrl(meData.value.avatar_url);
      }
      if (leaguesData.status === 'fulfilled') setLeagues(leaguesData.value);
      if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
    } catch {
      // silently fail - non-critical
    } finally {
      setIsLoading(false);
    }
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError('Image must be under 2MB');
      return;
    }
    setAvatarUploading(true);
    setAvatarError('');
    try {
      const updated = await uploadAvatar(file);
      setAvatarUrl(updated.avatar_url);
      setAuthAvatarUrl(updated.avatar_url);
      setAvatarVersion(v => v + 1);
    } catch {
      setAvatarError('Failed to upload. Try again.');
    } finally {
      setAvatarUploading(false);
      e.target.value = '';
    }
  };

  const startEditing = () => {
    setEditValue(displayName || username || '');
    setSaveError('');
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setSaveError('');
  };

  const saveDisplayName = async () => {
    const trimmed = editValue.trim();
    if (!trimmed) {
      setSaveError('Name cannot be empty');
      return;
    }
    setIsSaving(true);
    setSaveError('');
    try {
      const updated = await updateProfile(trimmed);
      setDisplayName(updated.display_name ?? trimmed);
      setIsEditing(false);
    } catch {
      setSaveError('Failed to save. Try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const processed = predictions.filter(p => p.is_processed);
  const totalPoints = processed.reduce((sum, p) => sum + p.points_earned, 0);
  const processedCricket = processed.filter((p): p is PredictionDetail => p.sport !== 'football');
  const correctWins = processedCricket.filter(p => p.actual_winner && p.predicted_winner.id === p.actual_winner.id).length;
  const accuracy = processedCricket.length > 0 ? Math.round((correctWins / processedCricket.length) * 100) : 0;

  const sortedCricket = [...processedCricket].sort(
    (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
  );
  let streak = 0;
  for (const p of sortedCricket) {
    if (p.actual_winner && p.predicted_winner.id === p.actual_winner.id) {
      streak++;
    } else {
      break;
    }
  }

  const visibleName = displayName || username || '';
  const initials = visibleName ? visibleName.substring(0, 2).toUpperCase() : '??';

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-5">
        <div className="flex flex-col items-center space-y-3">
          <Skeleton className="h-20 w-20 rounded-full" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-5 pb-24">
      {/* Profile Avatar */}
      <div className="flex flex-col items-center">
        <div className="relative">
          <button
            className="relative cursor-pointer group focus:outline-none"
            onClick={() => avatarInputRef.current?.click()}
            aria-label="Change profile picture"
          >
            <Avatar className="h-20 w-20 border-2 border-primary">
              {avatarUrl && (
                <AvatarImage
                  src={`${mediaUrl(avatarUrl)}?v=${avatarVersion}`}
                  alt={visibleName}
                />
              )}
              <AvatarFallback className="bg-primary/15 text-2xl font-bold text-primary">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
              <Camera className="h-5 w-5 text-white" />
            </div>
            {avatarUploading && (
              <div className="absolute inset-0 rounded-full bg-black/60 flex items-center justify-center">
                <Loader2 className="h-5 w-5 text-white animate-spin" />
              </div>
            )}
          </button>
          <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-accent pointer-events-none">
            <Trophy className="h-3.5 w-3.5 text-accent-foreground" />
          </div>
        </div>
        <input
          ref={avatarInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleAvatarChange}
        />
        {avatarError && (
          <p className="mt-1 text-xs text-destructive">{avatarError}</p>
        )}
        <h1 className="mt-3 text-lg font-bold text-foreground">{visibleName}</h1>
        <p className="text-xs text-muted-foreground">@{username}</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Points', value: String(totalPoints), icon: Trophy, color: 'text-primary' },
          { label: 'Accuracy', value: processed.length > 0 ? `${accuracy}%` : '0%', icon: Target, color: 'text-accent' },
          { label: 'Streak', value: String(streak), icon: Flame, color: 'text-orange-400' },
        ].map((stat) => (
          <Card key={stat.label} className="border-border bg-card">
            <CardContent className="flex flex-col items-center gap-1 p-3">
              <stat.icon className={cn('h-4 w-4', stat.color)} />
              <span className="text-lg font-bold text-foreground">{stat.value}</span>
              <span className="text-[10px] text-muted-foreground">{stat.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Display Name */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Profile</h2>
        <Card className="border-border bg-card">
          <CardContent className="flex flex-col gap-4 p-4">
            <div className="flex flex-col gap-1.5">
              <Label className="text-[11px] text-muted-foreground">Display Name</Label>
              {isEditing ? (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2">
                    <Input
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      placeholder="Your name"
                      maxLength={100}
                      className="h-8 text-sm"
                      autoFocus
                      onKeyDown={e => {
                        if (e.key === 'Enter') saveDisplayName();
                        if (e.key === 'Escape') cancelEditing();
                      }}
                    />
                    <Button
                      size="sm"
                      className="h-8 px-2"
                      onClick={saveDisplayName}
                      disabled={isSaving}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 px-2"
                      onClick={cancelEditing}
                      disabled={isSaving}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  {saveError && (
                    <p className="text-xs text-destructive">{saveError}</p>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">
                    {displayName || <span className="text-muted-foreground italic">Not set</span>}
                  </p>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 text-muted-foreground"
                    onClick={startEditing}
                  >
                    <Pencil className="h-3.5 w-3.5 mr-1" />
                    Edit
                  </Button>
                </div>
              )}
              <p className="text-[11px] text-muted-foreground">
                This is how your name appears on the leaderboard and across the app.
              </p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-[11px] text-muted-foreground">Username</Label>
              <p className="text-sm font-medium text-foreground">@{username}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* My Leagues */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">My Leagues</h2>
          <Badge variant="secondary" className="text-[10px]">
            {leagues.length}
          </Badge>
        </div>
        <Card className="border-border bg-card">
          {leagues.length === 0 ? (
            <CardContent className="p-4 text-center">
              <p className="text-sm text-muted-foreground">No leagues joined yet</p>
              <Link href="/leagues" className="mt-2 inline-block">
                <Button variant="outline" size="sm" className="text-xs mt-2">
                  Browse Leagues
                </Button>
              </Link>
            </CardContent>
          ) : (
            <CardContent className="divide-y divide-border p-0">
              {leagues.map((league) => (
                <Link
                  key={league.id}
                  href={`/leaderboard?league=${league.id}`}
                  className="flex items-center justify-between px-4 py-3 active:bg-secondary/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Users className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <p className="text-sm font-medium text-foreground">{league.name}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              ))}
            </CardContent>
          )}
        </Card>
      </div>

      {/* Settings Menu */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Settings</h2>
        <Card className="border-border bg-card">
          <CardContent className="divide-y divide-border p-0">
            {[
              { icon: Bell, label: 'Notifications', desc: 'Match reminders & results' },
              { icon: Shield, label: 'Privacy', desc: 'Profile visibility & data' },
              { icon: CircleHelp, label: 'Help & Support', desc: 'FAQs and contact us' },
            ].map((item) => (
              <button
                key={item.label}
                className="flex w-full items-center justify-between px-4 py-3 active:bg-secondary/50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary">
                    <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-foreground">{item.label}</p>
                    <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Sign Out */}
      <Button
        variant="outline"
        className="w-full border-destructive/30 bg-destructive/5 text-destructive active:bg-destructive/10"
        onClick={logout}
      >
        <LogOut className="mr-2 h-4 w-4" />
        Sign Out
      </Button>
    </div>
  );
}
