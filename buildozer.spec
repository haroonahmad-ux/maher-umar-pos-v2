
[app]

title = POS v2

package.name = maherumarpos

package.domain = org.maherumar

source.dir = .

source.include_exts = py,kv,png,jpg,jpeg,atlas,json,ttf,otf

version = 2.0.0

requirements = python3,kivy

orientation = portrait

fullscreen = 0

# Android permissions
android.permissions = INTERNET

# Android SDK and NDK compatibility
android.api = 36
android.minapi = 24
android.ndk = 29

# Target architecture
android.archs = arm64-v8a

# python-for-android configuration
p4a.branch = develop
p4a.bootstrap = sdl2

# Accept Android SDK licenses during automated builds
android.accept_sdk_license = True

# Keep the Android build focused on the required dependencies
android.add_src =

# Logging
log_level = 2


[buildozer]

# Buildozer runs in the GitHub Actions Linux environment
warn_on_root = 1
