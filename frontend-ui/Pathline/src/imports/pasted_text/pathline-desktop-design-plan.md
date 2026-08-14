# Figma Design & Handoff Plan — Pathline Desktop

This plan provides a complete, copy-pasteable Figma design specification for constructing the **Pathline Desktop** GUI. It is structured specifically for Figma Starter (free) constraints and maps directly to the React + Tauri implementation in `client/`.

---

## 1. Project & Figma Setup

| Parameter | Specification |
| :--- | :--- |
| **Figma File Name** | `Pathline Desktop` (Single file model) |
| **Canvas Resolution** | **1280 × 800 px** (Default macOS Tauri Webview container) |
| **Typography** | `Inter` or System Sans-Serif (`font-sans`) |
| **Color System** | Dark theme primary (matching `client/src/styles.css` CSS variables) |
| **Framework Mapping** | Tailwind CSS + Radix UI / shadcn primitive patterns |

### Figma File Structure (8 Pages)
1. **`Foundations`**: Color variables, typography scale, iconography, component primitives.
2. **`Shell`**: App frame, 240px sidebar, header, navigation state variants.
3. **`Dashboard`**: Overview surface (status, quick actions, recent activity).
4. **`Path Library`**: Master-detail surface (Path list + detail with Edit and Dial sub-tabs).
5. **`Accounts`**: Profiles list + detail (fields, secret bindings, ready Paths).
6. **`Input Vault`**: Sealed secret manager surface + Add Secret modal.
7. **`System`**: Runtime health, telephony stack, STT status, local audit ledger.
8. **`Flows`**: Prototyping links and user interaction flow diagram.

---

## 2. Foundations & Design Tokens

### Color Palette (Tokens)

```css
/* Dark Mode Base Tokens */
--background: 224 71% 4%;        /* #090d16 Deep slate dark */
--foreground: 213 31% 91%;       /* #e2e8f0 Soft white text */
--card: 224 71% 6%;             /* #0d1321 Elevated card bg */
--card-foreground: 213 31% 91%;
--primary: 210 100% 52%;         /* #0a84ff Bright blue accent */
--primary-foreground: 0 0% 100%;
--secondary: 215 27.9% 16.9%;    /* #1e293b Subtle section bg */
--muted: 215 27.9% 16.9%;
--muted-foreground: 215.4 16.3% 56.9%; /* #64748b Secondary text */
--accent: 216 34% 17%;
--destructive: 0 62.8% 30.6%;    /* Red highlight for errors/SIP drop */
--border: 216 34% 17%;           /* Subtle border stroke */
--success: 142 71% 45%;          /* Emerald green for online/SIP registered */
```

### Core Primitive Components to Create in `Foundations`

- **Button**: Variants (`default`, `secondary`, `outline`, `ghost`, `destructive`), Sizes (`sm`, `md`, `lg`, `icon`).
- **Input / Search Input**: Default, focused, error state, with left icon slot.
- **Badge**: `default` (slate), `success` (green), `warning` (amber), `destructive` (red).
- **Card**: Container with subtle border (`--border`) and 8px border-radius.
- **Tabs**: Tab bar with active underline indicator (`Edit` | `Dial`).
- **Table**: Clean rows with header dividers and action cells.
- **Dialog / Modal**: Centered modal overlay with header, body, and footer actions.
- **Select / Combobox**: Dropdown selector for account profile or vault key binding.

---

## 3. Surface Specifications & ASCII Layout Wireframes

### Surface 1: Shell Navigation Frame
- **Sidebar**: Fixed 240px width left panel.
- **Header**: Top 48px bar with current surface title and SIP connection indicator.
- **Content Area**: Flexible 1040 × 752 px viewport.

```
+-----------------------------------------------------------------------------+
| PATHLINE  [SIP: LAB ONLINE (127.0.0.1)]               [Operator: Local]     |
+---------------+-------------------------------------------------------------+
| [D] Dashboard |                                                             |
| [P] Path Lib  |                                                             |
| [A] Accounts  |                    MAIN CONTENT VIEWPORT                    |
| [V] Vault     |                         (1040 x 752)                        |
| [S] System    |                                                             |
|               |                                                             |
|---------------|                                                             |
| v1.0 Desktop  |                                                             |
+---------------+-------------------------------------------------------------+
```

---

### Surface 2: Dashboard
**Job**: Immediate situational awareness, rapid execution, and call logs.

