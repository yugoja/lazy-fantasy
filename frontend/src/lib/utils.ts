import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Map team short_name → ISO 3166 flag code for flagcdn.com (cricket + WC 2026 football) */
const FLAG_MAP: Record<string, string> = {
  // Cricket
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
  WI: "wi",
  BAN: "bd",
  // WC 2026 Football
  MEX: "mx", RSA: "za", BRA: "br", ARG: "ar", FRA: "fr", GER: "de",
  ESP: "es", POR: "pt", BEL: "be", URU: "uy", COL: "co", CHL: "cl",
  ECU: "ec", MAR: "ma", SEN: "sn", NGA: "ng", CMR: "cm", GHA: "gh",
  CIV: "ci", EGY: "eg", TUN: "tn", ALG: "dz", JPN: "jp", KOR: "kr",
  IRN: "ir", SAU: "sa", QAT: "qa", SUI: "ch", CRO: "hr", DEN: "dk",
  SRB: "rs", POL: "pl", WAL: "gb-wls", UKR: "ua", SVN: "si", SVK: "sk",
  ALB: "al", CZE: "cz", TUR: "tr", GRE: "gr", HAI: "ht", PAR: "py",
  PAN: "pa", COS: "cr", HON: "hn", JAM: "jm", SLV: "sv", BOL: "bo",
  PER: "pe", VEN: "ve", NZL: "nz", FIJ: "fj", PNG: "pg", TAH: "pf",
  IRQ: "iq", BIH: "ba", ROU: "ro", HUN: "hu", ISL: "is", NOR: "no",
  BFA: "bf", GUI: "gn", MLI: "ml", TAN: "tz",
  // Additional qualifiers in DB
  AUT: "at", COD: "cd", CPV: "cv", CUW: "cw",
  JOR: "jo", KSA: "sa", SWE: "se", UZB: "uz",
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

/** Map IPL team short_name → local logo path */
const TEAM_LOGO_MAP: Record<string, string> = {
  CSK:  '/teams/csk.svg',
  DC:   '/teams/dc.svg',
  GT:   '/teams/gt.svg',
  KKR:  '/teams/kkr.svg',
  LSG:  '/teams/lsg.svg',
  MI:   '/teams/mi.svg',
  PBKS: '/teams/pbks.svg',
  RCB:  '/teams/rcb.svg',
  RR:   '/teams/rr.svg',
  SRH:  '/teams/srh.svg',
  UPW:  '/teams/upw.png',
}

/**
 * Returns a logo URL for any team short_name.
 * IPL franchises → /teams/*.svg; national teams → /flags/*.png
 */
export function getTeamLogoUrl(shortName: string): string | undefined {
  return TEAM_LOGO_MAP[shortName] ?? getFlagUrl(shortName)
}

/** Map F1 constructor short_name → logo filename */
const CONSTRUCTOR_LOGO_MAP: Record<string, string> = {
  MCL: "mclaren",
  FER: "ferrari",
  RBR: "redbull",
  MER: "mercedes",
  AMR: "aston-martin",
  ALP: "alpine",
  HAA: "haas",
  RB: "rb",
  WIL: "williams",
  AUD: "audi",
  CAD: "cadillac",
}

export function getConstructorLogoUrl(shortName: string): string | undefined {
  const slug = CONSTRUCTOR_LOGO_MAP[shortName]
  if (!slug) return undefined
  return `/constructors/${slug}.png`
}
