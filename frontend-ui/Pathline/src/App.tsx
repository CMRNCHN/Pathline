import { useEffect, useState, type ReactNode } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

type Page = 'dashboard' | 'paths' | 'accounts' | 'system'
type Theme = 'light' | 'dark'

interface Path {
  id: string
  name: string
  description: string
  status: 'ready' | 'missing-key' | 'draft'
  lastRun: string
  steps: { phrase: string; action: string }[]
}

interface Account {
  id: string
  name: string
  fields: { name: string; value: string; type: 'plain' | 'vault' }[]
  paths: string[]
}

interface VaultSecret {
  id: string
  keyName: string
  created: string
  boundProfiles: number
  status: 'sealed' | 'unused'
}

interface AuditEntry {
  time: string
  event: string
  details: string
  hash: string
}

// ─── Mock data ────────────────────────────────────────────────────────────────

const PATHS: Path[] = [
  {
    id: 'p1',
    name: 'Customer Support IVR Verification',
    description: 'Automates verification code entry for customer support IVR flows.',
    status: 'ready',
    lastRun: '10m ago',
    steps: [
      { phrase: '"Press 1 for Verification"', action: 'Keypad "1"' },
      { phrase: '"Enter your 4-digit PIN"', action: 'Input {{account.pin}}' },
      { phrase: '"Thank you, confirmed"', action: 'ACCEPT & END CALL' },
    ],
  },
  {
    id: 'p2',
    name: 'Account Balance Check',
    description: 'Retrieves account balance via automated IVR using vault-bound credentials.',
    status: 'ready',
    lastRun: '2h ago',
    steps: [
      { phrase: '"For balance, press 2"', action: 'Keypad "2"' },
      { phrase: '"Enter your account number"', action: 'Input {{account.number}}' },
      { phrase: '"Your balance is"', action: 'RECORD & END CALL' },
    ],
  },
  {
    id: 'p3',
    name: 'Order Cancellation',
    description: 'Cancels an order through automated IVR — requires vault SSN binding.',
    status: 'missing-key',
    lastRun: 'Never',
    steps: [
      { phrase: '"For cancellations, press 4"', action: 'Keypad "4"' },
      { phrase: '"Enter last 4 of SSN"', action: 'Input {{account.ssn_last4}}' },
    ],
  },
]

const ACCOUNTS: Account[] = [
  {
    id: 'acc_prod_001',
    name: 'Production Customer Account A',
    fields: [
      { name: 'phone_number', value: '+1 (555) 019-2831', type: 'plain' },
      { name: 'account_pin', value: 'PROD_PIN_KEY', type: 'vault' },
      { name: 'ssn_last4', value: 'SSN_SECRET_KEY', type: 'vault' },
      { name: 'account_number', value: '4821-0019-3847', type: 'plain' },
    ],
    paths: ['Customer Support IVR Verification', 'Account Balance Check'],
  },
  {
    id: 'acc_test_002',
    name: 'Test Account B',
    fields: [
      { name: 'phone_number', value: '+1 (555) 888-0012', type: 'plain' },
      { name: 'account_pin', value: 'TEST_PIN_KEY', type: 'vault' },
    ],
    paths: ['Account Balance Check'],
  },
]

const VAULT: VaultSecret[] = [
  { id: 'v1', keyName: 'PROD_PIN_KEY', created: '2026-07-20', boundProfiles: 2, status: 'sealed' },
  { id: 'v2', keyName: 'SSN_SECRET_KEY', created: '2026-07-22', boundProfiles: 1, status: 'sealed' },
  { id: 'v3', keyName: 'API_OPERATOR_TOKEN', created: '2026-07-24', boundProfiles: 0, status: 'unused' },
  { id: 'v4', keyName: 'TEST_PIN_KEY', created: '2026-07-23', boundProfiles: 1, status: 'sealed' },
]

