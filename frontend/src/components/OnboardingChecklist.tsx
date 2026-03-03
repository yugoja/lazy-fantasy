'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Circle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'onboarding-dismissed';

export function OnboardingChecklist({
  hasPredicted,
  hasLeague,
}: {
  hasPredicted: boolean;
  hasLeague: boolean;
}) {
  const [notifGranted, setNotifGranted] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (localStorage.getItem(STORAGE_KEY)) setDismissed(true);
    if (typeof Notification !== 'undefined') {
      setNotifGranted(Notification.permission === 'granted');
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setDismissed(true);
  };

  const handleEnableNotifications = async () => {
    if (typeof Notification === 'undefined') return;
    const perm = await Notification.requestPermission();
    setNotifGranted(perm === 'granted');
  };

  const allDone = hasPredicted && hasLeague && notifGranted;

  if (!mounted || dismissed || allDone) return null;

  const steps = [
    {
      done: hasPredicted,
      label: 'Make your first prediction',
      action: (
        <Link href="/predictions">
          <Button size="sm" variant="outline" className="text-xs h-7 shrink-0">
            Predict →
          </Button>
        </Link>
      ),
    },
    {
      done: hasLeague,
      label: 'Join or create a league',
      action: (
        <Link href="/leagues">
          <Button size="sm" variant="outline" className="text-xs h-7 shrink-0">
            Leagues →
          </Button>
        </Link>
      ),
    },
    {
      done: notifGranted,
      label: 'Enable match reminders',
      action: (
        <Button
          size="sm"
          variant="outline"
          className="text-xs h-7 shrink-0"
          onClick={handleEnableNotifications}
        >
          Enable
        </Button>
      ),
    },
  ];

  const completedCount = steps.filter((s) => s.done).length;

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm font-semibold">Get started</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {completedCount} of {steps.length} done
            </p>
          </div>
          <button
            onClick={handleDismiss}
            className="text-muted-foreground hover:text-foreground p-1"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.label} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                {step.done ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <span
                  className={cn(
                    'text-sm truncate',
                    step.done && 'line-through text-muted-foreground',
                  )}
                >
                  {step.label}
                </span>
              </div>
              {!step.done && step.action}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
