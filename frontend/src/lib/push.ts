import { getVapidPublicKey, subscribePush } from '@/lib/api';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export async function registerPushSubscription(vapidPublicKey: string): Promise<void> {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey).buffer as ArrayBuffer,
  });
  const { endpoint, keys } = subscription.toJSON() as {
    endpoint: string;
    keys: { auth: string; p256dh: string };
  };
  await subscribePush(endpoint, keys.auth, keys.p256dh);
}

/** Whether the browser supports Web Push (Notification + ServiceWorker + PushManager). */
export function isPushSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'Notification' in window &&
    'serviceWorker' in navigator &&
    'PushManager' in window
  );
}

/** Whether the device is running iOS (iPhone, iPad, iPod). */
export function isIOS(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /iPhone|iPad|iPod/.test(navigator.userAgent);
}

/** Whether the app is running as an installed PWA (standalone mode). */
export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && (navigator as { standalone?: boolean }).standalone === true)
  );
}

/**
 * Request notification permission and register the push subscription in one step.
 * Returns true if successfully subscribed, false otherwise.
 */
export async function enablePushNotifications(): Promise<boolean> {
  if (!isPushSupported()) return false;

  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return false;

    const { public_key } = await getVapidPublicKey();
    await registerPushSubscription(public_key);
    return true;
  } catch {
    return false;
  }
}