const AUDIT: AuditEntry[] = [
  { time: '10:14:02 AM', event: 'CallState Accept', details: 'Path verification accepted by IVR system', hash: 'a8f9...31c2' },
  { time: '10:13:45 AM', event: 'Keypad Inject', details: "Injected digit '1' → IVR DTMF channel", hash: 'e3b1...88a4' },
  { time: '10:13:30 AM', event: 'Phrase Match', details: 'Matched "Press 1 for Verification"', hash: '7c4d...99b1' },
  { time: '10:12:58 AM', event: 'Call Started', details: 'RTP stream opened → 127.0.0.1:5060', hash: '2f1e...c4a9' },
  { time: '09:30:12 AM', event: 'CallState Accept', details: 'Balance check completed, IVR acknowledged', hash: 'b9d3...44f7' },
]

/** Latest outcome per Path — Dashboard shows one row per Path, not engine health. */
const PATH_LATEST = [
  {
    pathId: 'p1',
    path: 'Customer Support IVR Verification',
    account: 'Prod Account A',
    when: '10:14 AM',
    duration: '01:42',
    outcome: 'accepted' as const,
    summary: 'Verified and accepted by the phone menu',
  },
  {
    pathId: 'p2',
    path: 'Account Balance Check',
    account: 'Test Account B',
    when: '09:30 AM',
    duration: '00:55',
    outcome: 'completed' as const,
    summary: 'Finished — balance recorded',
  },
  {
    pathId: 'p3',
    path: 'Order Cancellation',
    account: 'Test Account B',
    when: '—',
    duration: '—',
    outcome: 'idle' as const,
    summary: 'Not run yet',
  },
]

// ─── Micro components ─────────────────────────────────────────────────────────

function Icon({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`w-3.5 h-3.5 flex-shrink-0 ${className}`}
      aria-hidden
    >
      {children}
    </svg>
  )
}

const Icons = {
  dashboard: (
    <Icon>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </Icon>
  ),
  paths: (
    <Icon>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="12" r="2.5" />
      <circle cx="6" cy="18" r="2.5" />
      <path d="M8.2 7.5 15.5 11" />
      <path d="M8.2 16.5 15.5 13" />
    </Icon>
  ),
  accounts: (
    <Icon>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 19.5c1.8-3.2 4.2-4.5 7-4.5s5.2 1.3 7 4.5" />
    </Icon>
  ),
  vault: (
    <Icon>
      <rect x="4" y="10" width="16" height="11" rx="1.5" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      <circle cx="12" cy="15.5" r="1.25" fill="currentColor" stroke="none" />
    </Icon>
  ),
  system: (
    <Icon>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8" />
    </Icon>
  ),
  sun: (
    <Icon>
      <circle cx="12" cy="12" r="3.5" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.05 5.05l1.4 1.4M17.55 17.55l1.4 1.4M17.55 5.05l-1.4 1.4M6.45 17.55l-1.4 1.4" />
    </Icon>
  ),
  moon: (
    <Icon>
      <path d="M20 14.5A7.5 7.5 0 1 1 9.5 4 6 6 0 0 0 20 14.5z" />
    </Icon>
  ),
}

function Badge({ variant, children }: { variant: 'success' | 'warning' | 'error' | 'muted' | 'primary'; children: React.ReactNode }) {
  const styles: Record<string, string> = {
    success: 'bg-success-soft text-success border border-success-border',
    warning: 'bg-warning-soft text-warning border border-warning-border',
    error: 'bg-destructive-soft text-destructive border border-destructive-border',
    muted: 'bg-muted text-muted-foreground border border-border',
    primary: 'bg-primary-soft text-foreground border border-primary-ring',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium tracking-wide ${styles[variant]}`}>
      {children}
    </span>
  )
}

function StatusDot({ color }: { color: 'green' | 'blue' | 'yellow' | 'red' | 'gray' }) {
  const colors: Record<string, string> = {
    green: 'bg-success',
    blue: 'bg-primary',
    yellow: 'bg-warning',
    red: 'bg-destructive',
    gray: 'bg-muted-foreground/40',
  }
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${colors[color]}`} />
}

