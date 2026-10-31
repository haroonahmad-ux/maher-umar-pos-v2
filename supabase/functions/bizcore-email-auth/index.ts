import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

function reply(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), { status, headers: cors });
}
async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
}
async function emailExists(admin: ReturnType<typeof createClient>, email: string) {
  for (let page = 1; page <= 100; page++) {
    const { data, error } = await admin.auth.admin.listUsers({ page, perPage: 1000 });
    if (error) throw new Error("Account lookup is temporarily unavailable.");
    const users = data.users || [];
    if (users.some(user => String(user.email || "").toLowerCase() === email)) return true;
    if (users.length < 1000) return false;
  }
  throw new Error("Account directory is too large for this lookup. Contact support.");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return reply(405, { error: "Method not allowed" });
  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || Deno.env.get("SUPABASE_PUBLISHABLE_KEY");
  if (!url || !serviceKey || !anonKey) return reply(500, { error: "Email authentication is not configured." });
  const admin = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  try {
    const payload = await req.json();
    const email = String(payload.email || "").trim().toLowerCase();
    const purpose = String(payload.purpose || "");
    const name = String(payload.customer_name || "").trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return reply(400, { error: "Enter a valid email address." });
    if (!["signup", "login"].includes(purpose)) return reply(400, { error: "Invalid account action." });
    if (purpose === "signup" && (name.length < 2 || name.length > 60)) return reply(400, { error: "Retailer name must be 2–60 characters." });

    const ip = req.headers.get("cf-connecting-ip") || req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
    const ipHash = await sha256(ip + ":" + url);
    const since = new Date(Date.now() - 15 * 60 * 1000).toISOString();
    const { count, error: countError } = await admin.from("retailer_auth_attempts")
      .select("id", { count: "exact", head: true }).eq("ip_hash", ipHash).gte("created_at", since);
    if (countError) throw new Error("Request protection is temporarily unavailable.");
    if ((count || 0) >= 20) return reply(429, { error: "Too many email verification requests. Please try again later." });
    const { error: logError } = await admin.from("retailer_auth_attempts").insert({ ip_hash: ipHash });
    if (logError) throw new Error("Request protection is temporarily unavailable.");

    const exists = await emailExists(admin, email);
    if (purpose === "signup" && exists) {
      return reply(409, { error: "LOGIN_TO_EXISTING_ACCOUNT: This email is already registered. Login to Existing Account." });
    }
    if (purpose === "login" && !exists) {
      return reply(404, { error: "No account exists for this email. Please Create Account first." });
    }

    const authResponse = await fetch(url + "/auth/v1/otp", {
      method: "POST",
      headers: { "apikey": anonKey, "Authorization": "Bearer " + anonKey, "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        create_user: purpose === "signup",
        ...(purpose === "signup" ? { data: { account_type: "retailer", customer_name: name } } : {}),
      }),
    });
    const responseText = await authResponse.text();
    let responseBody: Record<string, unknown> = {};
    try { responseBody = JSON.parse(responseText); } catch { responseBody = { message: responseText.slice(0, 180) }; }
    if (!authResponse.ok) {
      const message = String(responseBody.msg || responseBody.message || responseBody.error_description || responseBody.error || "Email OTP could not be sent.");
      return reply(authResponse.status, { error: message });
    }
    return reply(200, { success: true, message: "Verification code sent." });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Email OTP request failed.";
    return reply(400, { error: message });
  }
});
