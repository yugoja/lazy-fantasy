'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { getVapidPublicKey, subscribePush } from '@/lib/api';

const PROMPTED_KEY = 'push-permission-prompted';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

async function registerPushSubscription(vapidPublicKey: string): Promise<void> {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });
  const { endpoint, keys } = subscription.toJSON() as {
    endpoint: string;
    keys: { auth: string; p256dh: string };
  };
  await subscribePush(endpoint, keys.auth, keys.p256dh);
}

export default function NotificationPermission() {
  const { isAuthenticated } = useAuth();
  const [visible, setVisible] = useState(false);
  const [vapidKey, setVapidKey] = useState<string | null>(null);

  useEffect(() => {
    if (
      !isAuthenticated ||
      !('Notification' in window) ||
      !('serviceWorker' in navigator) ||
      !('PushManager' in window) ||
      Notification.permission !== 'default' ||
      localStorage.getItem(PROMPTED_KEY)
    ) return;

    // Fetch VAPID public key — if not configured, skip silently
    getVapidPublicKey()
      .then((data) => {
        setVapidKey(data.public_key);
        // Show after a short delay so it doesn't hit users immediately on load
        setTimeout(() => setVisible(true), 4000);
      })
      .catch(() => {/* push not configured — stay hidden */});
  }, [isAuthenticated]);

  async function handleEnable() {
    localStorage.setItem(PROMPTED_KEY, '1');
    setVisible(false);
    if (!vapidKey) return;
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        await registerPushSubscription(vapidKey);
      }

    } catch (e) {
      console.error('Push subscription failed:', e);
    }
  }

  function handleDismiss() {
    localStorage.setItem(PROMPTED_KEY, '1');
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 animate-in slide-in-from-bottom-4 duration-300">
      <div className="bg-card border border-border rounded-2xl p-4 shadow-xl flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 text-xl">
          🔔
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground leading-tight">Match reminders</p>
          <p className="text-xs text-muted-foreground mt-0.5">Get notified 1 hour before predictions lock</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleDismiss}
            className="text-xs text-muted-foreground px-2 py-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            Not now
          </button>
          <button
            onClick={handleEnable}
            className="text-xs font-semibold bg-primary text-primary-foreground px-3 py-1.5 rounded-lg"
          >
            Enable
          </button>
        </div>
      </div>
    </div>
  );
}