```
+-----------------------------------------------------------------------------+
| Dashboard                                                                   |
+-----------------------------------------------------------------------------+
| STATUS CARDS                                                                |
| +-------------------+ +-------------------+ +-------------------+           |
| | SIP Transport     | | Local STT Engine  | | Active Accounts   |           |
| | [● REGISTERED]    | | [● WHISPER READY] | | [ 4 Profiles ]    |           |
| +-------------------+ +-------------------+ +-------------------+           |
|                                                                             |
| QUICK ACTIONS                                                               |
| [ + New Path ]   [ Dial Path... ]   [ + Add Account ]   [ Vault Status ]    |
|                                                                             |
| RECENT CALL ACTIVITY                                                        |
| Time     Path Name         Account Profile   Duration   Status              |
| -------- ----------------- ----------------- ---------- ------------------- |
| 10:14 AM IVR Verification  Prod Account A    01:42      Completed (Accepted)|
| 09:30 AM Balance Check     Test Account B    00:55      Completed           |
+-----------------------------------------------------------------------------+
```

---

### Surface 3: Path Library (Master-Detail with Sub-Tabs)
**Job**: Browse, configure, edit, and dial automated telephony paths.

```
+-----------------------------------------------------------------------------+
| Path Library                                                                |
+--------------------------+--------------------------------------------------+
| [ Search Paths...     ]  | Path: Customer Support IVR Verification          |
| [ + New Path          ]  | Description: Automates verification code entry  |
| ------------------------ +--------------------------------------------------+
| * Cust Verification      | [ Edit Path ]  |  [ Dial & Execute (Live) ]       |
|   Ready • Last run 10m   +--------------------------------------------------+
|                          | WHEN PHRASE MATCHED       INJECT KEYPAD / ACTION |
| * Account Balance Check  | ------------------------- ---------------------- |
|   Ready • Last run 2h    | "Press 1 for Verification" -> Keypad "1"        |
|                          | "Enter your 4-digit PIN"   -> Input {{account.pin}}|
| * Order Cancellation     | "Thank you, confirmed"    -> ACCEPT & END CALL   |
|   Missing Vault Key      |                                                  |
+--------------------------+--------------------------------------------------+
```

---

### Surface 4: Accounts (Profiles & Input Binding)
**Job**: Manage identity profiles and bind plaintext inputs or vault secrets.

```
+-----------------------------------------------------------------------------+
| Accounts                                                                    |
+--------------------------+--------------------------------------------------+
| [ Search Accounts...  ]  | Profile: Production Customer Account A           |
| [ + New Profile       ]  | ID: acc_prod_001                                 |
| ------------------------ +--------------------------------------------------+
| * Prod Account A         | FIELD NAME        VALUE / BINDING TYPE           |
|   4 inputs • 3 Paths OK  | ----------------- ------------------------------ |
|                          | phone_number      "+1 (555) 019-2831" (Plain)    |
| * Test Account B         | account_pin       [ Vault: PROD_PIN_KEY ]        |
|   2 inputs • 1 Path OK   | ssn_last4         [ Vault: SSN_SECRET_KEY ]      |
|                          |                                                  |
|                          | COMPATIBLE PATHS                                 |
|                          | [✓] Customer Support IVR Verification (Ready)    |
|                          | [✓] Balance Check (Ready)                        |
+--------------------------+--------------------------------------------------+
```

---

### Surface 5: Input Vault
**Job**: Sealed on-device secret storage. Secrets are never exposed in raw JSON.

```
+-----------------------------------------------------------------------------+
| Input Vault                                         [ + Add New Secret Slot ]|
+-----------------------------------------------------------------------------+
| SEALED SECRET SLOTS                                                         |
| Vault Key Name        Created Date     Bound Accounts   Status              |
| --------------------- ---------------- ---------------- ------------------- |
| PROD_PIN_KEY          2026-07-20       2 Profiles       Sealed (Encrypted)  |
| SSN_SECRET_KEY        2026-07-22       1 Profile        Sealed (Encrypted)  |
| API_OPERATOR_TOKEN    2026-07-24       0 Profiles       Sealed (Unused)     |
|                                                                             |
| [ DIALOG MODAL: Add New Secret Slot ]                                       |
| +-------------------------------------------------------------------------+ |
| | Key Name: [ PROD_PIN_KEY                              ]                 | |
| | Secret Value: [ ••••••••••••                          ]                 | |
| |                                                                         | |
| | [ Cancel ]                                         [ Seal & Save Secret ] | |
| +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
```

---

### Surface 6: System
**Job**: Monitor on-device runtime, SIP engine, Whisper STT, and security ledger.

