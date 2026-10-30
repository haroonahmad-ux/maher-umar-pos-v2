# Firebase Phone Authentication Integration Audit

Date: 2026-10-30
Repository: `haroonahmad-ux/maher-umar-pos-v2`
Base branch: `main`
Working branch: `feature/firebase-phone-auth`

## Verified repository state

- Android package ID in `buildozer.spec`: `org.maherumar.maherumarpos`.
- App is a Kivy/Python application packaged with python-for-android/Buildozer.
- Build workflow uses Ubuntu 24.04, Python 3.14, Java 17, p4a `develop`, and builds a debug APK.
- Current `main.py` has no login, signup, Firebase, Supabase, or OTP implementation. It opens the POS dashboard directly.
- Current Buildozer requirements are `python3,kivy`; no Firebase Android SDK dependency or Java bridge exists.
- Firebase Android app registration matches the package ID and project ID `maher-umar-pos`. The user added SHA-1 and SHA-256 from the supplied debug APK.
- Firebase `google-services.json` was inspected locally in the conversation; it has not been committed to the repository.

## Verified Supabase state

Project: `dtajbsosaaohyluedcof` (`Maher-Umar-POS`, region `ap-south-1`).

- Existing tables: `products`, `sales`, `sale_items`, `expenses`, `retailer_accounts`, and `retailer_auth_attempts`.
- RLS is enabled on the listed public tables.
- The existing owner policies for products, sales, sale_items, and expenses compare UUID `owner_id` columns to `auth.uid()`.
- Those `owner_id` columns reference `auth.users(id)`.
- Existing cloud tables inspected currently report zero rows. This does not imply the user's local SQLite database is empty.
- Existing Edge Function `retailer-auth` v2 implements username/password login and signup using synthetic internal email addresses. It is not Firebase Phone Auth and must not be silently overwritten.
- The current Kivy `main.py` does not call that Edge Function.

## Integration constraints that must be addressed

1. **Kivy is not a standard Android Studio project.** The Android Firebase Auth SDK must be added through supported python-for-android/Buildozer Gradle dependencies and a Java/Pyjnius bridge. Copying Android Studio Gradle snippets into this repository is not sufficient.
2. **Phone verification requires app verification.** Firebase's Android flow uses Play Integrity and may fall back to reCAPTCHA. The app must be tested on an actual Android device with Google Play services. The uploaded APK fingerprints are for that debug signing certificate only.
3. **Spark plan is not a promise of free production SMS.** Firebase's current console warning says 10 SMS/day for new projects, but Google documentation says real phone SMS requires a Cloud Billing account and is billed per SMS. Use Firebase test phone numbers for no-cost development until the owner explicitly chooses to enable billing.
4. **Supabase third-party Firebase auth requires a provider integration and a `role: authenticated` JWT claim** for normal authenticated-role RLS access. Firebase ID tokens do not include that claim by default.
5. **Firebase UIDs are strings, not guaranteed UUIDs.** The current Supabase `owner_id UUID` foreign keys and `auth.uid()` RLS expressions are not automatically compatible with Firebase UIDs. Do not point Firebase tokens at these tables until a deliberate, tested identity/schema strategy is selected.
6. Do not expose Supabase service-role keys, Firebase service-account credentials, or signing secrets in the Android app or Git repository.

## Safe implementation sequence

1. Keep all work on `feature/firebase-phone-auth`; do not modify `main`.
2. Build and test a minimal native Firebase Phone Auth bridge for Kivy using the Firebase Android Auth SDK, with no real-SMS assumption. Add a debug/test-number path and safe error handling.
3. Add a polished phone-number/OTP UI gate without changing POS database logic or backup/restore behavior.
4. Decide and implement the Supabase identity bridge and RLS strategy only after validating Firebase token claims and the existing ownership model. Preserve the existing `retailer-auth` function until a replacement is fully tested.
5. Run Python syntax checks, Android build, install/launch tests, test-number OTP flow, restart/session persistence tests, and regression checks for all existing POS features before opening a PR.

## Current status

- Working branch created from the verified `main` commit.
- No production database schema, Edge Function, or `main` branch file has been changed by this audit.
- No claim is made that Firebase OTP is working yet.