function Btn({
  variant = 'default',
  size = 'md',
  onClick,
  children,
  className = '',
}: {
  variant?: 'default' | 'secondary' | 'ghost' | 'outline' | 'destructive' | 'primary'
  size?: 'sm' | 'md' | 'lg'
  onClick?: () => void
  children: React.ReactNode
  className?: string
}) {
  const base = 'inline-flex items-center gap-1.5 font-medium transition-all duration-150 cursor-pointer select-none rounded-md'
  const sizes: Record<string, string> = {
    sm: 'px-2.5 py-1 text-[12px]',
    md: 'px-3.5 py-1.5 text-[13px]',
    lg: 'px-5 py-2.5 text-[14px]',
  }
  const variants: Record<string, string> = {
    default: 'bg-primary text-primary-foreground hover:opacity-90 active:opacity-80',
    primary: 'bg-primary text-primary-foreground hover:opacity-90 active:opacity-80',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-muted border border-border',
    ghost: 'text-muted-foreground hover:bg-accent hover:text-foreground',
    outline: 'border border-border text-ink-soft hover:bg-accent hover:border-foreground/20',
    destructive: 'bg-destructive-soft text-destructive border border-destructive-border hover:opacity-90',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} onClick={onClick}>
      {children}
    </button>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1.5">
      {children}
    </div>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: Icons.dashboard },
  { id: 'paths', label: 'Path Library', icon: Icons.paths },
  { id: 'accounts', label: 'Accounts', icon: Icons.accounts },
  { id: 'system', label: 'System', icon: Icons.system },
] as const

