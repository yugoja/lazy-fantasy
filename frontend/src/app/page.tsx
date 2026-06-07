'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { Skeleton } from '@/components/ui/skeleton';
import s from './landing.module.css';

const NATIONS = [
  { f: '🇧🇷', n: 'Brazil' },       { f: '🇦🇷', n: 'Argentina' },
  { f: '🇫🇷', n: 'France' },        { f: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', n: 'England' },
  { f: '🇪🇸', n: 'Spain' },         { f: '🇩🇪', n: 'Germany' },
  { f: '🇵🇹', n: 'Portugal' },      { f: '🇳🇱', n: 'Netherlands' },
  { f: '🇧🇪', n: 'Belgium' },       { f: '🇲🇽', n: 'Mexico' },
  { f: '🇺🇸', n: 'USA' },           { f: '🇨🇦', n: 'Canada' },
  { f: '🇯🇵', n: 'Japan' },         { f: '🇰🇷', n: 'South Korea' },
  { f: '🇲🇦', n: 'Morocco' },       { f: '🇸🇳', n: 'Senegal' },
  { f: '🇳🇬', n: 'Nigeria' },       { f: '🇨🇴', n: 'Colombia' },
  { f: '🇺🇾', n: 'Uruguay' },       { f: '🇨🇭', n: 'Switzerland' },
  { f: '🇭🇷', n: 'Croatia' },       { f: '🇩🇰', n: 'Denmark' },
  { f: '🇵🇱', n: 'Poland' },        { f: '🇸🇦', n: 'Saudi Arabia' },
  { f: '🇮🇷', n: 'Iran' },          { f: '🇦🇺', n: 'Australia' },
  { f: '🇪🇨', n: 'Ecuador' },       { f: '🇬🇭', n: 'Ghana' },
  { f: '🇨🇲', n: 'Cameroon' },      { f: '🇷🇸', n: 'Serbia' },
  { f: '🇹🇷', n: 'Türkiye' },       { f: '🇦🇹', n: 'Austria' },
  { f: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', n: 'Scotland' },    { f: '🇨🇿', n: 'Czechia' },
  { f: '🇮🇹', n: 'Italy' },         { f: '🇨🇱', n: 'Chile' },
  { f: '🇵🇦', n: 'Panama' },        { f: '🇯🇲', n: 'Jamaica' },
  { f: '🇿🇦', n: 'South Africa' },  { f: '🇻🇪', n: 'Venezuela' },
  { f: '🇵🇾', n: 'Paraguay' },      { f: '🇳🇿', n: 'New Zealand' },
  { f: '🇷🇴', n: 'Romania' },       { f: '🇺🇦', n: 'Ukraine' },
  { f: '🇬🇷', n: 'Greece' },        { f: '🇸🇰', n: 'Slovakia' },
  { f: '🇨🇳', n: 'China' },         { f: '🇹🇳', n: 'Tunisia' },
];

const TICKER_NATIONS = [...NATIONS, ...NATIONS];

const PRED_ROWS = [
  { done: true,  cat: 'Match Result',        pick: 'England win',          pts: '+5 pts'  },
  { done: true,  cat: 'Exact Scoreline',     pick: '2 — 1',                pts: '+10 pts' },
  { done: true,  cat: 'Player Pick 1 · FWD', pick: 'Harry Kane (scored)',  pts: '+13 pts' },
  { done: false, cat: 'Player Pick 2',        pick: 'Pick a player',        pts: '— pts'   },
  { done: false, cat: 'Player Pick 3',        pick: 'Pick a player',        pts: '— pts'   },
];

const STEPS = [
  {
    n: '1',
    title: 'Create a league & invite your crew',
    desc: 'Sign up, name your league, share a 6-digit code. Your mates join — no app install needed. WhatsApp the code. Done.',
  },
  {
    n: '2',
    title: 'Predict before every match',
    desc: 'Pick the scoreline and three players you fancy, then let 104 matches do the talking. One shot per match. No going back.',
  },
  {
    n: '3',
    title: 'Watch the leaderboard heat up',
    desc: "Points drop after each result. The real World Cup drama is on the pitch — the real punishment is in your group chat.",
  },
];

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || isAuthenticated) {
    return (
      <div className="py-10 px-6 space-y-6 max-w-sm mx-auto">
        <Skeleton className="h-8 w-48 mx-auto" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-4 w-3/4 mx-auto" />
        <Skeleton className="h-10 w-40 mx-auto" />
      </div>
    );
  }

  return (
    <div className={s.page}>

      {/* ── Nav ── */}
      <nav className={s.nav}>
        <div className={s.navInner}>
          <span className={s.navLogo}>Lazy<span>Fantasy</span></span>
          <div className={s.navActions}>
            <Link href="/login"  className={`${s.btn} ${s.btnGhost}`}>Sign In</Link>
            <Link href="/signup" className={`${s.btn} ${s.btnPrimary}`}>Play Free</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className={s.hero}>
        <div className={s.heroBloom} />
        <div className={s.heroBloom2} />

        <div className={s.wcStamp}>
          <div className={s.wcStampContent}>
            <span className={s.wcStampBall}>⚽</span>
            <span className={s.wcStampYear}>2026</span>
            <span className={s.wcStampText}>World Cup</span>
          </div>
        </div>

        <div className={s.heroInner}>
          <div className={`${s.heroEyebrow} ${s.au}`}>
            <span className={s.eyebrowDot} />
            World Cup 2026 · Predictions Open
          </div>

          <h1 className={`${s.heroHeadline} ${s.au} ${s.d1}`}>
            Your mates think they know football<span className={s.dot}>.</span>
          </h1>

          <p className={`${s.heroTagline} ${s.au} ${s.d2}`}>Prove them wrong.</p>
          <p className={`${s.heroBody} ${s.au} ${s.d3}`}>
            Predict every match. Play in a private league with your crew.
            Let the World Cup settle the group chat once and for all.
          </p>

          <div className={`${s.heroCtas} ${s.au} ${s.d4}`}>
            <Link href="/signup" className={s.heroCtaMain}>Start Playing Free</Link>
            <Link href="/login"  className={s.heroCtaSec}>Sign In</Link>
          </div>
        </div>
      </section>

      {/* ── Ticker ── */}
      <div className={s.tickerWrap}>
        <div className={s.tickerTag}>48 Nations</div>
        <div className={s.tickerOverflow}>
          <div className={s.tickerTrack}>
            {TICKER_NATIONS.map((nation, i) => (
              <div key={i} className={s.tickerNation}>
                <span>{nation.f}</span>
                <span>{nation.n}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Stats strip ── */}
      <div className={s.statsStrip}>
        <div className={s.statsInner}>
          <div className={s.stat}>
            <div className={s.statVal}>48</div>
            <div className={s.statLbl}>Nations</div>
          </div>
          <div className={s.statsDivider} />
          <div className={s.stat}>
            <div className={s.statVal}>104</div>
            <div className={s.statLbl}>Matches</div>
          </div>
          <div className={s.statsDivider} />
          <div className={s.stat}>
            <div className={s.statVal}>1<span className={s.gold}>★</span></div>
            <div className={s.statLbl}>Champion</div>
          </div>
        </div>
      </div>

      {/* ── What you predict ── */}
      <div className={s.section}>
        <div className={s.eyebrow}>How you predict</div>
        <div className={s.sectionH}>Score it. Pick the stars.</div>
        <p className={s.sectionSub}>
          Scoreline + 3 player picks. Player points vary by position — more for defenders and keepers. Knockout rounds score double.
        </p>

        <div className={s.matchCard}>
          <div className={s.mcHeader}>
            <div className={s.mcMeta}>
              <div className={s.mcTournament}>⚽ FIFA WC 2026 · Group C</div>
              <div className={s.mcLock}>🔒 Locks 14 Jun 18:00</div>
            </div>
            <div className={s.mcTeams}>
              <div className={s.mcTeam}>
                <span className={s.mcFlag}>🏴󠁧󠁢󠁥󠁮󠁧󠁿</span>
                <span className={s.mcTeamName}>England</span>
              </div>
              <div className={s.mcScoreBlock}>
                <div className={s.mcScoreNums}>
                  <span className={s.mcScoreDigit}>2</span>
                  <span className={s.mcScoreDash}>—</span>
                  <span className={s.mcScoreDigit}>1</span>
                </div>
                <div className={s.mcScoreLabel}>Your pick</div>
              </div>
              <div className={s.mcTeam}>
                <span className={s.mcFlag}>🇫🇷</span>
                <span className={s.mcTeamName}>France</span>
              </div>
            </div>
          </div>

          <div className={s.mcPreds}>
            {PRED_ROWS.map((row) => (
              <div key={row.cat} className={s.predRow}>
                <div className={`${s.predCircle} ${row.done ? s.predCircleDone : s.predCircleEmpty}`}>
                  {row.done ? '✓' : '—'}
                </div>
                <div className={s.predInfo}>
                  <div className={s.predCat}>{row.cat}</div>
                  <div className={`${s.predPick} ${row.done ? '' : s.predPickDim}`}>{row.pick}</div>
                </div>
                <div className={`${s.predPts} ${row.done ? '' : s.predPtsDim}`}>{row.pts}</div>
              </div>
            ))}
          </div>

          <div className={s.mcTotal}>
            <span className={s.mcTotalLbl}>This example · group stage</span>
            <span className={s.mcTotalPts}>28 pts <span className={s.mcTotalBonus}>· 56 in knockouts</span></span>
          </div>
        </div>

        <p className={s.matchHint}>Predictions lock at kickoff. Player points vary by position and events.</p>
      </div>

      {/* ── How it works ── */}
      <div className={s.section} style={{ paddingTop: 0 }}>
        <div className={s.eyebrow}>How it works</div>
        <div className={s.sectionH}>Ready before kickoff.</div>
        <p className={s.sectionSub}>Under 2 minutes. Guaranteed.</p>
        <div className={s.steps}>
          {STEPS.map((step) => (
            <div key={step.n} className={s.step}>
              <div className={s.stepNum}>{step.n}</div>
              <div className={s.stepContent}>
                <div className={s.stepTitle}>{step.title}</div>
                <div className={s.stepDesc}>{step.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Banter strip ── */}
      <div className={s.banterStrip}>
        <div className={s.banterInner}>
          <div className={s.banterQ}>
            The real final happens in your <span className={s.hi}>group chat.</span>
          </div>
          <p className={s.banterBody}>
            No money. No stakes. Just the eternal burden of being confidently wrong
            in front of 11 friends for six weeks.
          </p>
          <div className={s.chat}>
            <div className={s.chatRow}>
              <div className={s.chatAv}>🔥</div>
              <div className={s.chatCol}>
                <div className={`${s.bubble} ${s.bubbleThem}`}>England are NOT winning this wtf</div>
                <div className={s.chatTs}>Raj · 14 Jun · Match Day 1</div>
              </div>
            </div>
            <div className={`${s.chatRow} ${s.chatRowMe}`}>
              <div className={s.chatAv}>👑</div>
              <div className={`${s.chatCol} ${s.chatColMe}`}>
                <div className={`${s.bubble} ${s.bubbleMe}`}>+28 pts. Kane scorer caller. Said what I said.</div>
                <div className={s.chatTs}>You · 14 Jun</div>
              </div>
            </div>
            <div className={s.chatRow}>
              <div className={s.chatAv}>😤</div>
              <div className={s.chatCol}>
                <div className={`${s.bubble} ${s.bubbleThem}`}>That was clearly lucky bro</div>
                <div className={s.chatTs}>Raj · 14 Jun</div>
              </div>
            </div>
            <div className={`${s.chatRow} ${s.chatRowMe}`}>
              <div className={s.chatAv}>👑</div>
              <div className={`${s.chatCol} ${s.chatColMe}`}>
                <div className={`${s.bubble} ${s.bubbleMe}`}>Leaderboard doesn't care about luck 🏆</div>
                <div className={s.chatTs}>You · 14 Jun</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Other sports ── */}
      <div className={s.section} style={{ paddingBottom: 16 }}>
        <div className={s.shelfLabel}>Also available on Lazy Fantasy</div>
        <div className={s.shelf}>
          <div className={s.shelfCard}>
            <div className={s.shelfIcon}>🏏</div>
            <div>
              <div className={s.shelfName}>IPL 2026</div>
              <div className={s.shelfSub}>Cricket · Season complete</div>
            </div>
          </div>
          <div className={s.shelfCard}>
            <div className={s.shelfIcon}>🏎️</div>
            <div>
              <div className={s.shelfName}>Formula 1</div>
              <div className={s.shelfSub}>2026 · Coming soon</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom CTA ── */}
      <div className={s.ctaWrap}>
        <div className={s.ctaCard}>
          <span className={s.ctaBall}>⚽</span>
          <div className={s.ctaH}>World Cup 2026 kicks off 11 June.</div>
          <p className={s.ctaSub}>
            Your group chat already thinks they've called the champion.
            Time to make them prove it.
          </p>
          <Link href="/signup" className={s.ctaBtn}>Challenge Your Mates</Link>
          <p className={s.ctaFree}>Free to play. Always.</p>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className={s.footer}>
        <div className={s.footerInner}>
          <div className={s.footerLogo}>Lazy<span>Fantasy</span></div>
          <div className={s.footerNote}>© 2026 · Free to play</div>
        </div>
      </footer>

    </div>
  );
}
