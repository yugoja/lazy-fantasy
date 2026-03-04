'use client';

import { useState, type ReactNode } from 'react';
import { Share2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ShareButtonProps {
  onClick: () => Promise<void>;
  children: ReactNode;
  className?: string;
}

export function ShareButton({ onClick, children, className }: ShareButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await onClick();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={cn(
        'flex items-center justify-center gap-2 w-full py-2.5 rounded-lg',
        'border border-primary/30 bg-primary/5 text-primary text-sm font-medium',
        'disabled:opacity-50 transition-colors',
        className,
      )}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Share2 className="h-4 w-4" />
      )}
      {children}
    </button>
  );
}
