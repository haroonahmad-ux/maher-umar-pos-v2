import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};
const FIREBASE_WEB_API_KEY = "AIzaSyA7xAVZcaXI2k1Rpv-4vc0g7mDTKW0fRgE";

function reply(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), { status, headers: cors });
}
async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
}
function normalizePhone(value: unknown): string {
  const raw = String(value ?? "").replace(/[\s()-]/g, "");
  if (/^03[0-9]{9}$/.test(raw)) return "+92" + raw.slice(1);
  if (/^3[0-9]{9}$/.test(raw)) return "+92" + raw;
  if (/^\+923[0-9]{9}$/.test(raw)) return raw;
  if (/^923[0-9]{9}$/.test(raw)) return "+" + raw;
  throw new Error("Enter a valid Pakistani mobile number.");
}
function syntheticEmail(phone: string) {
  return phone.replace(/\D/g, "") + "@retailer.maherumar.invalid";
}
async function verifyFirebasePhone(idToken: string, expectedPhone: string) {
  if (!idToken || idToken.length < 100) throw new Error("Firebase phone verification is required.");
  const response = await fetch(
    "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" + FIREBASE_WEB_API_KEY,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ idToken }) },
  );
  if (!response.ok) throw new Error("Firebase could not validate the phone verification. Please verify the OTP again.");
  const payload = await response.json();
  const user = payload.users?.[0];
  if (!user?.localId || user.phoneNumber !== expectedPhone) {
    throw new Error("Verified Firebase phone number does not match this account.");
  }
  return { uid: String(user.localId), phone: String(user.phoneNumber) };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return reply(405, { error: "Method not allowed" });

  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !serviceKey) return reply(500, { error: "Authentication service is not configured." });

  const admin = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  try {
    const payload = await req.json();
    const action = String(payload.action || "");
    const phone = normalizePhone(payload.phone);
    const password = String(payload.password || "");
    const name = String(payload.customer_name || "").trim();
    const attemptId = String(payload.attempt_id || "");

    const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
    const ipHash = await sha256(forwarded + ":" + url);
    const since = new Date(Date.now() - 15 * 60 * 1000).toISOString();
    const { count, error: countError } = await admin.from("retailer_auth_attempts")
      .select("id", { count: "exact", head: true }).eq("ip_hash", ipHash).gte("created_at", since);
    if (countError) throw new Error("Rate-limit check unavailable.");
    if ((count || 0) >= 30) return reply(429, { error: "Too many authentication attempts. Try again later." });
    const { error: logError } = await admin.from("retailer_auth_attempts").insert({ ip_hash: ipHash });
    if (logError) throw new Error("Rate-limit logging unavailable.");

    if (action === "request_otp") {
      const purpose = String(payload.purpose || "");
      if (!["signup", "login"].includes(purpose)) return reply(400, { error: "Invalid authentication purpose." });
      if (password.length < 6 || password.length > 72) return reply(400, { error: "Password must be 6–72 characters." });

      const { data: account, error: lookupError } = await admin.from("retailer_accounts")
        .select("user_id,phone").eq("phone", phone).maybeSingle();
      if (lookupError) throw new Error("Account lookup failed.");

      if (purpose === "signup") {
        if (name.length < 2 || name.length > 60) return reply(400, { error: "Name must be 2–60 characters." });
        if (account) return reply(409, { error: "This mobile number is already registered. Please use Login." });
      } else {
        if (!account) return reply(401, { error: "Mobile number or password is incorrect." });
        const { error: passwordError } = await admin.auth.signInWithPassword({
          email: syntheticEmail(phone), password,
        });
        if (passwordError) return reply(401, { error: "Mobile number or password is incorrect." });
      }

      const { data: quota, error: quotaError } = await admin.rpc("reserve_retailer_otp", { p_phone: phone });
      if (quotaError) throw new Error("OTP quota service unavailable.");
      if (!quota?.allowed) {
        const reason = String(quota?.reason || "limit");
        const messages: Record<string, string> = {
          daily_limit: "Daily OTP limit reached. Maximum 2 OTP requests are allowed per Pakistan calendar day.",
          monthly_limit: "Monthly OTP limit reached. Maximum 4 OTP requests are allowed per calendar month.",
          incorrect_otp_cooldown: "Incorrect OTP entered. Please wait 5 minutes before requesting another OTP.",
          invalid_phone: "Invalid mobile number.",
        };
        return reply(429, { error: messages[reason] || "OTP request is temporarily blocked.", retry_after_seconds: quota?.retry_after_seconds });
      }
      return reply(200, { allowed: true, attempt_id: quota.attempt_id, daily_remaining: quota.daily_remaining, monthly_remaining: quota.monthly_remaining });
    }

    if (action === "record_otp_failure") {
      if (!attemptId) return reply(400, { error: "OTP attempt reference is missing." });
      const { data, error } = await admin.rpc("set_retailer_otp_cooldown", { p_phone: phone, p_attempt_id: attemptId });
      if (error) throw new Error("Could not record OTP failure.");
      return data ? reply(200, { cooldown_seconds: 300 }) : reply(409, { error: "OTP attempt is no longer active." });
    }

    if (action === "complete_signup" || action === "complete_login") {
      if (!attemptId) return reply(400, { error: "OTP attempt reference is missing." });
      if (password.length < 6 || password.length > 72) return reply(400, { error: "Password must be 6–72 characters." });
      const firebase = await verifyFirebasePhone(String(payload.firebase_id_token || ""), phone);

      if (action === "complete_signup") {
        if (name.length < 2 || name.length > 60) return reply(400, { error: "Name must be 2–60 characters." });
        const { data: existing, error: existingError } = await admin.from("retailer_accounts")
          .select("user_id").eq("phone", phone).maybeSingle();
        if (existingError) throw new Error("Account lookup failed.");
        if (existing) return reply(409, { error: "This mobile number is already registered. Please use Login." });

        const email = syntheticEmail(phone);
        const { data: created, error: createError } = await admin.auth.admin.createUser({
          email, password, email_confirm: true,
          user_metadata: { account_type: "retailer", customer_name: name },
        });
        if (createError || !created.user) return reply(400, { error: createError?.message || "Account could not be created." });

        const { error: insertError } = await admin.from("retailer_accounts").insert({
          user_id: created.user.id,
          username: phone.replace(/\D/g, ""),
          customer_name: name,
          phone,
          phone_verified: true,
          firebase_uid: firebase.uid,
        });
        if (insertError) {
          await admin.auth.admin.deleteUser(created.user.id);
          return reply(409, { error: "This mobile number or Firebase identity is already registered." });
        }
        await admin.rpc("clear_retailer_otp_cooldown", { p_phone: phone, p_attempt_id: attemptId });
        return reply(200, { success: true, firebase_uid: firebase.uid, customer_name: name, phone });
      }

      const { data: account, error: accountError } = await admin.from("retailer_accounts")
        .select("user_id,username,customer_name,phone,firebase_uid")
        .eq("phone", phone).maybeSingle();
      if (accountError) throw new Error("Account lookup failed.");
      if (!account) return reply(401, { error: "Mobile number or password is incorrect." });
      if (account.firebase_uid && account.firebase_uid !== firebase.uid) {
        return reply(403, { error: "This mobile number is linked to a different verified account." });
      }
      const { error: passwordError } = await admin.auth.signInWithPassword({
        email: syntheticEmail(phone), password,
      });
      if (passwordError) return reply(401, { error: "Mobile number or password is incorrect." });
      if (!account.firebase_uid) {
        const { error: linkError } = await admin.from("retailer_accounts")
          .update({ firebase_uid: firebase.uid, phone_verified: true })
          .eq("user_id", account.user_id).is("firebase_uid", null);
        if (linkError) throw new Error("Could not link verified phone identity.");
      }
      await admin.rpc("clear_retailer_otp_cooldown", { p_phone: phone, p_attempt_id: attemptId });
      return reply(200, { success: true, firebase_uid: firebase.uid, customer_name: account.customer_name || account.username, phone });
    }

    return reply(400, { error: "Unsupported authentication action." });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Authentication request failed.";
    console.error("retailer-auth error:", message);
    return reply(400, { error: message });
  }
});
