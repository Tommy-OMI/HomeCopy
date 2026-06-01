# HomeCopy 原生重写设计文档

> 文档日期：2026-05-31 PDT
> 状态：方案已定，未开工。Mac/Windows 架构已详细规划；iOS/Android 仅定位 + 已知约束，详细架构待补。
> 现有 Python 版进入**维护冻结**，新版从零开始，不背任何兼容包袱。

---

## 1. 项目背景

### 1.1 HomeCopy 是什么
一个**局域网内设备之间**互传文字和文件的桌面工具。核心场景：在一台设备上复制一段文字 / 选一个文件，通过全局快捷键或界面操作，瞬间发到同一局域网的另一台设备。

### 1.2 现状
- 技术栈：Python + PySide6(Qt) UI + PyInstaller 打包，覆盖 macOS / Windows。
- 架构：一台机器跑**中心 WebSocket relay server**（端口 8765）+ UDP 广播做设备发现（端口 8766），其它机器当 client 连上来。
- 已有功能：设备发现、文本收发、**文件分块传输**（256KB/块，上限 10MB）、全局快捷键、菜单栏/托盘常驻、历史记录、收到文本自动写入剪贴板、开机自启、简单 token 鉴权。

### 1.3 为什么重写
1. **要上架 + 多平台**：目标做成正经产品，免费下载、App 内打赏，覆盖四平台。Python/PyInstaller 上 Mac App Store 是公认的"失败之地"（沙盒撞 Python 运行时），无法满足。
2. **架构要去中心**：现有"一台当 server"的模式笨重；改成对等设备(P2P) + mDNS 自动发现，无单点。
3. **原生体验 + 系统集成**：剪贴板、全局快捷键、通知、分享等深度系统集成，原生实现远优于跨平台 Python。

---

## 2. 产品决策（已拍板）

