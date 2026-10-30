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

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return reply(405, { error: "Method not allowed" });

  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !serviceKey) return reply(500, { error: "Authentication service is not configured" });

  const admin = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  try {
    const payload = await req.json();
    const action = String(payload.action || "");
    const username = String(payload.username || "").trim().toLowerCase();
    const password = String(payload.password || "");
    let phone = String(payload.phone || "").replace(/[\s()-]/g, "");

    if (!["signup", "login"].includes(action)) return reply(400, { error: "Invalid action" });
    if (!/^[a-z0-9_]{4,24}$/.test(username)) return reply(400, { error: "Username must be 4–24 letters, numbers or underscores" });
    if (password.length < 12 || password.length > 128 ||
        !/[A-Z]/.test(password) || !/[a-z]/.test(password) ||
        !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      return reply(400, { error: "Use a 12+ character password with uppercase, lowercase, number and symbol" });
    }

    const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
    const ipHash = await sha256(forwarded + ":" + (Deno.env.get("SUPABASE_DB_URL") || url));
    const since = new Date(Date.now() - 15 * 60 * 1000).toISOString();
    const { count, error: countError } = await admin.from("retailer_auth_attempts")
      .select("id", { count: "exact", head: true }).eq("ip_hash", ipHash).gte("created_at", since);
    if (countError) throw new Error("Rate-limit check unavailable");
    if ((count || 0) >= 30) return reply(429, { error: "Too many attempts. Please try again later." });
    const { error: logError } = await admin.from("retailer_auth_attempts").insert({ ip_hash: ipHash });
    if (logError) throw new Error("Rate-limit logging unavailable");

    // Synthetic internal email keeps Supabase Auth credentials private and avoids
    // falsely marking the retailer's phone number as verified.
    const authEmail = username + "@retailer.maherumar.invalid";

    if (action === "signup") {
      if (!/^\+92[0-9]{10}$/.test(phone)) return reply(400, { error: "Enter a valid Pakistani mobile number" });
      const { data: existing } = await admin.from("retailer_accounts")
        .select("user_id").or("username.eq." + username + ",phone.eq." + phone).limit(1);
      if (existing && existing.length) return reply(409, { error: "Username or mobile number is already registered" });

      const { data: created, error: createError } = await admin.auth.admin.createUser({
        email: authEmail,
        password,
        email_confirm: true,
        user_metadata: { account_type: "retailer" },
      });
      if (createError || !created.user) return reply(400, { error: createError?.message || "Account could not be created" });

      const { error: insertError } = await admin.from("retailer_accounts").insert({
        user_id: created.user.id, username, phone, phone_verified: false,
      });
      if (insertError) {
        await admin.auth.admin.deleteUser(created.user.id);
        return reply(409, { error: "Username or mobile number is already registered" });
      }
    } else {
      const { data: account, error: lookupError } = await admin.from("retailer_accounts")
        .select("phone").eq("username", username).maybeSingle();
      if (lookupError) throw new Error("Account lookup failed");
      if (!account) return reply(401, { error: "Invalid username or password" });
    }

    const { data: sessionData, error: signInError } = await admin.auth.signInWithPassword({
      email: authEmail, password,
    });
    if (signInError || !sessionData.session) return reply(401, { error: "Invalid username or password" });

    return reply(200, {
      access_token: sessionData.session.access_token,
      refresh_token: sessionData.session.refresh_token,
      expires_at: sessionData.session.expires_at,
      username,
      phone: action === "signup" ? phone : undefined,
      phone_verified: false,
    });
  } catch (error) {
    console.error("retailer-auth error:", error);
    return reply(500, { error: "Authentication service temporarily unavailable" });
  }
});
