import { toast } from 'sonner';

interface ShareOptions {
  text: string;
  title?: string;
  image?: Blob;
}

export async function shareWithCard({ text, title, image }: ShareOptions): Promise<void> {
  // Tier 1: Web Share API with image file
  if (navigator.share && image) {
    const file = new File([image], 'lazy-fantasy.png', { type: 'image/png' });

    // Check if sharing files is supported
    if (navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ text, title, files: [file] });
        return;
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        // Fall through to text-only share
      }
    }
  }

  // Tier 2: Web Share API text-only
  if (navigator.share) {
    try {
      await navigator.share({ text, title });
      return;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      // Fall through to clipboard
    }
  }

  // Tier 3: Clipboard copy + toast
  try {
    await navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  } catch {
    toast.error('Could not share');
  }
}
