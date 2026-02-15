import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Map cricket team short_name → ISO 3166 flag code for flagcdn.com */
const FLAG_MAP: Record<string, string> = {
  IND: "in",
  PAK: "pk",
  AUS: "au",
  ENG: "gb-eng",
  SA: "za",
  NZ: "nz",
  SL: "lk",
  AFG: "af",
  NED: "nl",
  NAM: "na",
  USA: "us",
  SCO: "gb-sct",
  NEP: "np",
  ITA: "it",
  IRE: "ie",
  ZIM: "zw",
  OMA: "om",
  UAE: "ae",
  CAN: "ca",
  WI: "wi",    // no real country — fallback handled in component
  BAN: "bd",
}

export function getFlagCode(shortName: string): string | undefined {
  return FLAG_MAP[shortName]
}

/** Get local flag image path for a team short_name or flag code */
export function getFlagUrl(shortNameOrCode: string): string | undefined {
  const code = FLAG_MAP[shortNameOrCode] || shortNameOrCode
  if (!code) return undefined
  return `/flags/${code}.png`
}
