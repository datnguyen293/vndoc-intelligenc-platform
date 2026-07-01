# Giữ DTO kotlinx.serialization của SDK (parse JSON phản hồi).
-keep,includedescriptorclasses class vn.vndoc.sdk.model.**$$serializer { *; }
-keepclassmembers class vn.vndoc.sdk.model.** { *** Companion; }
-keepclasseswithmembers class vn.vndoc.sdk.model.** { kotlinx.serialization.KSerializer serializer(...); }