```
+-----------------------------------------------------------------------------+
| System & Runtime Health                                                     |
+-----------------------------------------------------------------------------+
| RUNTIME ENGINES                                                             |
| +-----------------------------+ +-----------------------------+             |
| | SIP / RTP Stack (Rust)      | | Local STT Engine (Whisper)  |             |
| | Transport: UDP / SRTP       | | Model: ggml-base.en.bin   |             |
| | Target: 127.0.0.1:5060      | | Latency: 42ms             |             |
| | Status: Healthy             | | Status: Loaded & Active   |             |
| +-----------------------------+ +-----------------------------+             |
|                                                                             |
| ON-DEVICE SECURITY & AUDIT LEDGER                                           |
| Timestamp   Event Type           Details                       Ledger Hash  |
| ----------- -------------------- ----------------------------- ------------ |
| 10:14:02 AM CallState Accept     Path verification accepted    a8f9...31c2  |
| 10:13:45 AM Keypad Inject        Injected digit '1'            e3b1...88a4  |
| 10:13:30 AM Phrase Match         Matched "Press 1 for..."      7c4d...99b1  |
+-----------------------------------------------------------------------------+
```

---

## 4. Phase Prompts for Figma Generation (Copy-Paste Ready)

### Prompt 1 — File & Pages Initialization
```text
Create a new Figma design file named "Pathline Desktop".
Add pages: Foundations, Shell, Dashboard, Path Library, Accounts, Input Vault, System, Flows.
Do not create extra files. Use 1280x800 desktop viewport frames.
Do not include Templates, Runs, Settings, or Workflows as top-level app pages.
```

### Prompt 2 — Foundations Page
```text
On the Foundations page, generate color variables using dark slate background (#090d16), bright blue primary (#0a84ff), and slate border (#1e293b).
Create local components for: Button (default, secondary, outline, ghost, destructive), Input (text & search), Badge (status variants), Card, Tabs (Edit|Dial), Table, Dialog modal, and Sidebar navigation item.
Use auto-layout on all components.
```

### Prompt 3 — Shell Page
```text
On the Shell page, create a 1280x800 main application window.
Add a 240px left sidebar with 5 items: Dashboard, Path Library, Accounts, Input Vault, System.
Add a 48px top header bar with app title and SIP lab connection badge.
Create 5 state artboards showing the sidebar selection for each surface.
```

### Prompt 4 — Path Library Page
```text
On the Path Library page, design a master-detail split layout.
Left side (320px): Search bar, New Path button, list of Paths with readiness badges.
Right side: Path details header with sub-tabs for [ Edit Path ] and [ Dial & Execute ].
Inside the Edit tab: Phrase matching rows (When phrase -> Inject keypad).
Inside the Dial tab: Active call state, RTP audio meter, and real-time transcript log.
```

### Prompt 5 — Accounts & Vault Pages
```text
On Accounts page: Master-detail view. Left: list of profiles. Right: profile inputs table showing field name and binding type (Plain vs Vault Key selector).
On Input Vault page: Sealed secret inventory table with Key Name, Created Date, Bound Profiles, and Security Status. Include an 'Add Secret' modal dialog.
```

### Prompt 6 — Dashboard & System Pages
```text
On Dashboard: 3 top status cards (SIP, STT, Accounts), 4 quick action buttons, and Recent Call Activity log table.
On System: Telephony engine card, Whisper STT status card, and On-Device Security & Audit Ledger hash table.
```

### Prompt 7 — Flows & Handoff Page
```text
On Flows page: Connect prototype links for sidebar navigation, Path selection to Edit/Dial tabs, and Account secret selection to Vault modal.
Annotate frames with component names matching client/src/components/ui/*.
```

---

## 5. Handoff Mapping: Figma to React Codebase

| Figma Component / Frame | React Component File Path |
| :--- | :--- |
| **Shell Frame** | [`client/src/components/Shell.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/components/Shell.tsx) |
| **Sidebar** | [`client/src/components/AppSidebar.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/components/AppSidebar.tsx) |
| **Dashboard Surface** | [`client/src/pages/DashboardPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/DashboardPage.tsx) |
| **Path Library Surface** | [`client/src/pages/PathsPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/PathsPage.tsx) |
| **Path Edit Form** | [`client/src/pages/edit/EditForm.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/edit/EditForm.tsx) |
| **Path Dial Panel** | [`client/src/pages/RunPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/RunPage.tsx) |
| **Accounts Surface** | [`client/src/pages/AccountsPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/AccountsPage.tsx) |
| **Input Vault Surface** | [`client/src/pages/VaultPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/VaultPage.tsx) |
| **System Surface** | [`client/src/pages/SystemPage.tsx`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/pages/SystemPage.tsx) |
| **Design Tokens** | [`client/src/styles.css`](file:///Users/cameroncohen/Developer/projects/Pathline/client/src/styles.css) |
