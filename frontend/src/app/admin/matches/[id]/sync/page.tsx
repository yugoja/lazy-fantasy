'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { API_BASE } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Link2, Link2Off, RefreshCw, CheckCircle2, AlertCircle,
  ChevronLeft, Users, Zap,
} from 'lucide-react';

interface SyncStatus {
  match_id: number;
  external_match_id: string | null;
  sync_state: string;
  last_synced_at: string | null;
  sync_error: string | null;
  cricapi_preview: {
    name: string;
    status: string;
    lineup_announced: boolean;
    team1_players: number;
    team2_players: number;
  } | null;
}

interface PlayerMappingEntry {
  provider_id: string;
  provider_name: string;
  resolved: boolean;
  player_id: number | null;
  player_name: string | null;
  suggestions: { id: number; name: string }[];
}

const SYNC_STATE_LABELS: Record<string, { label: string; className: string }> = {
  unlinked:      { label: 'Unlinked',      className: 'bg-muted text-muted-foreground' },
  linked:        { label: 'Linked',        className: 'bg-yellow-500/20 text-yellow-400' },
  lineup_synced: { label: 'Lineup Synced', className: 'bg-blue-500/20 text-blue-400' },
  result_synced: { label: 'Result Synced', className: 'bg-green-500/20 text-green-400' },
};

