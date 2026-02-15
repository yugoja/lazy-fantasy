'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function CreateLeaguePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/leagues');
  }, [router]);

  return null;
}
