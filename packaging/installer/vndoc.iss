; ============================================================================
; vndoc.iss — Inno Setup script cho bộ cài VNDoc OCR Service (DOC-11 §6, DEC-081)
; Sinh:  VNDoc-Setup-{version}.exe   (cài thủ công từng máy, cần quyền Administrator)
; Compile:  iscc packaging\installer\vndoc.iss   (sau khi build.ps1 dựng xong staging)
; ============================================================================

#define AppName    "VNDoc OCR Service"
#define AppVersion "0.1.0"
#define AppPublisher "VNDoc"
#define ServiceName "VNDocOCR"
; Thư mục staging do build.ps1 tạo (đường dẫn tương đối tính từ file .iss này).
#define StageDir   "..\..\build\stage"

[Setup]
AppId={{8F5C2A10-VNDOC-4B21-9E3A-0CR5SERVICE01}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\VNDoc
DefaultGroupName=VNDoc
DisableProgramGroupPage=yes
OutputBaseFilename=VNDoc-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Cài service cần quyền admin.
PrivilegesRequired=admin
WizardStyle=modern

[Files]
; Toàn bộ cây staging (app đã obfuscate, rectifier, runtime, site-packages, models, plugins,
; launcher, nssm.exe, init-config.ps1, script service, config\vndoc.env.example...).
; KHÔNG đè config\vndoc.env đang có của admin (init-config.ps1 tạo/sinh key lần đầu).
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "config\vndoc.env"

[Dirs]
; Thư mục ghi log + config giữ lại khi gỡ (chứa cấu hình/nhật ký admin).
Name: "{app}\logs";   Flags: uninsneveruninstall
Name: "{app}\config"; Flags: uninsneveruninstall

[Icons]
; Lối tắt Start Menu cho cán bộ triển khai.
Name: "{group}\Hướng dẫn cài đặt VNDoc";     Filename: "{app}\HUONG-DAN-CAI-DAT.md"
Name: "{group}\Thư mục cấu hình (API key)";   Filename: "{app}\config"
Name: "{group}\Kiểm tra VNDoc (health)";      Filename: "http://127.0.0.1:11001/api/v1/health"

[Run]
; 0) Mở hướng dẫn sau khi cài (tuỳ chọn — checkbox ở màn hình cuối).
Filename: "{app}\HUONG-DAN-CAI-DAT.md"; \
    Description: "Mở hướng dẫn cài đặt & cấu hình"; \
    Flags: postinstall shellexec skipifsilent nowait unchecked
; 1) Tạo config + SINH API KEY ngẫu nhiên lần cài đầu (DEC-088) — TRƯỚC khi service chạy.
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\init-config.ps1"" -InstallRoot ""{app}"""; \
    StatusMsg: "Đang tạo cấu hình & sinh API Key..."; \
    Flags: runhidden waituntilterminated

; 2) Đăng ký + khởi động Windows Service qua NSSM (script kiểm tra /health).
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install-service.ps1"" -InstallRoot ""{app}"""; \
    StatusMsg: "Đang đăng ký dịch vụ VNDoc OCR (:11001)..."; \
    Flags: runhidden waituntilterminated

[UninstallRun]
; Gỡ service trước khi xoá file.
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall-service.ps1"" -InstallRoot ""{app}"""; \
    RunOnceId: "RemoveVNDocService"; \
    Flags: runhidden waituntilterminated

[Messages]
; (tuỳ chọn) Việt hoá vài chuỗi — Inno có gói ngôn ngữ riêng nếu cần đầy đủ.
