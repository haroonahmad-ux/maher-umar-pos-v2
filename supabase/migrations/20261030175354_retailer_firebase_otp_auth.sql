-- Firebase-backed retailer identity and server-side OTP limits.
-- Existing POS tables and local SQLite business data are not modified.

ALTER TABLE public.retailer_accounts
  ADD COLUMN IF NOT EXISTS firebase_uid text,
  ADD COLUMN IF NOT EXISTS customer_name text;

CREATE UNIQUE INDEX IF NOT EXISTS retailer_accounts_firebase_uid_uq
  ON public.retailer_accounts(firebase_uid)
  WHERE firebase_uid IS NOT NULL;

CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA private TO service_role;

CREATE TABLE IF NOT EXISTS private.retailer_otp_limits (
  phone text PRIMARY KEY CHECK (phone ~ '^\+92[0-9]{10}$'),
  daily_date date NOT NULL DEFAULT (timezone('Asia/Karachi', now()))::date,
  daily_count integer NOT NULL DEFAULT 0 CHECK (daily_count >= 0),
  monthly_bucket date NOT NULL DEFAULT date_trunc('month', timezone('Asia/Karachi', now()))::date,
  monthly_count integer NOT NULL DEFAULT 0 CHECK (monthly_count >= 0),
  cooldown_until timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  pending_attempt_id uuid
);

ALTER TABLE private.retailer_otp_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON private.retailer_otp_limits FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON private.retailer_otp_limits TO service_role;

CREATE OR REPLACE FUNCTION private.reserve_retailer_otp(p_phone text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_row private.retailer_otp_limits%ROWTYPE;
  v_today date := (timezone('Asia/Karachi', now()))::date;
  v_month date := date_trunc('month', timezone('Asia/Karachi', now()))::date;
  v_attempt uuid := gen_random_uuid();
BEGIN
  IF p_phone IS NULL OR p_phone !~ '^\+92[0-9]{10}$' THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'invalid_phone');
  END IF;
  INSERT INTO private.retailer_otp_limits(phone, daily_date, monthly_bucket)
  VALUES (p_phone, v_today, v_month)
  ON CONFLICT (phone) DO NOTHING;
  SELECT * INTO v_row FROM private.retailer_otp_limits WHERE phone = p_phone FOR UPDATE;
  IF v_row.cooldown_until IS NOT NULL AND v_row.cooldown_until > now() THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'incorrect_otp_cooldown',
      'retry_after_seconds', GREATEST(1, CEIL(EXTRACT(EPOCH FROM (v_row.cooldown_until - now())))::integer));
  END IF;
  IF v_row.daily_date <> v_today THEN
    v_row.daily_count := 0;
    v_row.daily_date := v_today;
  END IF;
  IF v_row.monthly_bucket <> v_month THEN
    v_row.monthly_count := 0;
    v_row.monthly_bucket := v_month;
  END IF;
  IF v_row.monthly_count >= 4 THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'monthly_limit', 'limit', 4);
  END IF;
  IF v_row.daily_count >= 2 THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'daily_limit', 'limit', 2);
  END IF;
  UPDATE private.retailer_otp_limits
  SET daily_date = v_today,
      daily_count = v_row.daily_count + 1,
      monthly_bucket = v_month,
      monthly_count = v_row.monthly_count + 1,
      pending_attempt_id = v_attempt,
      updated_at = now()
  WHERE phone = p_phone;
  RETURN jsonb_build_object(
    'allowed', true,
    'attempt_id', v_attempt,
    'daily_remaining', 1 - v_row.daily_count,
    'monthly_remaining', 3 - v_row.monthly_count
  );
END;
$$;

CREATE OR REPLACE FUNCTION private.set_retailer_otp_cooldown(p_phone text, p_attempt_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_updated integer;
BEGIN
  UPDATE private.retailer_otp_limits
  SET cooldown_until = now() + interval '5 minutes',
      updated_at = now()
  WHERE phone = p_phone AND pending_attempt_id = p_attempt_id;
  GET DIAGNOSTICS v_updated = ROW_COUNT;
  RETURN v_updated = 1;
END;
$$;

CREATE OR REPLACE FUNCTION private.clear_retailer_otp_cooldown(p_phone text, p_attempt_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_updated integer;
BEGIN
  UPDATE private.retailer_otp_limits
  SET cooldown_until = NULL,
      pending_attempt_id = NULL,
      updated_at = now()
  WHERE phone = p_phone AND pending_attempt_id = p_attempt_id;
  GET DIAGNOSTICS v_updated = ROW_COUNT;
  RETURN v_updated = 1;
END;
$$;

CREATE OR REPLACE FUNCTION public.reserve_retailer_otp(p_phone text)
RETURNS jsonb
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$ SELECT private.reserve_retailer_otp(p_phone); $$;

CREATE OR REPLACE FUNCTION public.set_retailer_otp_cooldown(p_phone text, p_attempt_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$ SELECT private.set_retailer_otp_cooldown(p_phone, p_attempt_id); $$;

CREATE OR REPLACE FUNCTION public.clear_retailer_otp_cooldown(p_phone text, p_attempt_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY INVOKER
SET search_path = ''
AS $$ SELECT private.clear_retailer_otp_cooldown(p_phone, p_attempt_id); $$;

REVOKE ALL ON FUNCTION private.reserve_retailer_otp(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION private.set_retailer_otp_cooldown(text, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION private.clear_retailer_otp_cooldown(text, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION private.reserve_retailer_otp(text) TO service_role;
GRANT EXECUTE ON FUNCTION private.set_retailer_otp_cooldown(text, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION private.clear_retailer_otp_cooldown(text, uuid) TO service_role;

REVOKE ALL ON FUNCTION public.reserve_retailer_otp(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.set_retailer_otp_cooldown(text, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.clear_retailer_otp_cooldown(text, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_retailer_otp(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.set_retailer_otp_cooldown(text, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.clear_retailer_otp_cooldown(text, uuid) TO service_role;
