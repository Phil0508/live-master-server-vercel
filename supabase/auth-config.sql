-- Supabase Auth 설정 및 커스텀 JWT 클레임 구성
-- Live Master Server - 역할 기반 접근 제어를 위한 Auth 설정
-- 실행: Supabase Dashboard > Authentication > Settings에서 설정 또는 SQL 에디터에서 실행

-- ============================================
-- 1. AUTH 설정 (Dashboard에서 설정 권장, 여기선 참조용)
-- ============================================

/*
Supabase Dashboard > Authentication > Settings에서 다음 설정 적용:

Site URL: https://your-production-domain.vercel.app
Additional Redirect URLs:
  - http://localhost:3000 (Overlay)
  - http://localhost:3001 (Controller)
  - http://localhost:3002 (Roulette)
  - https://your-preview-deployment.vercel.app

JWT Expiry: 3600 (1시간)
Refresh Token Rotation: Enabled
Refresh Token Reuse Interval: 10초

Enable Signup: false (운영자만 계정 생성)
Enable Email Confirmations: true
Enable Phone Confirmations: false
Enable Anonymous Sign-ins: true (오버레이/뷰어용)

Email Provider: 활성화
SMTP 설정: Supabase 기본 또는 커스텀 SMTP
*/

-- ============================================
-- 2. 커스텀 JWT 클레임을 위한 데이터베이스 함수
-- ============================================

-- 사용자 메타데이터에서 역할 추출하여 JWT에 포함
-- Supabase Auth Hooks (PostgreSQL Functions) 사용

-- JWT 생성 시 호출되는 커스텀 클레임 함수
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
  claims jsonb;
  user_role text;
  user_permissions text[];
  user_metadata jsonb;
  app_metadata jsonb;
BEGIN
  -- 이벤트에서 클레임 추출
  claims := event -> 'claims';
  user_metadata := COALESCE(claims -> 'user_metadata', '{}'::jsonb);
  app_metadata := COALESCE(claims -> 'app_metadata', '{}'::jsonb);
  
  -- 역할 결정 로직
  -- 1. app_metadata.role이 있으면 우선 사용
  -- 2. user_metadata.role 확인
  -- 3. 이메일 도메인 기반 자동 할당
  -- 4. 기본값: 'viewer'
  
  user_role := COALESCE(
    app_metadata ->> 'role',
    user_metadata ->> 'role',
    CASE 
      WHEN claims ->> 'email' LIKE '%@admin.%' THEN 'admin'
      WHEN claims ->> 'email' LIKE '%@controller.%' THEN 'controller'
      WHEN claims ->> 'email' LIKE '%@overlay.%' THEN 'overlay'
      ELSE 'viewer'
    END
  );
  
  -- 권한 배열 구성
  user_permissions := COALESCE(
    (app_metadata -> 'permissions')::text[],
    (user_metadata -> 'permissions')::text[],
    CASE user_role
      WHEN 'admin' THEN ARRAY['*']
      WHEN 'controller' THEN ARRAY['players:write', 'rankings:write', 'donations:manage', 'matches:manage', 'roulette:manage', 'slots:manage', 'settings:write', 'snapshots:manage']
      WHEN 'overlay' THEN ARRAY['players:read', 'rankings:read', 'donations:read', 'matches:read', 'roulette:read', 'slots:read', 'reactions:read', 'settings:read']
      WHEN 'viewer' THEN ARRAY['players:read:top20', 'rankings:read:latest', 'donations:read:top20', 'matches:read:active', 'roulette:read:active', 'slots:read:active', 'reactions:read:active']
      ELSE ARRAY[]
    END
  );
  
  -- 클레임에 역할 및 권한 추가
  claims := jsonb_set(claims, '{role}', to_jsonb(user_role));
  claims := jsonb_set(claims, '{app_metadata}', jsonb_build_object(
    'role', user_role,
    'permissions', user_permissions
  ));
  
  -- 이벤트 업데이트
  RETURN jsonb_set(event, '{claims}', claims);
END;
$$;

-- ============================================
-- 3. 사용자 역할 관리 테이블 (관리자용)
-- ============================================

-- 사용자 역할 매핑 테이블 (Supabase Auth users 테이블과 연결)
CREATE TABLE IF NOT EXISTS public.user_roles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'controller', 'overlay', 'viewer')),
  permissions TEXT[] DEFAULT '{}',
  assigned_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE(user_id, role)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_active ON public.user_roles(is_active) WHERE is_active = TRUE;

-- RLS 활성화
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- 관리자만 사용자 역할 관리 가능
CREATE POLICY "admin_manage_user_roles" ON public.user_roles
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.user_roles ur
      WHERE ur.user_id = auth.uid() 
      AND ur.role = 'admin' 
      AND ur.is_active = TRUE
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.user_roles ur
      WHERE ur.user_id = auth.uid() 
      AND ur.role = 'admin' 
      AND ur.is_active = TRUE
    )
  );

