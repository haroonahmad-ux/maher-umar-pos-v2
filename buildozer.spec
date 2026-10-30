[app]

title = POS v2

package.name = maherumarpos

package.domain = org.maherumar

# The workflow creates this isolated directory from main.py before building.
# Keeping the Java source root outside the repository root avoids Gradle task
# validation errors caused by generated build outputs being scanned as sources.
source.dir = .app-source

source.include_exts = py,kv,png,jpg,jpeg,atlas,json,ttf,otf

version = 2.0.0

# Custom bright mobile-retail POS app icon
icon.filename = app_icon.png

requirements = python3,kivy

# Native Firebase Phone Authentication SDK and Java bridge
android.gradle_dependencies = com.google.firebase:firebase-auth:25.0.0
android.add_src = android-src
android.enable_androidx = True
android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"

orientation = portrait

fullscreen = 0

# Android permissions
android.permissions = INTERNET

# Android SDK and NDK compatibility
android.api = 36
android.minapi = 24
android.ndk = 28c

# Target architecture
android.archs = arm64-v8a

# python-for-android configuration
p4a.branch = develop
p4a.bootstrap = sdl2

# Accept Android SDK licenses during automated builds
android.accept_sdk_license = True

# Logging
log_level = 2


[buildozer]

# Buildozer runs in the GitHub Actions Linux environment
warn_on_root = 1
