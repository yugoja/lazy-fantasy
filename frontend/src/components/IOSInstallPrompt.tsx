'use client';

import { useEffect, useState } from 'react';
import { isIOS, isStandalone } from '@/lib/push';

const DISMISSED_KEY = 'ios-install-dismissed';

export default function IOSInstallPrompt() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!isIOS() || isStandalone()) return;

    const show = () => setVisible(true);
    const showIfNotDismissed = () => {
      if (!localStorage.getItem(DISMISSED_KEY)) setVisible(true);
    };

    // Show after first prediction (like Android prompt), respects dismiss
    window.addEventListener('prediction-submitted', showIfNotDismissed);
    // Show on demand from onboarding checklist (always opens)
    window.addEventListener('show-ios-install', show);

    return () => {
      window.removeEventListener('prediction-submitted', showIfNotDismissed);
      window.removeEventListener('show-ios-install', show);
    };
  }, []);

  function handleDismiss() {
    localStorage.setItem(DISMISSED_KEY, '1');
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 animate-in slide-in-from-bottom-4 duration-300">
      <div className="bg-card border border-border rounded-2xl p-4 shadow-xl">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
              <polyline points="16 6 12 2 8 6" />
              <line x1="12" y1="2" x2="12" y2="15" />
            </svg>
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground leading-tight">
              Install for match reminders
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Add to Home Screen to get push notifications:
            </p>

            <ol className="text-xs text-muted-foreground mt-2 space-y-1.5">
              <li className="flex items-center gap-1.5">
                <span className="font-semibold text-foreground">1.</span>
                Tap the share button
                <svg className="inline-block shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                  <polyline points="16 6 12 2 8 6" />
                  <line x1="12" y1="2" x2="12" y2="15" />
                </svg>
              </li>
              <li>
                <span className="font-semibold text-foreground">2.</span>
                {' '}Tap <span className="font-medium text-foreground">&quot;Add to Home Screen&quot;</span>
              </li>
              <li>
                <span className="font-semibold text-foreground">3.</span>
                {' '}Tap <span className="font-medium text-foreground">&quot;Add&quot;</span>
              </li>
            </ol>
          </div>
        </div>

        <div className="flex justify-end mt-3">
          <button
            onClick={handleDismiss}
            className="text-xs text-muted-foreground px-2 py-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
