# 🏗️ Live Master Server — 리팩토링 마스터 플랜

> **레포**: [github.com/Phil0508/live-master-server-vercel](https://github.com/Phil0508/live-master-server-vercel)
> **배포 스택**: Vercel (Frontend Apps 호스팅) + Supabase (Postgres, Auth, Realtime, Edge Functions) + Cloudflare Workers(Hono, `apps/api`)
> **원본 레거시**: `server.py` (Flask, 2738줄) · `overlay.html` (2588줄) · `controller.html` (4506줄) — 저장소에서 이미 삭제되고 아래 Turborepo 모노레포로 마이그레이션이 진행 중
> 목표: 로직 없는 스파게티 코드를 프로급 엔진/컴포넌트 아키텍처로 전면 재설계
> 원칙: **방송 안정성 최우선** — 매 단계마다 롤백 가능해야 하며, 기능 변경 없는 순수 구조 개선부터 시작한다.

---

## 0. 현재 프로젝트 실제 구조 (Vercel + Supabase 기반)

저장소는 이미 Flask 모놀리식 구조에서 **Turborepo 모노레포**로 전환이 진행 중입니다.

```
live-master-server-vercel/  (Turborepo, npm workspaces)
├── apps/
│   ├── overlay/        # React + Vite + Framer Motion — 방송 송출 오버레이 (구 overlay.html 대체)
│   ├── controller/      # React + Vite + React Router + TanStack Query — 조종실 대시보드 (구 controller.html 대체)
│   ├── roulette/        # React + Vite — 독립 룰렛 앱 (package.json만 존재, src/ 비어있음 — 미착수)
│   └── api/             # Hono + Cloudflare Workers (wrangler) — 서버리스 API 레이어
├── packages/
│   ├── shared/          # 공통 타입(Zod), Supabase 자동생성 타입, 유틸 (@live-master/shared)
│   └── ui/              # 공통 React 컴포넌트, Tailwind (@live-master/ui)
├── supabase/
│   ├── schema.sql, policies.sql(RLS), seed.sql, auth-config.sql
│   ├── functions/       # Edge Functions: ranking-recalc(구현됨), leaderboard, reaction-upload,
│   │                    #   roulette-rig, roulette-spin, snapshot-create, webhook-toonation (스캐폴딩만 존재)
│   └── migrations/, seed/
├── .vercel/project.json # Vercel 프로젝트 연결 완료 (projectName: live-master-server-vercel)
└── turbo.json           # build/dev/lint/typecheck 파이프라인
```

**핵심 아키텍처 치환 매핑 (레거시 → 신규):**

| 구분 | 레거시(Flask) | 신규(Vercel+Supabase) |
|---|---|---|
| 상태 저장 | SQLite/전역 dict `MEMORY_STATE` | Supabase Postgres (`players`, `rankings`, `donations`, `snapshots` 등 테이블) |
| 실시간 통신 | 커스텀 SSE(`/api/stream`, `broadcast_event`) | **Supabase Realtime** (Postgres 변경 감지 + `channel().send()` 브로드캐스트) |
| 비즈니스 로직 | Flask 라우트 함수 내 인라인 | **Supabase Edge Functions** (Deno) — `ranking-recalc`가 이미 구현된 참조 사례 |
| 프론트 상태관리 | 없음(인라인 DOM 조작 추정) | **Zustand** 스토어(`overlayStore.ts`) + React 컴포넌트 트리 |
| 인증 | 세션 쿠키 + 하드코딩 비밀번호 | **Supabase Auth** (익명/이메일, JWT 커스텀 클레임, RLS 정책) |
| 배포 | 로컬 PC/PyInstaller GUI 실행 | **Vercel**(프론트 서버리스 호스팅) + **Supabase**(DB/Realtime/Edge Functions) + **Cloudflare Workers**(경량 API) |

따라서 이 문서의 이후 섹션은 **"레거시 문제를 진단하되, 해법은 이미 선택된 Vercel+Supabase 스택 위에서 어떻게 구현할지"**를 기준으로 서술합니다. 순수 Flask 클래스 설계(`StateStore`, `EventBus` 등)는 **Supabase Edge Functions + Realtime 채널 + Postgres 트리거**로 치환해 적용합니다.

---

## 1. 코드베이스 구조 분석 — 레거시 통신 아귀 및 취약점

### 1-1. 레거시 데이터 흐름 (마이그레이션 대상 원본)

```
controller.html (관리자 조종실)
        │  POST /api/data, /api/donation, /api/roulette/winner ...
        ▼
server.py — 전역 MEMORY_STATE(dict) 단일 진실 공급원
        │  save_data() → SQLite(로컬) / PostgreSQL(Supabase, Vercel)
        │  broadcast_event('update', state)  ← 이벤트명이 사실상 하나뿐
        ▼
SSE 채널 (/api/stream, sse_clients 리스트)
        │
        ├──▶ overlay.html  (방송 송출 화면, EventSource로 구독)
        └──▶ controller.html (자기 자신도 되받아 재수신 → 자기 UI 갱신)
```

핵심 상태는 `DEFAULT_STATE`(server.py L271-312)에 정의된 통짜 dict 하나로, 랭킹(`bjs`), 번외게임(`extra_bjs`), 매치(`match_data`), 룰렛(`roulette`), 슬롯머신(`slot_machine`), 후원대기함(`pending_donations`) 등 완전히 이질적인 도메인이 **하나의 딕셔너리, 하나의 락, 하나의 이벤트**로 뭉쳐 있었다.

### 1-2. 레거시 핵심 API 라우트 맵 (기능별 분류)

| 도메인 | 라우트 | 문제 요약 |
|--------|--------|-----------|
| 상태 동기화 | `GET/POST /api/data` | 전체 state를 통째로 주고받음. `version` 필드로 낙관적 잠금만 하고 필드 단위 병합 없음 |
| 후원 처리 | `POST /api/donation` | `receive_donation()` 한 함수가 187줄: 파싱→중복체크→슬롯머신 판정→DB기록→리액션 매칭→브로드캐스트까지 전부 하드코딩 |
| SSE 스트림 | `GET /api/stream` | 이벤트 타입 구분 없이 `update` 하나만 존재. 클라이언트가 "무엇이 바뀌었는지" 알 수 없음 |
| 룰렛 | `POST /api/roulette/winner` | 승자 확정 로직이 라우트 함수 안에 인라인, 조작(rig) 각도 계산 로직은 프론트 전담으로 추정 |
| 슬롯머신 | (`receive_donation` 내부에 내장) | 독립 엔드포인트조차 없이 후원 라우트에 조건문으로 끼워넣어짐 |
| 번외게임 | `/api/extra_game/{start,end,cancel}` | 상태 전환 로직 중복 (3개 라우트가 비슷한 초기화 코드 반복) |
| 스냅샷/타임머신 | `/api/snapshots/*`, `/api/time_machine/restore_by_time` | DB 직접 쿼리가 라우트에 인라인, 서비스 레이어 없음 |
| 방송 시작/종료 | `/api/server/{start_broadcast,end_broadcast,reset}` | kv_store 키 화이트리스트를 하드코딩된 튜플로 라우트마다 중복 작성 |
| 인증 | `before_request require_login()` | `public_routes` 하드코딩 배열로 관리 — 신규 라우트 추가 시 누락 위험 |

### 1-3. 핵심 취약점 요약 (신규 스택에서 반드시 회피해야 할 패턴)

1. **전역 뮤터블 dict + 단일 스레드락** — 서버리스 다중 인스턴스 환경에서 무의미. → **신규**: Postgres row 단위 UPDATE + RLS로 대체, 락은 DB 트랜잭션에 위임.
2. **이중 신뢰 캐시 문제** — 메모리 캐시와 DB를 뒤섞어 신뢰. → **신규**: Supabase가 유일한 소스, 클라이언트는 Realtime 구독으로만 갱신, 로컬 캐시 없음(Zustand는 파생 상태만 보관).
3. **라우트 함수 = 비즈니스 로직 그 자체** — 서비스/엔진 계층 부재. → **신규**: Edge Functions가 이 역할(예: `ranking-recalc`)을 전담, 각 Function은 단일 책임.
4. **SSE 이벤트 단일화** — `update` 하나로 뭉쳐 전체 리렌더링 유발. → **신규**: Supabase Realtime의 `postgres_changes` + `broadcast` 채널을 테이블/도메인별로 세분화 구독 (`ranking-updates`, `roulette-updates` 등 채널 분리 — `ranking-recalc` Edge Function이 이미 `ranking-updates` 채널로 분리 발행 중).
5. **상태 머신 부재** — bool 플래그 + 타임스탬프로만 관리. → **신규**: Postgres 테이블 컬럼 + CHECK 제약조건으로 상태 전이를 스키마 레벨에서 강제.
6. **프론트 DOM 직접 조작과 상태 갱신 혼재** — React+Zustand 도입으로 원천 해결되나, 컴포넌트가 스토어 구독 규율을 지키지 않으면 동일 문제가 재발할 수 있음(3장 가이드라인 참고).

---

## 2. 백엔드 로직 분리 설계 — Supabase Edge Functions + Cloudflare Workers(Hono)

레거시의 `LiveGameEngine`/`ScoreManager`/`BgmController`/`EffectManager` 같은 클래스 분리 요구를, **서버리스 스택에 맞는 "함수 단위 도메인 서비스"**로 치환합니다. Flask처럼 하나의 프로세스에 다 때려박는 대신, 각 도메인을 **독립 배포 가능한 Edge Function 또는 Worker 라우트**로 쪼갭니다.

### 2-1. 계층 구조

```
supabase/functions/               # Deno Edge Functions — DB에 가까운 무거운 연산/트랜잭션
├── ranking-recalc/               # ✅ 구현됨 — ScoreManager 역할 (점수/배지/랭킹 재계산 + ranking-updates 채널 발행)
├── roulette-spin/                # ⏳ 스캐폴딩 — RouletteEngine 역할 (가중치 계산, 스핀 시작)
├── roulette-rig/                 # ⏳ 스캐폴딩 — RouletteEngine의 선관위 조작 콘솔 전용 (rig_target_angle 계산)
├── snapshot-create/              # ⏳ 스캐폴딩 — 타임머신 스냅샷 생성/복원
├── reaction-upload/              # ⏳ 스캐폴딩 — 리액션 파일 업로드 + Storage 연동
├── webhook-toonation/            # ⏳ 스캐폴딩 — DonationProcessor 역할 (외부 후원 웹훅 수신 + 파싱 + 매칭)
└── leaderboard/                  # ⏳ 스캐폴딩 — 공개 랭킹 조회 (읽기 전용, RLS로 익명 접근 허용)

apps/api/  (Hono + Cloudflare Workers)
└── src/
    ├── routes/
    │   ├── slot-machine.ts       # SlotMachineEngine 역할 — 상태 정규화, 후보 추첨, 결과 커밋
    │   ├── bgm.ts                 # BgmController 역할 — YouTube/로컬 오디오 재생·볼륨 통제 (경량 상태이므로 Worker가 적합)
    │   └── effects.ts             # EffectManager 역할 — 네온/피버타임/전광판 트리거
    └── index.ts                   # Hono 앱 진입점, 라우트 등록만 담당
```

**역할 분담 원칙:**
- **DB 트랜잭션이 무겁고 정합성이 중요한 도메인(랭킹 재계산, 후원 처리, 스냅샷)** → Supabase Edge Function. DB와 물리적으로 가까워 지연시간이 짧고, `supabase-js` 서비스 롤 키로 RLS를 우회한 안전한 쓰기가 가능.
- **상태가 가볍고 응답속도가 중요한 도메인(슬롯머신 애니메이션 트리거, BGM 컨트롤, 이펙트 스위치)** → Cloudflare Workers(Hono). 콜드스타트가 사실상 없고 전세계 엣지에서 즉시 응답.

### 2-2. 참조 구현 패턴 (이미 존재하는 `ranking-recalc` 기준)

`supabase/functions/ranking-recalc/index.ts`는 이미 다음 패턴을 구현했으며, 이를 다른 모든 Edge Function의 표준 템플릿으로 삼습니다:

```typescript
// 표준 패턴 요약 (ranking-recalc 참고)
serve(async (req) => {
  // 1. CORS + 메서드 검증
  // 2. Service Role Key로 Supabase 클라이언트 생성 (RLS 우회, 서버 신뢰 영역)
  // 3. 요청 본문 파싱 (trigger 종류, 대상 ID 등)
  // 4. JWT에서 사용자/역할 추출 (감사 로그용)
  // 5. 핵심 비즈니스 로직 수행 (예: recalculateRankings)
  // 6. audit_logs 테이블에 감사 로그 기록
  // 7. supabase.channel('ranking-updates').send({ type: 'broadcast', event: 'ranking:update', payload }) 로 세분화 이벤트 발행
  // 8. 응답 반환
});
```

**앞으로 만들 각 Function도 동일 골격을 따른다:**
- `roulette-spin`: `players` 테이블 기여도 기준 가중치 계산 → `roulette-updates` 채널로 `roulette:spin` 이벤트 발행
- `roulette-rig`: 컨트롤러의 "선관위 조작 콘솔"에서 타깃 지정 시 호출 → 목표 각도 계산 후 `roulette:spin`에 `targetAngle` 포함해 재발행
- `webhook-toonation`: 투네이션 웹훅 수신 → 이름/메시지 파싱(레거시 `receive_donation`의 콜론 파싱 로직 이관) → `donations` 테이블 insert → `donation-updates` 채널 발행
- `snapshot-create`: 수동/자동 스냅샷 생성, `snapshots` 테이블에 현재 랭킹/매치/후원 상태 JSON 스냅샷 저장

### 2-3. Cloudflare Workers(Hono) 라우트 설계 — `apps/api`

```typescript
// apps/api/src/index.ts
import { Hono } from 'hono'
import { slotMachineRoutes } from './routes/slot-machine'
import { bgmRoutes } from './routes/bgm'
import { effectsRoutes } from './routes/effects'

const app = new Hono()
app.route('/slot', slotMachineRoutes)   // SlotMachineEngine
app.route('/bgm', bgmRoutes)             // BgmController
app.route('/effects', effectsRoutes)     // EffectManager

export default app
```

```typescript
// apps/api/src/routes/slot-machine.ts
export const slotMachineRoutes = new Hono()
  .post('/normalize', async (c) => { /* normalize_slot_machine_state 이관 */ })
  .post('/draw', async (c) => { /* get_slot_reaction_candidate 이관 */ })
  .post('/apply-result', async (c) => { /* apply_slot_score 이관 + supabase Realtime broadcast */ })
```

이렇게 하면 레거시가 요구했던 "독립적인 전역 객체/클래스 단위 모듈화"가 **서버리스 환경에서는 독립 배포 가능한 함수/라우트 단위 모듈화**로 자연스럽게 치환됩니다.

---

## 3. 프론트엔드(overlay/controller) 전역 상태 관리 설계

### 3-1. 원칙

> **"Supabase Realtime 이벤트 수신 → Zustand 스토어 갱신 → 구독 컴포넌트만 리렌더"** 단방향 파이프라인을 강제한다.
> DOM 조작은 React가 대신하므로, 규율의 핵심은 **"컴포넌트가 필요한 스토어 슬라이스만 selector로 구독하고, 렌더링 로직과 실시간 이벤트 처리 로직을 파일 단위로 분리하는 것"**이다.

### 3-2. 현재 구조 확인 및 강화 방향

`apps/overlay/src/stores/overlayStore.ts`는 이미 아래 골격을 갖추고 있다:

```typescript
export const useOverlayStore = create<OverlayState>()(
  devtools(persist((set, get) => ({
    rankingData: null,
    updateRanking: (data) => set({ rankingData: data }),
    handleNewDonation: (donation) => { /* 점수 갱신 + 정렬 + 랭킹 재계산 */ },
    handleRouletteEvent: (event) => { /* type별 분기 */ },
    triggerScoreAnimation: (playerId, type) => { /* setTimeout으로 idle 복귀 */ },
    ...
  })))
)
```

**강화가 필요한 지점:**

1. **`handleNewDonation`의 랭킹 재계산 로직이 클라이언트에 중복 구현되어 있다.** 이는 이미 Edge Function `ranking-recalc`가 서버에서 수행하는 작업과 동일하다. → **원칙**: 클라이언트는 서버가 계산한 결과(Realtime으로 수신한 `ranking:update` payload)를 **그대로 반영만** 하고, 클라이언트 사이드 재계산 로직은 제거한다. (낙관적 업데이트가 필요한 경우에만 예외적으로 임시 로컬 계산 후 서버 응답 도착 시 덮어쓰기)
2. **Realtime 구독 초기화 코드가 아직 없다.** `lib/supabase.ts`에 클라이언트만 있고, `overlayStore`와 연결하는 `useRealtimeSubscription` 훅이 필요하다.

```typescript
// apps/overlay/src/hooks/useRealtimeSync.ts (신규 작성 대상)
export function useRealtimeSync() {
  const { updateRanking, handleRouletteEvent, updateMatch, updateSlotMachine, showVIPCard } = useOverlayStore()

  useEffect(() => {
    const rankingChannel = supabase.channel('ranking-updates')
      .on('broadcast', { event: 'ranking:update' }, ({ payload }) => updateRanking(payload))
      .subscribe()

    const rouletteChannel = supabase.channel('roulette-updates')
      .on('broadcast', { event: 'roulette:spin' }, ({ payload }) => handleRouletteEvent({ type: 'roulette:spin', payload }))
      .on('broadcast', { event: 'roulette:result' }, ({ payload }) => handleRouletteEvent({ type: 'roulette:result', payload }))
      .subscribe()

    const matchChannel = supabase.channel('match-updates')
      .on('broadcast', { event: 'match:update' }, ({ payload }) => updateMatch(payload))
      .subscribe()

    // slot-updates, donation-updates 채널도 동일 패턴으로 추가

    return () => {
      supabase.removeChannel(rankingChannel)
      supabase.removeChannel(rouletteChannel)
      supabase.removeChannel(matchChannel)
    }
  }, [])
}
```

이 훅을 `App.tsx` 최상단에서 한 번만 호출하면, 레거시의 `EventSource('/api/stream')` + `onmessage` 핸들러 전체를 대체한다.

### 3-3. 컴포넌트 구독 가이드라인

1. **컴포넌트는 필요한 슬라이스만 selector로 구독한다.**
   ```typescript
   // ❌ 전체 스토어 구독 — 관련 없는 상태 변화에도 리렌더
   const store = useOverlayStore()
   // ✅ 필요한 슬라이스만 구독
   const rankingData = useOverlayStore((s) => s.rankingData)
   ```
2. **실시간 이벤트 처리(`useRealtimeSync`)와 렌더링(컴포넌트 JSX)은 파일이 분리되어야 한다.** `RankingContainer.tsx`는 오직 `rankingData`를 받아 그리기만 하고, 데이터가 어떻게 갱신되는지는 몰라야 한다. (이미 `RankingContainer.tsx` 구조가 이 원칙을 잘 따르고 있음 — 유지)
3. **애니메이션 트리거(스파크, 바운스, 피버타임 불꽃)는 상태 변화의 부산물로 별도 처리한다.** 현재 `overlayStore.triggerScoreAnimation()`이 이 역할을 하고 있으나, `handleNewDonation` 내부에서 직접 호출하지 말고, **서버의 `ranking:update` payload에 "변경된 playerId 목록"을 포함시켜** 클라이언트가 diff 계산 없이 바로 트리거할 수 있도록 서버-클라이언트 계약을 명확히 한다.
4. **낙관적 업데이트는 Controller 앱에서만 사용한다.** Overlay는 순수 표시 전용이므로 항상 서버 확정 값만 반영(안정성 우선). Controller는 매니저의 버튼 클릭 반응성을 위해 `store.patch()` 후 API 호출 → 실패 시 롤백 패턴을 사용한다.

---

## 4. 안전한 단계별 실행 계획 (Vercel + Supabase 기준)

> 원칙: 매 단계는 **기존 배포를 깨뜨리지 않는 점진적 추가**부터 시작한다. Vercel Preview Deployment를 적극 활용해 프로덕션 영향 없이 검증 후 병합한다.

| 단계 | 작업 내용 | 검증 방법 | 롤백 전략 |
|---|---|---|---|
| **0. 기준선 확보** | 현재 `main` 브랜치를 `git tag pre-refactor-v2`로 고정. Supabase 프로덕션 DB 스냅샷(pg_dump) 1회 확보 | 태그/백업 존재 확인 | 태그 체크아웃 + DB 스냅샷 복원 |
| **1. Edge Function 표준 템플릿 확정** | `ranking-recalc` 패턴을 그대로 복제하여 `roulette-spin`, `roulette-rig`, `webhook-toonation`, `snapshot-create` 뼈대 작성 (로직은 TODO로 비워둠) | `supabase functions serve`로 로컬 실행, 빈 응답 200 확인 | 함수 파일 삭제만으로 원복 |
| **2. DonationProcessor → webhook-toonation 이관** | 레거시 `receive_donation()`의 이름/메시지 파싱, tx_id 중복 체크, 리액션 매칭 로직을 Edge Function으로 이식 | 후원 시뮬레이션 payload로 로컬 테스트, 결과가 레거시와 동일한지 회귀 검증 | 함수 배포 취소(`supabase functions delete`) |
| **3. RouletteEngine → roulette-spin/roulette-rig 구현** | 가중치 계산 + 선관위 조작 각도 산출 로직 구현, `roulette-updates` 채널 발행 | 컨트롤러 개발 환경에서 수동 스핀 테스트 | Vercel Preview에서만 테스트 후 병합 보류 가능 |
| **4. SlotMachineEngine, BgmController, EffectManager → apps/api(Hono) 구현** | 경량 상태 관리 라우트 작성, wrangler로 Cloudflare Workers 배포 | `wrangler dev` 로컬 테스트 + Postman/curl 회귀 테스트 | Workers 배포 롤백(`wrangler rollback`) |
| **5. `useRealtimeSync` 훅 작성 및 Overlay 연결** | Overlay `App.tsx`에 Realtime 구독 훅 연결, 기존 데모/목업 데이터 제거 | 로컬에서 Supabase Realtime 채널에 테스트 이벤트 발행 → Overlay 화면 갱신 확인 | 훅 호출 제거로 즉시 원복 |
| **6. Controller에서 낙관적 업데이트 + Edge Function 호출 연결** | 후원 대기함, 룰렛 리모컨, 선관위 조작 콘솔 UI에서 각 Edge Function/Worker 호출 연결 | 매니저 시나리오 수동 리허설 | 컴포넌트 단위 커밋이므로 개별 revert |
| **7. Roulette 독립 앱 완성 및 임베드 모드** | `apps/roulette` 스캐폴딩 완료, 실제 컴포넌트 구현 + `?embed=true` 모드 | Vercel Preview URL로 독립 접속 테스트 | 별도 앱이므로 배포 격리 |
| **8. Vercel 프로덕션 배포 파이프라인 확정** | `apps/overlay`, `apps/controller`, `apps/roulette` 각각 Vercel 프로젝트로 연결, 환경변수(`VITE_SUPABASE_URL` 등) 설정 | 각 앱 Preview → Production 승격 후 스모크 테스트 | Vercel Instant Rollback 기능 사용 |
| **9. 레거시 완전 제거 확인** | `server.py`, `overlay.html`, `controller.html` 등이 저장소에서 완전히 사라졌는지 최종 확인(이미 삭제됨), README/문서 갱신 | `git log --all -- server.py` 등으로 이력만 남고 워킹 트리엔 없음 확인 | 필요 시 git 이력에서 복원 가능 |
| **10. 모니터링/감사 로그 정착** | Supabase `audit_logs` 테이블 기반 대시보드, Vercel Analytics, Edge Function 에러 로그 알림 연동 | 실제 방송 1회 리허설로 전체 파이프라인 종단 테스트 | 문제 발생 시 이전 Vercel 배포로 즉시 롤백 |

### 리스크 관리 수칙

- **Edge Function/Worker는 기능 단위로 독립 배포**되므로, 하나가 실패해도 다른 도메인(랭킹, 룰렛 등)에 영향을 주지 않는다 — 이 격리성이 서버리스 아키텍처의 핵심 안전장치다.
- **Realtime 채널은 도메인별로 분리**하고(`ranking-updates`, `roulette-updates`, `match-updates`, `slot-updates`, `donation-updates`), 절대 레거시처럼 하나의 `update` 채널로 합치지 않는다.
- **Vercel Preview Deployment를 항상 우선 사용**한다 — 프로덕션에 영향 없이 실제 URL로 검증 후 병합.
- 매 단계 종료 시 Supabase `snapshot-create` Function으로 실제 운영 데이터 스냅샷을 생성해, 데이터 손실 없이 되돌릴 수 있는 안전장치를 확보한다.
- 배포는 항상 방송이 없는 시간대에만 수행하고, 배포 직후 최소 1회 이상 실사용 시나리오로 확인한다.