function Sidebar({
  current,
  onNav,
  theme,
  onToggleTheme,
}: {
  current: Page
  onNav: (p: Page) => void
  theme: Theme
  onToggleTheme: () => void
}) {
  return (
    <aside
      style={{ width: 200, minWidth: 200 }}
      className="flex flex-col h-full bg-sidebar border-r border-border"
    >
      <div className="flex items-center gap-2 px-3 h-10 border-b border-border">
        <div className="w-5 h-5 rounded-sm bg-primary flex items-center justify-center">
          <span className="text-primary-foreground text-[10px] font-bold font-mono">P</span>
        </div>
        <span className="text-foreground font-semibold text-[13px] tracking-[0.14em] uppercase">Pathline</span>
      </div>

      <nav className="flex-1 px-1.5 py-2 flex flex-col gap-0.5">
        {NAV.map(item => {
          const active = current === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNav(item.id as Page)}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left text-[12px] transition-all duration-150 cursor-pointer group ${
                active
                  ? 'bg-primary-soft text-foreground border border-primary-ring'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground border border-transparent'
              }`}
            >
              <span className={active ? 'text-foreground' : 'text-muted-foreground/70 group-hover:text-muted-foreground'}>
                {item.icon}
              </span>
              {item.label}
              {active && <div className="ml-auto w-1 h-1 rounded-full bg-primary" />}
            </button>
          )
        })}
      </nav>

      <div className="px-2 py-2 border-t border-border flex flex-col gap-1.5">
        <button
          onClick={onToggleTheme}
          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[12px] text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
        >
          {theme === 'light' ? Icons.moon : Icons.sun}
          {theme === 'light' ? 'Dark mode' : 'Light mode'}
        </button>
        <div className="px-2.5">
          <div className="text-[11px] text-muted-foreground/70 font-mono">v1.0 Desktop</div>
        </div>
      </div>
    </aside>
  )
}

// ─── Header ───────────────────────────────────────────────────────────────────

const PAGE_TITLES: Record<Page, string> = {
  dashboard: 'Dashboard',
  paths: 'Path Library',
  accounts: 'Accounts',
  system: 'System & Runtime Health',
}

function Header({ page }: { page: Page }) {
  return (
    <header className="flex items-center justify-between px-4 h-10 border-b border-border bg-card/80 backdrop-blur-sm flex-shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-foreground font-medium text-[13px] tracking-wide">{PAGE_TITLES[page]}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-success-soft border border-success-border">
          <StatusDot color="green" />
          <span className="font-mono text-[11px] text-success tracking-wide">Line online</span>
        </div>
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-muted border border-border">
          <StatusDot color="gray" />
          <span className="font-mono text-[11px] text-muted-foreground tracking-wide">Local</span>
        </div>
      </div>
    </header>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function pathOutcomeBadge(outcome: (typeof PATH_LATEST)[number]['outcome']): {
  variant: 'success' | 'warning' | 'error' | 'muted'
  label: string
  dot: 'green' | 'yellow' | 'red' | 'gray'
} {
  if (outcome === 'accepted') return { variant: 'success', label: 'Accepted', dot: 'green' }
  if (outcome === 'completed') return { variant: 'success', label: 'Completed', dot: 'green' }
  if (outcome === 'blocked') return { variant: 'error', label: 'Blocked', dot: 'red' }
  if (outcome === 'idle') return { variant: 'muted', label: 'Idle', dot: 'gray' }
  return { variant: 'muted', label: 'Idle', dot: 'gray' }
}

function DashboardPage() {
  const ready = PATH_LATEST.filter(r => r.outcome === 'accepted' || r.outcome === 'completed').length
  const blocked = PATH_LATEST.filter(r => r.outcome === 'blocked' || r.outcome === 'idle').length
  const total = PATH_LATEST.length

  const actions = [
    { label: 'New Path', hint: 'Build a call flow', icon: Icons.paths, primary: true },
    { label: 'Dial Path', hint: 'Run against an account', icon: Icons.system, primary: false },
    { label: 'Add Account', hint: 'Profile + inputs', icon: Icons.accounts, primary: false },
    { label: 'Sealed secrets', hint: 'Under Accounts', icon: Icons.vault, primary: false },
  ]

  return (
    <div className="p-3 flex flex-col gap-2.5 overflow-y-auto h-full">
      {/* Snapshot strip */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'Paths', value: String(total), sub: 'tracked' },
          { label: 'Succeeded', value: String(ready), sub: 'last run ok' },
          { label: 'Idle', value: String(blocked), sub: 'not run yet' },
          { label: 'Accounts', value: '2', sub: 'ready to dial' },
        ].map(stat => (
          <div
            key={stat.label}
            className="rounded-md border border-border bg-card px-2.5 py-2 surface-shadow"
          >
            <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{stat.label}</div>
            <div className="text-[18px] font-semibold text-foreground leading-tight mt-0.5 tabular-nums">{stat.value}</div>
            <div className="text-[11px] text-muted-foreground">{stat.sub}</div>
          </div>
        ))}
      </div>

      {/* Quick actions as tiles */}
      <div>
        <SectionLabel>Quick Actions</SectionLabel>
        <div className="grid grid-cols-4 gap-2">
          {actions.map(a => (
            <button
              key={a.label}
              className={`text-left rounded-md border px-2.5 py-2 transition-colors cursor-pointer surface-shadow ${
                a.primary
                  ? 'bg-primary text-primary-foreground border-primary hover:opacity-90'
                  : 'bg-card border-border hover:bg-accent text-foreground'
              }`}
            >
              <div className={`mb-1.5 ${a.primary ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>
                {a.icon}
              </div>
              <div className="text-[12px] font-semibold leading-tight">{a.label}</div>
              <div className={`text-[10px] mt-0.5 ${a.primary ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                {a.hint}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Dense path status table */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between mb-1.5">
          <SectionLabel>Path Status</SectionLabel>
          <span className="text-[10px] font-mono text-muted-foreground -mt-1.5">Latest run per path</span>
        </div>
        <div className="rounded-md border border-border bg-card overflow-hidden surface-shadow flex-1">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                {['Path', 'Result', 'Summary', 'When', 'Account', ''].map(h => (
                  <th
                    key={h || 'act'}
                    className="text-left px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground font-medium"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PATH_LATEST.map(row => {
                const badge = pathOutcomeBadge(row.outcome)
                return (
                  <tr key={row.pathId} className="border-b border-border last:border-0 hover:bg-accent/40 transition-colors">
                    <td className="px-2.5 py-1.5">
                      <div className="flex items-center gap-2">
                        <StatusDot color={badge.dot} />
                        <span className="font-medium text-foreground">{row.path}</span>
                      </div>
                    </td>
                    <td className="px-2.5 py-1.5">
                      <Badge variant={badge.variant}>{badge.label}</Badge>
                    </td>
                    <td className="px-2.5 py-1.5 text-ink-soft max-w-[220px] truncate">{row.summary}</td>
                    <td className="px-2.5 py-1.5 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {row.when}
                      <span className="text-muted-foreground/60"> · {row.duration}</span>
                    </td>
                    <td className="px-2.5 py-1.5 text-muted-foreground whitespace-nowrap">{row.account}</td>
                    <td className="px-2.5 py-1.5 text-right">
                      <Btn variant="ghost" size="sm">Open</Btn>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Path Library ─────────────────────────────────────────────────────────────

function PathsPage() {
  const [selected, setSelected] = useState<Path>(PATHS[0])
  const [tab, setTab] = useState<'edit' | 'dial'>('edit')
  const [search, setSearch] = useState('')
  const [dialing, setDialing] = useState(false)

  const filtered = PATHS.filter(p => p.name.toLowerCase().includes(search.toLowerCase()))

  const statusVariant = (s: Path['status']): 'success' | 'warning' | 'error' => {
    if (s === 'ready') return 'success'
    if (s === 'draft') return 'warning'
    return 'error'
  }
  const statusLabel = (s: Path['status']) => {
    if (s === 'ready') return 'Ready'
    if (s === 'draft') return 'Draft'
    return 'Missing Key'
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className="w-60 border-r border-border flex flex-col flex-shrink-0 bg-card/40">
        <div className="p-2 border-b border-border flex flex-col gap-1.5">
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground text-[11px]">⌕</span>
            <input
              className="w-full bg-card border border-border rounded-md pl-7 pr-3 py-1.5 text-[12px] text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/15 transition-colors"
              placeholder="Search paths…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Btn variant="primary" size="sm" className="w-full justify-center">+ New Path</Btn>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {filtered.map(path => (
            <button
              key={path.id}
              onClick={() => setSelected(path)}
              className={`w-full text-left px-3 py-2 border-b border-border transition-all cursor-pointer ${
                selected.id === path.id
                  ? 'bg-primary-soft border-l-2 border-l-primary'
                  : 'hover:bg-accent/70 border-l-2 border-l-transparent'
              }`}
            >
              <div className="text-[13px] text-foreground mb-1 font-medium">{path.name}</div>
              <div className="flex items-center gap-2">
                <Badge variant={statusVariant(path.status)}>{statusLabel(path.status)}</Badge>
                <span className="text-[10px] text-muted-foreground font-mono">Last run {path.lastRun}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden bg-background">
        <div className="px-4 py-2.5 border-b border-border flex-shrink-0 bg-card/50">
          <div className="flex items-start justify-between mb-1">
            <div>
              <h2 className="text-[15px] font-semibold text-foreground">{selected.name}</h2>
              <p className="text-[12px] text-muted-foreground mt-0.5">{selected.description}</p>
            </div>
            <Badge variant={statusVariant(selected.status)}>{statusLabel(selected.status)}</Badge>
          </div>
        </div>

        <div className="flex border-b border-border px-4 flex-shrink-0 bg-card/30">
          {(['edit', 'dial'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 text-[12px] font-medium transition-all cursor-pointer border-b-2 -mb-px ${
                tab === t
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-ink-soft'
              }`}
            >
              {t === 'edit' ? 'Edit Path' : 'Dial & Execute'}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {tab === 'edit' ? (
            <div>
              <SectionLabel>Phrase Matching Rules</SectionLabel>
              <div className="rounded-lg border border-border overflow-hidden bg-card surface-shadow">
                <table className="w-full text-[12px]">
                  <thead>
                    <tr className="bg-muted/70 border-b border-border">
                      <th className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground w-1/2">
                        When Phrase Matched
                      </th>
                      <th className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                        Inject Keypad / Action
                      </th>
                      <th className="w-12" />
                    </tr>
                  </thead>
                  <tbody>
                    {selected.steps.map((step, i) => (
                      <tr key={i} className="border-b border-border last:border-0 hover:bg-accent/50 group">
                        <td className="px-3 py-2 font-mono text-[11px] text-primary">{step.phrase}</td>
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center gap-2">
                            <span className="text-muted-foreground/40">→</span>
                            <span className="font-mono text-[11px] text-success">{step.action}</span>
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive text-[11px] transition-all cursor-pointer">
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 flex gap-2">
                <Btn variant="secondary" size="sm">+ Add Rule</Btn>
                <Btn variant="default" size="sm">Save Path</Btn>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5">
              <div className="rounded-md border border-primary-ring bg-primary-soft p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-[11px] font-mono uppercase tracking-widest text-primary/80">
                    Live Execution
                  </div>
                  {dialing && <Badge variant="primary">● ACTIVE CALL</Badge>}
                </div>
                <div className="flex items-center gap-3">
                  <Btn variant="default" size="md" onClick={() => setDialing(!dialing)}>
                    {dialing ? 'End Call' : 'Dial & Execute'}
                  </Btn>
                  <div className="text-[11px] text-muted-foreground font-mono">
                    Account: <span className="text-ink-soft">Prod Account A</span>
                  </div>
                </div>
              </div>

              {dialing && (
                <div className="rounded-md border border-border bg-card p-3 surface-shadow">
                  <SectionLabel>Live Transcript</SectionLabel>
                  <div className="space-y-2 font-mono text-[11px]">
                    <div className="flex gap-3 items-center">
                      <span className="text-muted-foreground">00:04</span>
                      <span className="text-muted-foreground">[IVR]</span>
                      <span className="text-foreground">"Press 1 for Verification"</span>
                      <Badge variant="success">Matched</Badge>
                    </div>
                    <div className="flex gap-3">
                      <span className="text-muted-foreground">00:05</span>
                      <span className="text-primary">[INJECT]</span>
                      <span className="text-foreground">DTMF "1"</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-muted-foreground">00:08</span>
                      <span className="text-muted-foreground">Listening…</span>
                      <span className="animate-pulse text-primary">▌</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Accounts ─────────────────────────────────────────────────────────────────

function AccountsPage() {
  const [selected, setSelected] = useState<Account>(ACCOUNTS[0])
  const [search, setSearch] = useState('')

  const filtered = ACCOUNTS.filter(a => a.name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="flex h-full overflow-hidden">
      <div className="w-60 border-r border-border flex flex-col flex-shrink-0 bg-card/40">
        <div className="p-2 border-b border-border flex flex-col gap-1.5">
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground text-[11px]">⌕</span>
            <input
              className="w-full bg-card border border-border rounded-md pl-7 pr-3 py-1.5 text-[12px] text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/15 transition-colors"
              placeholder="Search accounts…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Btn variant="primary" size="sm" className="w-full justify-center">+ New Profile</Btn>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {filtered.map(acc => (
            <button
              key={acc.id}
              onClick={() => setSelected(acc)}
              className={`w-full text-left px-3 py-2 border-b border-border transition-all cursor-pointer ${
                selected.id === acc.id
                  ? 'bg-primary-soft border-l-2 border-l-primary'
                  : 'hover:bg-accent/70 border-l-2 border-l-transparent'
              }`}
            >
              <div className="text-[13px] text-foreground mb-1 font-medium">{acc.name}</div>
              <div className="text-[10px] text-muted-foreground font-mono">
                {acc.fields.length} inputs · {acc.paths.length} path{acc.paths.length !== 1 ? 's' : ''} OK
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border flex-shrink-0 bg-card/50">
          <h2 className="text-[15px] font-semibold text-foreground">{selected.name}</h2>
          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">ID: {selected.id}</div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          <div>
            <SectionLabel>Input Fields</SectionLabel>
            <div className="rounded-lg border border-border overflow-hidden bg-card surface-shadow">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="bg-muted/70 border-b border-border">
                    <th className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Field Name</th>
                    <th className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Value / Binding</th>
                    <th className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.fields.map((field, i) => (
                    <tr key={i} className="border-b border-border last:border-0 hover:bg-accent/50">
                      <td className="px-3 py-1.5 font-mono text-[11px] text-primary">{field.name}</td>
                      <td className="px-3 py-1.5 text-ink-soft">
                        {field.type === 'vault' ? (
                          <span className="inline-flex items-center gap-1.5">
                            <span className="text-warning font-mono text-[10px]">KEY</span>
                            <span className="font-mono text-[11px] text-warning">{field.value}</span>
                          </span>
                        ) : (
                          <span className="font-mono text-[11px]">{field.value}</span>
                        )}
                      </td>
                      <td className="px-3 py-1.5">
                        <Badge variant={field.type === 'vault' ? 'warning' : 'muted'}>
                          {field.type === 'vault' ? 'Vault Key' : 'Plain'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Btn variant="secondary" size="sm">+ Add Field</Btn>
            </div>
          </div>

          <div>
            <SectionLabel>Compatible Paths</SectionLabel>
            <div className="flex flex-col gap-1.5">
              {selected.paths.map((p, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-md bg-success-soft border border-success-border">
                  <span className="text-success text-[11px]">✓</span>
                  <span className="text-[12px] text-ink-soft">{p}</span>
                  <Badge variant="success">Ready</Badge>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Input Vault ──────────────────────────────────────────────────────────────

function VaultPage() {
  const [showModal, setShowModal] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [secretValue, setSecretValue] = useState('')

  return (
    <div className="p-4 flex flex-col gap-3 h-full overflow-y-auto relative">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-1">Sealed Secret Slots</div>
          <div className="text-[11px] text-muted-foreground">On-device AES-256 encrypted vault. Secrets never exposed in plaintext.</div>
        </div>
        <Btn variant="default" size="sm" onClick={() => setShowModal(true)}>+ Add New Secret Slot</Btn>
      </div>

      <div className="rounded-lg border border-border overflow-hidden bg-card surface-shadow">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-muted/70 border-b border-border">
              {['Vault Key Name', 'Created Date', 'Bound Accounts', 'Security Status', ''].map(h => (
                <th key={h} className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {VAULT.map(row => (
              <tr key={row.id} className="border-b border-border last:border-0 hover:bg-accent/50 group transition-colors">
                <td className="px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="text-warning font-mono text-[10px]">KEY</span>
                    <span className="font-mono text-[12px] text-warning">{row.keyName}</span>
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">{row.created}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {row.boundProfiles === 0 ? (
                    <span className="text-muted-foreground/50">None</span>
                  ) : (
                    `${row.boundProfiles} Profile${row.boundProfiles > 1 ? 's' : ''}`
                  )}
                </td>
                <td className="px-3 py-2">
                  <Badge variant={row.status === 'sealed' ? 'success' : 'muted'}>
                    {row.status === 'sealed' ? 'Sealed' : 'Unused'}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-right">
                  <button className="opacity-0 group-hover:opacity-100 text-[11px] text-muted-foreground hover:text-destructive transition-all cursor-pointer">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div
          className="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50" style={{ background: 'var(--overlay)' }}
          onClick={e => e.target === e.currentTarget && setShowModal(false)}
        >
          <div className="bg-card border border-border rounded-xl w-[460px] surface-shadow-lg">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
              <div>
                <div className="text-[14px] font-semibold text-foreground">Add New Secret Slot</div>
                <div className="text-[11px] text-muted-foreground mt-0.5">Secret is sealed on save and never stored plaintext.</div>
              </div>
              <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground text-[16px] cursor-pointer transition-colors">✕</button>
            </div>
            <div className="px-6 py-5 flex flex-col gap-2.5">
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-1.5">Key Name</label>
                <input
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-[13px] text-foreground font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/15 transition-colors"
                  placeholder="e.g. PROD_PIN_KEY"
                  value={keyName}
                  onChange={e => setKeyName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-widest text-muted-foreground mb-1.5">Secret Value</label>
                <input
                  type="password"
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-[13px] text-foreground font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/15 transition-colors"
                  placeholder="••••••••••••"
                  value={secretValue}
                  onChange={e => setSecretValue(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5 border-t border-border">
              <Btn variant="ghost" size="sm" onClick={() => setShowModal(false)}>Cancel</Btn>
              <Btn variant="default" size="md" onClick={() => { setShowModal(false); setKeyName(''); setSecretValue('') }}>
                Seal & Save Secret
              </Btn>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── System ───────────────────────────────────────────────────────────────────

function SystemPage() {
  const systemRows = [
    {
      label: 'Phone line',
      status: 'Connected',
      detail: 'Ready to place calls on the lab line',
      ok: true,
    },
    {
      label: 'Speech recognition',
      status: 'Ready',
      detail: 'Listening on this Mac — no cloud speech',
      ok: true,
    },
    {
      label: 'App services',
      status: 'Online',
      detail: 'Local API and encrypted storage are up',
      ok: true,
    },
  ]

  return (
    <div className="p-4 flex flex-col gap-3 h-full overflow-y-auto">
      <div>
        <SectionLabel>System Status</SectionLabel>
        <div className="rounded-md border border-border bg-card p-3 surface-shadow">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[13px] font-semibold text-foreground">Everything you need to dial</div>
            <Badge variant="success">All good</Badge>
          </div>
          <div className="flex flex-col gap-1">
            {systemRows.map(row => (
              <div
                key={row.label}
                className="flex items-center gap-2.5 rounded-md border border-border bg-background/80 px-2.5 py-1.5"
              >
                <StatusDot color={row.ok ? 'green' : 'red'} />
                <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] font-medium text-foreground">{row.label}</span>
                  <Badge variant={row.ok ? 'success' : 'error'}>{row.status}</Badge>
                  <span className="text-[11px] text-muted-foreground">{row.detail}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <SectionLabel>Local Audit Ledger</SectionLabel>
        <div className="rounded-lg border border-border overflow-hidden bg-card surface-shadow">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-muted/70 border-b border-border">
                {['Time', 'Event', 'Details', 'Hash'].map(h => (
                  <th key={h} className="text-left px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {AUDIT.map((row, i) => (
                <tr key={i} className="border-b border-border last:border-0 hover:bg-accent/50 transition-colors">
                  <td className="px-3 py-1.5 font-mono text-[11px] text-muted-foreground whitespace-nowrap">{row.time}</td>
                  <td className="px-3 py-1.5 text-foreground font-medium">{row.event}</td>
                  <td className="px-3 py-1.5 text-muted-foreground">{row.details}</td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-primary/70">{row.hash}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'light'
    const saved = window.localStorage.getItem('pathline-theme')
    return saved === 'dark' || saved === 'light' ? saved : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem('pathline-theme', theme)
  }, [theme])

  return (
    <div className="flex h-full w-full bg-background text-foreground overflow-hidden" data-theme={theme}>
      <Sidebar
        current={page}
        onNav={setPage}
        theme={theme}
        onToggleTheme={() => setTheme(t => (t === 'light' ? 'dark' : 'light'))}
      />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header page={page} />
        <main className="flex-1 overflow-hidden">
          {page === 'dashboard' && <DashboardPage />}
          {page === 'paths' && <PathsPage />}
          {page === 'accounts' && <AccountsPage />}
          {page === 'system' && <SystemPage />}
        </main>
      </div>
    </div>
  )
}