export default function MatchSyncPage() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [playerMapping, setPlayerMapping] = useState<PlayerMappingEntry[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);
  const [linkInput, setLinkInput] = useState('');
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  // player_id overrides for unresolved players: provider_id → selected player_id
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const loadSyncStatus = useCallback(async () => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE}/admin/matches/${id}/sync-status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to load sync status');
    const data: SyncStatus = await res.json();
    setSyncStatus(data);
    return data;
  }, [id]);

  const loadPlayerMapping = useCallback(async () => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE}/admin/matches/${id}/player-mapping`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return; // Not linked yet — OK
    const data = await res.json();
    setPlayerMapping(data.players ?? null);
  }, [id]);

  useEffect(() => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    Promise.all([loadSyncStatus(), loadPlayerMapping()])
      .catch(() => setError('Failed to load match sync data'))
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, loadSyncStatus, loadPlayerMapping]);

  const handleLink = async () => {
    if (!linkInput.trim()) return;
    setIsLinking(true);
    setError('');
    setSuccess('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/admin/matches/${id}/link`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ external_match_id: linkInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Link failed');
      }
      setSuccess('Match linked successfully');
      setLinkInput('');
      const newStatus = await loadSyncStatus();
      if (newStatus.external_match_id) await loadPlayerMapping();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Link failed');
    } finally {
      setIsLinking(false);
    }
  };

  const handleUnlink = async () => {
    if (!confirm('Unlink this match from CricAPI? Sync state will be reset.')) return;
    setIsUnlinking(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/admin/matches/${id}/link`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Unlink failed');
      setSyncStatus(s => s ? { ...s, external_match_id: null, sync_state: 'unlinked', sync_error: null } : s);
      setPlayerMapping(null);
      setSuccess('Match unlinked');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unlink failed');
    } finally {
      setIsUnlinking(false);
    }
  };

  const handleForceSync = async () => {
    setIsSyncing(true);
    setError('');
    setSuccess('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/admin/matches/${id}/sync`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Sync failed');
      }
      const result = await res.json();
      setSuccess(`Sync complete — action: ${result.action}`);
      await loadSyncStatus();
      await loadPlayerMapping();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sync failed');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSaveMapping = async () => {
    const mappings = Object.entries(overrides)
      .filter(([, val]) => val !== '')
      .map(([provider_id, player_id]) => ({ provider_id, player_id: Number(player_id) }));
    if (mappings.length === 0) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/admin/matches/${id}/player-mapping`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mappings }),
      });
      if (!res.ok) throw new Error('Save mapping failed');
      setOverrides({});
      setSuccess(`Saved ${mappings.length} player mapping(s)`);
      await loadPlayerMapping();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  const stateInfo = SYNC_STATE_LABELS[syncStatus?.sync_state ?? 'unlinked'];
  const unresolvedCount = playerMapping?.filter(p => !p.resolved).length ?? 0;

  return (
    <div className="container-mobile py-6 space-y-5">
      {/* Header */}
      <div>
        <Link href="/admin" className="inline-flex items-center gap-1 text-xs text-muted-foreground mb-3">
          <ChevronLeft className="h-3 w-3" /> Admin
        </Link>
        <h1 className="text-xl font-bold">CricAPI Sync</h1>
        <p className="text-sm text-muted-foreground">Match #{id}</p>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="p-3 flex gap-2 items-start">
            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}
      {success && (
        <Card className="border-green-500/30 bg-green-500/10">
          <CardContent className="p-3 flex gap-2 items-center">
            <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
            <p className="text-sm text-green-400">{success}</p>
          </CardContent>
        </Card>
      )}

      {/* Current Status */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Sync Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">State</span>
            <Badge className={`text-[10px] ${stateInfo.className}`}>{stateInfo.label}</Badge>
          </div>
          {syncStatus?.external_match_id && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">CricAPI ID</span>
              <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                {syncStatus.external_match_id}
              </code>
            </div>
          )}
          {syncStatus?.last_synced_at && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Last synced</span>
              <span className="text-xs">
                {new Date(syncStatus.last_synced_at).toLocaleString()}
              </span>
            </div>
          )}
          {syncStatus?.sync_error && (
            <div className="rounded bg-destructive/10 px-2 py-1.5">
              <p className="text-[10px] text-destructive font-mono">{syncStatus.sync_error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* CricAPI Preview */}
      {syncStatus?.cricapi_preview && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">CricAPI Preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-medium">{syncStatus.cricapi_preview.name}</p>
            <p className="text-xs text-muted-foreground">{syncStatus.cricapi_preview.status}</p>
            <div className="flex gap-3 text-xs">
              <span className={syncStatus.cricapi_preview.lineup_announced ? 'text-green-400' : 'text-muted-foreground'}>
                {syncStatus.cricapi_preview.lineup_announced ? '✓ Lineup announced' : '○ Lineup pending'}
              </span>
              <span className="text-muted-foreground">
                {syncStatus.cricapi_preview.team1_players + syncStatus.cricapi_preview.team2_players} players
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Link / Unlink */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Link2 className="h-4 w-4" /> Link to CricAPI
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!syncStatus?.external_match_id ? (
            <>
              <p className="text-xs text-muted-foreground">
                Enter the CricAPI match ID (e.g. from <code>/series/{'{'}series_id{'}'}/matches</code>).
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g. abc123-def456"
                  value={linkInput}
                  onChange={e => setLinkInput(e.target.value)}
                  className="text-xs h-8 font-mono"
                  onKeyDown={e => e.key === 'Enter' && handleLink()}
                />
                <Button size="sm" onClick={handleLink} disabled={isLinking || !linkInput.trim()}>
                  {isLinking ? <RefreshCw className="h-3 w-3 animate-spin" /> : 'Link'}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                className="flex-1 text-xs gap-1"
                onClick={handleForceSync}
                disabled={isSyncing}
              >
                {isSyncing
                  ? <RefreshCw className="h-3 w-3 animate-spin" />
                  : <Zap className="h-3 w-3" />
                }
                Force Sync
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="text-xs gap-1"
                onClick={handleUnlink}
                disabled={isUnlinking}
              >
                <Link2Off className="h-3 w-3" /> Unlink
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Player Mapping */}
      {playerMapping && playerMapping.length > 0 && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Users className="h-4 w-4" /> Player Mapping
              {unresolvedCount > 0 && (
                <Badge variant="destructive" className="text-[10px] ml-auto">
                  {unresolvedCount} unresolved
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {playerMapping.map(p => (
              <div key={p.provider_id} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{p.provider_name}</p>
                  {p.resolved && p.player_name && (
                    <p className="text-[10px] text-green-400">→ {p.player_name}</p>
                  )}
                </div>
                {!p.resolved && (
                  <select
                    className="text-[10px] bg-background border border-border rounded px-1.5 py-1 ml-2 max-w-[140px]"
                    value={overrides[p.provider_id] ?? ''}
                    onChange={e => setOverrides(prev => ({ ...prev, [p.provider_id]: e.target.value }))}
                  >
                    <option value="">— select player —</option>
                    {p.suggestions.map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                )}
                {p.resolved && <CheckCircle2 className="h-3.5 w-3.5 text-green-400 shrink-0 ml-2" />}
              </div>
            ))}
            {Object.values(overrides).some(v => v !== '') && (
              <Button size="sm" className="w-full text-xs mt-2" onClick={handleSaveMapping}>
                Save Mappings
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
