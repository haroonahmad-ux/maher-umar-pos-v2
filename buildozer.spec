[app]
title = Maher Umar POS
package.name = maherumarpos
package.domain = org.maherumar
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt
version = 1.0.1
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.skip_update = False

[buildozer]
log_level = 2
warn_on_root = 1