| 决策项 | 结论 |
|---|---|
| 商业模式 | 免费下载，App 内"支持开发者/打赏"入口 |
| 打赏实现 | **IAP Consumable**（消耗型应用内购，3 档如 $2.99/$9.99/$19.99）。**禁止用 "donation/捐款" 字样**——营利主体只能做功能性 IAP，文案用 "Supporter Pack / 请开发者喝咖啡 / Tip" |
| 开发者账号 | 用 **OMI OPTICS 公司（组织）会员**，卖家名显示 OMI OPTICS |
| 新增需求 | **文件传输**升级为一等功能（去掉 base64、放宽到 GB 级、加 SHA256 校验、进度、断点） |
| 平台优先级 | **macOS > Windows > iOS > Android**（Android 最后） |
| 协议 | **全新定义，不兼容旧 Python 版**（产品未正式发布，无历史包袱） |
| UI 风格 | **沿用现有配色**：暖白底(#f4efe7 / #fffaf2) + 深海军蓝卡片(#183153) + 金黄强调(#f5c451)，圆角卡片式布局。**禁止 AI 味淡紫渐变** |
| 网络边界 | 仅"同一局域网同一子网"。不做 NAT 穿透 / 跨网 / 中继（未来若做跨网走 Tailscale 类虚拟局域网，现在不碰） |

---

## 3. 平台策略

各平台用各自一等公民技术栈，靠**一套冻结的通信协议**打通（详见 §5）。

| 平台 | UI / 语言 | 上架与分发 |
|---|---|---|
| **macOS** | Swift（SwiftUI 为主，AppKit 兜底） | Mac App Store（免费 + IAP 打赏，沙盒 + 公证）；同时 Developer ID 公证版走 Homebrew Cask / GitHub / 官网 |
| **Windows** | C# / .NET（**WPF**，非 WinUI 3） | 官网 / GitHub / winget。**不买代码签名证书**，接受 SmartScreen "未知发布者"提示（下载页注明"点'仍要运行'"） |
| **iOS** | Swift（与 macOS 共享 SwiftUI 代码） | App Store。**形态与桌面不同**，见 §3.1 |
| **Android** | Kotlin / Compose | 官网 / Play Store（最后做） |

> **架构选型仍有一个开放议题**：四平台 + 文件传输 + 加密让"每个平台各写一遍核心逻辑"成本高（4 倍 bug 面 + 协议易漂移）。备选方案是把核心引擎（mDNS/P2P/文件传输/加密/协议）做成**共享库**（Rust FFI 或 Kotlin Multiplatform），各平台只写原生 UI。**当前方案按"各平台原生"规划；是否引入 Rust 共享核心待后续 ROI 评估。**

### 3.1 iOS 的特殊性（关键约束）
- **iOS 没有"全局剪贴板自动监控"**：app 退后台后被系统挂起，读不到剪贴板；前台读剪贴板还会弹系统提示。所以"自动同步剪贴板"在 iOS 上**做不到**。
- **iOS 没有简单的后台保活**：app 一退后台几秒内挂起，socket 断、Bonjour 监听停。无法做到"app 没开还能随时收"。
  - 唯一能"局域网后台保活接收"的正路是 **Local Push Connectivity (NEAppPushProvider / Network Extension)**，但实现复杂、绑定特定 WiFi、审核审查严——是否投入待定。
- **iOS 定位**：**以"发送"为主、接收为辅**。手机主动把文字/文件推到桌面（顺）；接收只在前台或靠通知提醒打开。**不承诺桌面级无缝后台同步**。文件传输是移动端更自然的主场景。
- Android 限制较宽，但后台 service 也有约束，规划时一并处理。

---

## 4. 目标架构（macOS Swift 端，作为基准）

单 App target + 多个 local Swift package（便于单元测试）。不引入跨平台抽象，Windows 自己实现，共享的只有协议规范文档。

```
HomeCopyMac.app
├── App/              SwiftUI App + AppDelegate, MenuBarExtra, Onboarding
└── Packages/
    ├── HCCore/       ID 生成、配置(Codable)、Logger、Keychain 封装
    ├── HCDiscovery/  Bonjour 发布+浏览 (Network.framework NWBrowser/NWListener)
    ├── HCTransport/  P2P 连接 (NWConnection + TLS)、帧编解码 (length-prefixed CBOR)
    ├── HCProtocol/   消息 schema(Codable) + 版本协商 + 状态机
    ├── HCCrypto/     CryptoKit：Ed25519 身份、X25519 配对、ChaCha20-Poly1305
    ├── HCClipboard/  NSPasteboard 读写 + changeCount 轮询
    ├── HCHotkey/     CGEventTap + Input Monitoring 引导
    ├── HCHistory/    GRDB + SQLite，最近 N 条
    └── HCStore/      收件文件落地
```

### 4.1 macOS 技术选型（已拍板）
| 决策点 | 选定 | 理由 |
|---|---|---|
| UI | SwiftUI 为主 + AppKit 兜底 | macOS 13+ 够用，开发快 |
| 服务发现 | Network.framework (NWListener.service) | 沙盒友好，不用废弃的 NetService |
| P2P 传输 | NWConnection over TCP + TLS | 沙盒下 network.client/server 即可；不用 QUIC（沙盒坑多） |
| Wire format | **CBOR + length-prefixed framing** | 二进制紧凑，文件块不用 base64；不用 protobuf 避免 codegen 工具链 |
| 加密 | CryptoKit：Ed25519 身份 + X25519 协商 + ChaCha20-Poly1305；配对用 **SAS 短码比对** | TLS 保传输，应用层加密防设备伪造 |
| 全局快捷键 | CGEventTap + Input Monitoring 权限 | 比 Carbon 在沙盒+SwiftUI 下稳 |
| 剪贴板 | NSPasteboard + changeCount 轮询(250ms) | macOS 无剪贴板变更通知 |
| 本地存储 | GRDB.swift + SQLite | history 要查询/分页/清理 |
| IAP | StoreKit 2 | async/await，收据校验内置 |
| 包管理 / 异步 | SPM only / async-await + AsyncSequence | 不引 CocoaPods / RxSwift |

### 4.2 Windows 选型（已拍板）
- UI 用 **WPF 而非 WinUI 3**：WinUI 3 要 Windows App SDK，对"未签名小工具"分发不友好；WPF 单文件发布、SmartScreen 提示一次即可、托盘(NotifyIcon)简单。
- mDNS：Makaretu.Dns.Multicast 或 Zeroconf.NET（需真机验证与 Apple Bonjour 互通）。
- TLS：SslStream + 自签证书；Crypto：.NET 9 BCL 或 NSec.Cryptography；全局热键：P/Invoke RegisterHotKey；剪贴板：System.Windows.Clipboard；托盘：H.NotifyIcon.Wpf。

---

## 5. 通信协议 v1（跨平台契约）

这是各平台打通的唯一权威契约，落地前应单独写成 `PROTOCOL.md`（字段表 + hex dump 示例）。

### 5.1 服务发现（mDNS / DNS-SD）
- Service type：`_homecopy._tcp.`
- Port：进程启动由 OS 分配 ephemeral 端口，经 SRV 暴露。
- TXT records（小写键）：
  ```
  v=1                    协议主版本
  did=<base32 指纹>      设备身份：Ed25519 公钥 SHA256 前 16 字节 base32
  n=<utf8 设备名>        展示名
  os=mac|win|ios|android 平台 hint
  ver=0.9.0              软件版本（diagnostic）
  proto=cbor1            wire format 标签
  ```

### 5.2 配对流程（SAS pairing，类 AirDrop 体验）
1. TLS 握手：双端自签证书（CN=did，Ed25519 私钥签名），**pin-by-fingerprint**，不验证书链。
2. 发起方发 `pair_req`（含 x25519 公钥 + 展示名）。
3. 接收方 UI 确认后回 `pair_ack`。
4. 双端各自 `HKDF(shared_secret, salt=did_a||did_b, info="homecopy-sas")` 派生 **6 位十进制 SAS**，两屏同时显示，用户肉眼比对一致后点"匹配"。
5. 持久化对端 did + 公钥 + long-term chain_key 到 Keychain(Mac) / DPAPI(Win)。

后续连接直接 TLS+pinned cert；每条消息用 chain_key 派生的 per-session key 走 ChaCha20-Poly1305 AEAD，nonce 用消息序号。

### 5.3 消息格式（CBOR，length-prefixed）
- Framing：`[uint32 BE length][CBOR payload]`，单帧上限 1 MiB（文件多帧分块）。
- Envelope：`{ v, t(type), id(16字节UUID), ts(ms), p(payload) }`
- Types：`hello / hello_ok / pair_req / pair_ack / sas_confirm / text / file_begin / file_chunk / file_end / ack / ping / pong / bye`
  - `file_begin`：`{file_id, name, size, mime?, sha256}`
  - `file_chunk`：`{file_id, seq, data:bytes}`（CBOR bytes 无需 base64）
  - `file_end`：`{file_id, total_chunks}`，接收端校验 SHA256，不通过则丢弃。
- 版本协商：双方互发 hello 取 `min(proto_max)`；v1 不接受 v0。

### 5.4 设计取舍
- **不做** message queue / 离线暂存：对端离线即失败，UI 提示 "X is offline"。
- **不做** NAT 穿透 / WAN：明确同子网边界。
- 文件 SHA256 **必填**校验。

---

## 6. 分阶段路线

### macOS（约 26 人日，含审核往返）
- **M1 协议骨架 + 两 Mac 文本互通**（~5 人日）：HCCrypto(Ed25519+Keychain) → HCDiscovery(Bonjour+TXT) → HCTransport(TLS+pin) → HCProtocol(CBOR envelope + hello/text/ack)。命令行 demo 验证两台 Mac 互发文本。无 UI/配对/加密/沙盒。
- **M2 UI + 剪贴板 + 全局快捷键 + 历史**（~7 人日）：SwiftUI 主窗 + MenuBarExtra + 托盘常驻 + 热键发剪贴板 + GRDB 历史。
- **M3 配对 + 加密 + 文件传输**（~8 人日）：X25519+SAS 配对流程、文件分块 + SHA256 + 进度条、通知集成。验收 100MB 量级文件跑通、非配对设备被拒。
- **M4 沙盒 + 公证 + IAP + 上架**（~6 人日）：app-sandbox + network.client/server entitlements、Info.plist（NSLocalNetworkUsageDescription 必填 + NSBonjourServices）、Input Monitoring 引导、StoreKit2 Consumable + 感谢 UI、notarization + App Store Connect 提审。

> **M4 中需要 Tommy 本人操作的部分**（账户/财务，不可代劳）：Apple ID 登录、签名证书、IAP 产品配置、Paid Apps 协议。其余 M1–M3 编码不需 Tommy 在场。

### Windows（约 15 人日）
照协议实现 M1–M3 对位功能（无 IAP/公证/上架）。**关键里程碑**：macOS M1 一完成，立刻用 Makaretu.Dns 在 Windows 发同样 `_homecopy._tcp` 服务，验证 Mac↔Win 互相发现 + TXT 解析——**这一步决定 Windows 路线是否成立，不能拖到后期**。

### iOS / Android
详细架构待补（见 §3.1 约束）。iOS 重点是重新设计"前台 + 发送为主"的交互模型，以及评估 Local Push Connectivity 是否值得。

---

## 7. 关键技术风险
- **沙盒 Bonjour**：Info.plist 漏写 NSBonjourServices 会导致服务发布静默失败、无报错——M1 第一天就要在沙盒环境验证。
- **CGEventTap + Input Monitoring**：权限要用户手动去系统设置开，无法编程申请；未开权限时 EventTap "装得上但收不到事件"，必须主动 poll 权限状态并引导。
- **App Store 审 network.server**：reviewer 可能质疑为何要监听，文案要讲清"局域网设备间直传"。
- **IAP 文案**：禁 donation/tip jar 字样，必须包装成功能性 IAP（Supporter Pack 之类）。
- **Local Network 权限**（macOS 14+）：首次 Bonjour 弹系统权限，拒绝后无回退，UI 要显式说明。
- **mDNS 跨 Mac/Win 互通**：部分 .NET mDNS 库有边角 bug，M1 后立刻联调。
- **TLS pin-by-fingerprint**：要手写 verify block，写错会变成"接受任何证书" → 中间人风险。
- **Ed25519 跨平台编码差异**：协议统一约定"裸 32 字节"，不用 DER/PKIX。

---

## 8. 相对现有 Python 版主动删除的功能
- 嵌入式 server 启停按钮、EmbeddedServerController、Local Relay 面板、server stats 轮询——P2P 后无 server 角色，整块删。
- token 鉴权 + 配置向导里的 token 字段——用 SAS 配对密钥替代，用户不再手填字符串。
- 文件 base64 over JSON、10MB 上限——P2P 直传二进制，放宽到 GB 级。

---

## 9. 未决问题 / 未来方向
1. **核心引擎是否做共享库**（Rust FFI / KMP）vs 各平台原生——待四平台铺开后做 ROI 评估。
2. **iOS 后台接收**是否上 Local Push Connectivity——待 iOS 阶段评估。
3. **跨网同步**：当前仅同子网；未来跨网可走 Tailscale 类虚拟局域网把异地设备纳入同一虚拟 LAN，不自建 NAT 穿透。
4. **分发渠道铺设**：Homebrew Cask / winget manifest / 官网下载页（含打赏入口）/ Product Hunt 发布——地基（公证安装包）完成后边际成本低。

---

## 10. 第一步落地清单
1. 建 `Mac-Swift/` 子目录（与现有 `MacOS/` Python 版并存，Python 进入维护冻结），Xcode 起 SwiftUI App + 多 local Swift package 骨架。
2. 把 §5 落定为 `PROTOCOL.md`（唯一权威 spec）。
3. 实现 M1，命令行 demo 验证两 Mac 互发文本。
4. M1 完成立刻做 Windows mDNS 互通 spike。
5. 按 M2 → M3 → M4 推进，每阶段写 CHANGELOG。