-- 사용자 본인 역할 조회 가능
CREATE POLICY "user_read_own_roles" ON public.user_roles
  FOR SELECT USING (user_id = auth.uid());

-- ============================================
-- 4. JWT 클레임 동기화 트리거
-- ============================================

-- 사용자 역할 변경 시 JWT 갱신을 위한 트리거 함수
CREATE OR REPLACE FUNCTION public.sync_user_role_to_jwt()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  -- 역할이 변경되면 사용자의 다음 로그인/토큰 갱신 시 반영됨
  -- Supabase는 자동으로 JWT에 app_metadata 포함
  RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_sync_user_role
  AFTER INSERT OR UPDATE ON public.user_roles
  FOR EACH ROW EXECUTE FUNCTION public.sync_user_role_to_jwt();

-- ============================================
-- 5. 초기 관리자 계정 설정 함수
-- ============================================

-- 첫 번째 관리자 계정 생성 헬퍼 (Supabase Dashboard > SQL Editor에서 실행)
/*
-- 사용법:
-- 1. Supabase Dashboard > Authentication > Users에서 사용자 생성
-- 2. 아래 쿼리에서 USER_ID를 해당 사용자의 UUID로 변경 후 실행

INSERT INTO public.user_roles (user_id, role, permissions, assigned_by)
VALUES (
  'USER_UUID_HERE',  -- 생성된 사용자의 UUID
  'admin',
  ARRAY['*'],
  'USER_UUID_HERE'  -- 자기 자신으로 설정
)
ON CONFLICT (user_id, role) DO UPDATE SET
  permissions = EXCLUDED.permissions,
  is_active = TRUE,
  assigned_at = NOW();
*/

-- 컨트롤러 계정 추가 헬퍼
/*
INSERT INTO public.user_roles (user_id, role, permissions, assigned_by)
VALUES (
  'CONTROLLER_USER_UUID',
  'controller',
  ARRAY['players:write', 'rankings:write', 'donations:manage', 'matches:manage', 'roulette:manage', 'slots:manage', 'settings:write', 'snapshots:manage'],
  'ADMIN_USER_UUID'
)
ON CONFLICT (user_id, role) DO UPDATE SET
  permissions = EXCLUDED.permissions,
  is_active = TRUE,
  assigned_at = NOW();
*/

-- 오버레이 계정 추가 헬퍼
/*
INSERT INTO public.user_roles (user_id, role, permissions, assigned_by)
VALUES (
  'OVERLAY_USER_UUID',
  'overlay',
  ARRAY['players:read', 'rankings:read', 'donations:read', 'matches:read', 'roulette:read', 'slots:read', 'reactions:read', 'settings:read'],
  'ADMIN_USER_UUID'
)
ON CONFLICT (user_id, role) DO UPDATE SET
  permissions = EXCLUDED.permissions,
  is_active = TRUE,
  assigned_at = NOW();
*/

-- ============================================
-- 6. 익명 사용자(Anonymous) 역할 처리
-- ============================================

-- 익명 로그인 시 기본 역할 'viewer' 부여
-- Supabase는 익명 사용자에게도 JWT 발급 (role: 'anon')
-- 이를 우리 시스템의 'viewer' 역할로 매핑

-- JWT 훅에서 이미 처리됨 (custom_access_token_hook 함수)

-- ============================================
-- 7. Supabase Auth Hooks 등록 (Dashboard에서 설정)
-- ============================================

/*
Supabase Dashboard > Database > Functions에서 다음 설정:

1. custom_access_token_hook 함수를 "Auth Hook"으로 등록
   - Hook Type: "Custom Access Token Hook"
   - Function: public.custom_access_token_hook

또는 Supabase CLI로 설정:
supabase functions deploy custom-access-token-hook --project-ref YOUR_PROJECT_REF
*/

-- ============================================
-- 8. Row Level Security for auth.users (참조용)
-- ============================================

-- auth.users 테이블은 Supabase가 관리하므로 직접 정책 수정 불가
-- 대신 public.user_roles 테이블을 통해 역할 관리

-- ============================================
-- 9. 세션 관리 및 보안 설정
-- ============================================

-- 세션 타임아웃 설정 (Dashboard에서 설정)
/*
JWT Expiry: 3600 (1시간)
Refresh Token Rotation: Enabled
Refresh Token Reuse Interval: 10초
Session Timeout: 24시간 (Refresh Token 유효기간)
*/

-- ============================================
-- 10. 프로바이더 설정 (이메일/소셜)
-- ============================================

/*
Email Provider: 
  - Enable Signup: false (초대 기반)
  - Enable Confirmations: true
  - Double Confirm: false
  - Secure Email Change: true

Social Providers (선택사항):
  - Google: 관리자/컨트롤러 편의용
  - GitHub: 개발자용
  - Discord: 스트리머 커뮤니티용
*/

-- ============================================
-- 11. 이메일 템플릿 커스터마이징
-- ============================================

