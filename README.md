# Maher Umar POS — clean repository starter

This package contains the full UI source from the uploaded project, with targeted UI fixes. It is not yet confirmed crash-free: GitHub Actions and a real Android phone test are still required.

## Included fixes
- Uses the full POS UI source as `main.py`, rather than the older unrelated/simple app entrypoint.
- Keeps Android status and navigation bars visible (`fullscreen = 0`, `Window.fullscreen = False`).
- Adds top breathing room so page headings do not overlap the status bar.
- Adds 104dp bottom clearance so Back to Dashboard buttons sit above the Android navigation area.
- Replaces the confirmation dialog with bold, dark, readable text and dynamic height.
- Preserves a copy of the unmodified UI source as `ORIGINAL_UI_SOURCE_BACKUP.py`.
- Adds startup exception logging already present in the full UI source.
- Workflow adds libtool-related packages for the observed `LT_SYS_SYMBOL_USCORE` / `autoreconf` build failure and uploads diagnostics even on failure.

## Upload to a new repository
1. Create a new GitHub repository (keep the old repository and working APK for now).
2. Upload all files and folders from this ZIP, including `.github/workflows/build-apk.yml`.
3. Ensure the default branch is `main`.
4. Open Actions and run **Build and diagnose Maher Umar POS APK**.
5. If it fails, download the diagnostics artifact; do not keep blindly reinstalling new APKs.
6. If it succeeds, install-test the APK and test dashboard, product save, checkout, expense save, reports and back buttons before retiring the old repository.

## Important limits
- Python syntax checks passed in this environment, but this ZIP has not been built by GitHub Actions or launched on a physical Android phone.
- A successful build does not prove the app will not crash on launch.
- The `libtool` dependency fix is based on the observed build log and may reveal another toolchain issue after it is resolved.
