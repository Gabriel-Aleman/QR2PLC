[app]
title = Escaner QR PLC
package.name = escanerqr
package.domain = org.planta
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0

# opencv usa la receta de python-for-android (la primera compilación tarda bastante)
requirements = python3,kivy==2.3.1,numpy,opencv,plyer,pycomm3
p4a.branch = develop

orientation = portrait
fullscreen = 0

android.permissions = CAMERA,INTERNET,ACCESS_NETWORK_STATE,READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