/*
Dashboard > Authentication > Email Templates에서 설정:

Confirm Signup:
  Subject: "[Live Master] 계정 인증 이메일"
  Body: 관리자가 초대했습니다. 링크를 클릭하여 계정을 활성화하세요.

Invite User:
  Subject: "[Live Master] 운영자 계정 초대"
  Body: 라이브 마스터 서버 운영자로 초대되었습니다. 비밀번호를 설정하세요.

Magic Link:
  Subject: "[Live Master] 로그인 링크"
  Body: 비밀번호 없이 로그인하세요.

Change Email:
  Subject: "[Live Master] 이메일 변경 확인"
  Body: 새 이메일 주소를 확인해주세요.

Reset Password:
  Subject: "[Live Master] 비밀번호 재설정"
  Body: 비밀번호를 재설정하려면 링크를 클릭하세요.
*/

-- ============================================
-- 12. Rate Limiting 및 보안 설정
-- ============================================

/*
Dashboard > Authentication > Settings > Rate Limits:

Email Signup: 3 requests/hour
Email Signin: 10 requests/hour
SMS Signup: 5 requests/hour
SMS Signin: 10 requests/hour
OAuth Signin: 20 requests/hour
Token Refresh: 100 requests/hour
*/

-- ============================================
-- 13. 테스트용 시드 데이터 (개발 환경만)
-- ============================================

-- 개발 환경에서만 실행 (app.environment = 'development')
DO $$
BEGIN
  IF current_setting('app.environment', true) = 'development' THEN
    -- 테스트용 사용자 역할 시드 (실제 auth.users ID로 교체 필요)
    -- INSERT INTO public.user_roles (user_id, role, permissions, assigned_by) VALUES
    --   ('00000000-0000-0000-0000-000000000001', 'admin', ARRAY['*'], '00000000-0000-0000-0000-000000000001'),
    --   ('00000000-0000-0000-0000-000000000002', 'controller', ARRAY['players:write', 'rankings:write', 'donations:manage'], '00000000-0000-0000-0000-000000000001'),
    --   ('00000000-0000-0000-0000-000000000003', 'overlay', ARRAY['players:read', 'rankings:read', 'donations:read'], '00000000-0000-0000-0000-000000000001')
    -- ON CONFLICT (user_id, role) DO NOTHING;
    RAISE NOTICE 'Development environment detected. Seed data skipped - add real user IDs manually.';
  END IF;
END $$;

-- ============================================
-- 14. 유틸리티 함수: 현재 사용자 역할 확인
-- ============================================

-- 현재 로그인한 사용자의 활성 역할 조회
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TABLE(role TEXT, permissions TEXT[], is_active BOOLEAN) LANGUAGE sql STABLE AS $$
  SELECT ur.role, ur.permissions, ur.is_active
  FROM public.user_roles ur
  WHERE ur.user_id = auth.uid()
  AND ur.is_active = TRUE
  AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
  ORDER BY 
    CASE ur.role 
      WHEN 'admin' THEN 1 
      WHEN 'controller' THEN 2 
      WHEN 'overlay' THEN 3 
      WHEN 'viewer' THEN 4 
      ELSE 5 
    END
  LIMIT 1;
$$;

-- 현재 사용자가 특정 역할을 가지고 있는지 확인
CREATE OR REPLACE FUNCTION public.has_role(target_role TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles ur
    WHERE ur.user_id = auth.uid()
    AND ur.role = target_role
    AND ur.is_active = TRUE
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
  );
$$;

-- 현재 사용자가 특정 권한을 가지고 있는지 확인
CREATE OR REPLACE FUNCTION public.has_permission(required_permission TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles ur
    WHERE ur.user_id = auth.uid()
    AND ur.is_active = TRUE
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    AND (
      ur.permissions @> ARRAY[required_permission]
      OR ur.permissions @> ARRAY['*']
    )
  );
$$;

-- ============================================
-- 15. 적용 완료 확인
-- ============================================

-- 함수 존재 확인
-- SELECT proname FROM pg_proc WHERE proname IN ('custom_access_token_hook', 'get_my_role', 'has_role', 'has_permission', 'sync_user_role_to_jwt');

-- 테이블 존재 확인
-- SELECT * FROM public.user_roles LIMIT 5;

-- RLS 정책 확인
-- SELECT * FROM pg_policies WHERE tablename = 'user_roles';

COMMENT ON TABLE public.user_roles IS '사용자 역할 매핑 - Supabase Auth users와 연결, JWT 커스텀 클레임 동기화용';
COMMENT ON FUNCTION public.custom_access_token_hook(jsonb) IS 'JWT 발급 시 커스텀 클레임(role, permissions) 주입 훅';
COMMENT ON FUNCTION public.get_my_role() IS '현재 로그인한 사용자의 활성 역할 및 권한 조회';
COMMENT ON FUNCTION public.has_role(text) IS '현재 사용자 역할 보유 여부 확인';
COMMENT ON FUNCTION public.has_permission(text) IS '현재 사용자 권한 보유 여부 확인';