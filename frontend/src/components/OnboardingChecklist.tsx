'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { CheckCircle2, Circle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { isPushSupported, enablePushNotifications, isIOS, isStandalone } from '@/lib/push';

const STORAGE_KEY = 'onboarding-dismissed';

export function OnboardingChecklist({
  hasPredicted,
  hasLeague,
}: {
  hasPredicted: boolean;
  hasLeague: boolean;
}) {
  const [notifGranted, setNotifGranted] = useState(false);
  const [pushSupported, setPushSupported] = useState(true);
  const [iosNonStandalone, setIosNonStandalone] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (localStorage.getItem(STORAGE_KEY)) setDismissed(true);
    setPushSupported(isPushSupported());
    setIosNonStandalone(isIOS() && !isStandalone());
    if (typeof Notification !== 'undefined') {
      setNotifGranted(Notification.permission === 'granted');
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setDismissed(true);
  };

  const handleEnableNotifications = async () => {
    const ok = await enablePushNotifications();
    setNotifGranted(ok);
  };

  const allDone =
    hasPredicted && hasLeague && (notifGranted || (!pushSupported && !iosNonStandalone));

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
    ...(pushSupported
      ? [
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
        ]
      : iosNonStandalone
        ? [
            {
              done: false,
              label: 'Install app for reminders',
              action: (
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs h-7 shrink-0"
                  onClick={() => window.dispatchEvent(new Event('show-ios-install'))}
                >
                  How?
                </Button>
              ),
            },
          ]
        : []),
  ];

  const completedCount = steps.filter((s) => s.done).length;

  return (
    <div className="rounded-xl border-l-4 border-l-primary bg-primary/5 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm font-bold">Get started</p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {completedCount}/{steps.length} done
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
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground/50 shrink-0" />
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
    </div>
  );
}
