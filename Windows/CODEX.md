# OMI Astera 项目实施文档（Codex 执行版）

## 项目名称

**OMI Astera**

## 项目工作根目录

Codex 后续执行本项目相关命令、读取文件、修改文件时，默认以以下目录作为工作根目录：

```text
D:\AIAgent\OMI Astera
```

副标题：

> OMI Astro AI-powered Astrophotography Platform

定位：

> 面向天文摄影用户的桌面 App，集成本地拍摄工作流、Dropbox 同步、云端校准叠加、AI 辅助拍摄决策，并为未来自动化拍摄执行预留架构。

---

# 一、项目目标

OMI Astera 不是普通同步工具，而是 OMI Astro 未来的软件平台入口。

## Phase 1：MVP

目标：先做可收费版本。

核心功能：

- 桌面 App 输入 License Key
- 连接 OMI Cloud API
- 获取客户专属 Dropbox 共享目录
- 自动创建本地项目目录
- 监听本地 FITS 文件
- 云端自动校准、注册、叠加
- 输出各通道 Master 图像
- 邮件通知客户完成

暂不做：

- NINA 模板自动部署
- 自动修改 NINA 配置
- 全自动拍摄执行

---

## Phase 2：AI Planner

新增：

- AI 辅助拍摄决策
- 根据设备、地点、天气、月相、目标高度、历史数据，推荐今晚最值得拍的目标
- 输出目标评分、推荐曝光方案、滤镜组合、预计可用拍摄时长

核心理念：

> 不是列出今晚能拍什么，而是判断今晚拍什么最值得。

---

## Phase 3：Auto Capture Engine

未来实现：

- 自动生成拍摄任务
- 自动下发 NINA Sequence
- 自动执行拍摄
- 自动失败重试
- 自动多夜累计
- 自动云端处理

---

# 二、产品形态

OMI Astera 是 **桌面 App + 云端服务**，不是单纯网站。

```text
客户电脑：
OMI Astera Desktop App

云端：
OMI Cloud API（优先使用 Wix HTTP Functions 实现）
Processing Server
Storage
Task Queue
Email Notification
```

现有业务网站：

```text
https://omiastro.com
```

该网站基于 Wix 开发，因此 Phase 1 的 OMI Cloud API 优先使用 Wix 的 HTTP 接口能力实现，作为桌面 App 与业务网站、License、客户配置、Dropbox 路径、处理任务之间的桥梁。

---

# 三、已确认的关键决策

以下决策作为 MVP 实施边界：

1. Phase 1 只做可收费闭环：
   `License -> Dropbox 项目目录 -> 本地监听 FITS -> 云端处理 -> 输出 Master -> 邮件通知`

2. 桌面端技术栈：
   `Electron + React + TypeScript + SQLite`

3. Phase 1 同步方案：
   Dropbox Desktop Client 负责实际文件同步；OMI Astera 不调用 Dropbox API 上传 / 下载 FITS。桌面端和服务端只读取各自机器上的本地 Dropbox 同步目录，并维护 readiness、索引和处理状态。后续再抽象支持 S3、Cloudflare R2 或自有对象存储。

4. AI Planner：
   Phase 1 只保留 Dashboard 展示和页面入口，可使用 mock 数据或只读占位数据；真实推荐算法放到 Phase 2。

5. NINA 自动化：
   不进入 MVP。Phase 1 只在项目结构和数据模型上为未来 Auto Capture Engine 预留接口。

---

# 四、总体架构设计

OMI Astera 采用 **Desktop Control Platform + Local Agent + Cloud Processing Platform** 架构。

```text
OMI Astera Desktop App
├─ UI Console
├─ Local Agent
├─ License Client
├─ Project Manager
├─ File Watcher
├─ Dropbox Sync Adapter
├─ Processing Monitor
├─ Local SQLite Database
└─ Local Log System

OMI Cloud
├─ Wix HTTP Functions / OMI Cloud API
├─ License & Account Service
├─ Customer Config Service
├─ Dropbox Provisioning Service
├─ Project / Job Service
├─ Processing Queue
├─ Processing Worker
├─ Storage / Output Service
├─ Email Notification Service
└─ Future AI Planner Service
```

## 4.1 桌面端模块

### UI Console

对应原型图中的主要页面：

- Dashboard
- Projects
- AI Planner
- Files & Sync
- Processing
- Logs
- Settings

Dashboard 需要展示：

- License 状态
- Dropbox 连接状态
- Local Agent 运行状态
- Cloud Service 状态
- Storage 使用量
- 当前项目
- 处理进度
- Processing Pipeline
- Log Console
- AI Planner 摘要
- Quick Actions

### Local Agent

Local Agent 是桌面端的核心后台模块，负责：

- 常驻运行
- 监听本地项目目录
- 检测新 FITS 文件
- 判断文件是否写入完成
- 将稳定文件加入同步队列
- 维护本地任务状态
- 写入本地日志
- 与云端 API 同步任务进度

### License Client

负责：

- 保存 License Key
- 启动时验证 License
- 获取 Account ID、Plan、有效期
- 获取客户专属 Dropbox 路径
- 获取云端配置
- 处理 License 过期、无效、降级等状态

### Project Manager

负责：

- 创建新项目
- 打开已有项目
- 管理项目元数据
- 自动生成项目目录结构
- 保存目标对象、滤镜、曝光、备注、处理状态

建议本地项目结构：

```text
Projects/
└─ M31_Andromeda_Galaxy/
   ├─ raw/
   │  ├─ L/
   │  ├─ R/
   │  ├─ G/
   │  ├─ B/
   │  ├─ Ha/
   │  └─ OIII/
   ├─ calibration/
   ├─ output/
   ├─ logs/
   └─ project.omi.json
```

### File Watcher

负责：

- 监听 `.fit` / `.fits` 文件
- 过滤临时文件
- 检测文件大小是否稳定
- 记录发现时间、稳定时间、上传状态
- 避免重复上传

### Dropbox Local Sync Adapter

Phase 1 只实现 Dropbox 本地同步目录适配，但接口设计需要可替换：

```text
SyncAdapter
├─ DropboxLocalFolderAdapter
├─ FutureS3SyncAdapter
├─ FutureR2SyncAdapter
└─ FutureCustomStorageAdapter
```

核心能力：

- 关联 License 返回的 Dropbox shared link 与本地 Dropbox 目录
- 扫描本地 Dropbox 同步目录
- 统计目标文件夹、通道、FITS 数量、曝光时长和总大小
- 判断文件是否稳定
- 写入 / 识别 `omi_complete.json` 完成标记
- 维护 ready、queued、processing、done、failed 等状态

### Processing Monitor

负责显示云端处理状态：

```text
Ingest -> Calibration -> Registration -> Integration -> Color Calibration -> Master Output -> Completed
```

桌面端不负责实际天文图像处理，只负责：

- 创建处理任务
- 查询任务状态
- 展示 pipeline 进度
- 展示输出结果
- 打开本地输出目录

### Local SQLite Database

用于保存：

- License 缓存
- 用户配置
- 项目列表
- 文件索引
- 同步状态
- Processing Job 状态
- 日志索引
- AI Planner 缓存数据

---

# 五、云端架构设计

## 5.1 OMI Cloud API

由于现有业务网站 `omiastro.com` 基于 Wix 开发，Phase 1 的 API 层优先使用 Wix HTTP Functions 实现。

## 5.1.1 Desktop 登录方案

OMI Astera Desktop App 登录不打开 `omiastro.com` 网站首页，也不嵌入普通网站页面。

登录采用 **Wix Headless OAuth 2.0 + PKCE**：

```text
Desktop App
  -> 生成 PKCE code_verifier / code_challenge
  -> POST https://www.wixapis.com/oauth2/token 获取 anonymous visitor token
  -> POST https://www.wixapis.com/_api/redirects-api/v1/redirect-session 创建 Wix 托管登录页
  -> Electron 登录窗口打开 redirectSession.fullUrl
  -> Wix 登录成功后回调 https://www.omiastro.com/_functions/authCallback
  -> Wix HTTP Function 302 到 omiastro://auth?code=...&state=...
  -> Desktop App 捕获 code
  -> POST https://www.wixapis.com/oauth2/token 换取 access_token / refresh_token
  -> GET https://www.wixapis.com/members/v1/members/my?fieldsets=FULL 获取会员信息
```

桌面端配置：

```text
clientId: d587c932-f679-4ecb-9eed-646950b99331
siteId: 6ce2d899-07f4-421f-912e-872f081db5d9
redirectUri: https://www.omiastro.com/_functions/authCallback
callbackScheme: omiastro
tokenEndpoint: https://www.wixapis.com/oauth2/token
```

Wix 端需要提供：

- `/_functions/authCallback`：接收 `code` 和 `state` 后 302 到 `omiastro://auth?code=...&state=...`
- `/_functions/astera/license/activate`：校验 License，返回用户对应 Dropbox Shared Link

启动检查当前只做：

- 是否有用户登录态
- 是否有 License 激活态

建议 API 职责：

- License 验证
- Account 查询
- Plan 查询
- 客户 Dropbox 路径查询
- 项目创建
- 处理任务创建
- 处理状态查询
- 输出结果查询
- 桌面端配置下发

建议 API 示例：

```text
POST /_functions/astera/license/activate
GET  /_functions/astera/account/me
GET  /_functions/astera/dropbox/config
POST /_functions/astera/projects
POST /_functions/astera/jobs
GET  /_functions/astera/jobs/{jobId}
GET  /_functions/astera/storage/usage
POST /_functions/astera/logs/client
```

Wix API 层不建议承担重型图像处理任务。它更适合作为业务网关、权限层和任务调度入口。

## 5.2 Processing Server

Processing Server 负责实际天文图像处理，应独立于 Wix 运行。

职责：

- 从本机 Dropbox Desktop 已同步到本地的目录读取 FITS 文件
- 扫描目标文件夹并按通道统计 FITS 数、曝光时长、总大小
- 判断目标文件夹是否已完成拍摄并可开始预处理
- 执行校准
- 执行注册
- 执行叠加
- 生成各通道 Master
- 写回本地 Dropbox 输出目录，由 Dropbox Desktop 自动同步回云端和客户电脑
- 更新任务状态

第一阶段 Processing Server 采用 Python CLI 形态，不注册 Windows Service：

```text
omi-processing health
omi-processing scan --config D:\OMI\config\processing-server.yaml
omi-processing process-once --config D:\OMI\config\processing-server.yaml --dry-run
```

GitHub self-hosted runner 安装在预处理机器上并作为 Windows Service 常驻。每次服务端代码 push 后，GitHub Actions 在该机器上执行：

```text
checkout -> install Python package -> run tests -> CLI health -> optional real Dropbox scan
```

这样可以形成“发布 -> 启动命令行验证 -> 查看日志 -> 修复 -> 再发布”的闭环。OMI Processing Server 本身暂不需要开机自动加载；等处理逻辑稳定后，再增加长期 worker 或 Windows Service。

目标文件夹 readiness 建议：

```text
存在 omi_complete.json
AND 所有 FITS 文件修改时间超过 stable_after_minutes
AND 没有正在变化的文件
=> ready
```

如果没有 `omi_complete.json`，但目录长时间稳定，则显示 `stable`，默认不自动处理，等待用户确认或后续规则触发。

后续可接入：

- PixInsight CLI / WBPP
- Siril CLI
- 自研 Python processing pipeline
- GPU Worker

## 5.3 Task Queue

建议 Processing Job 通过队列异步执行。

Phase 1 可先简单实现：

- Wix API 创建 Job
- 数据库记录 Job
- Worker 定时拉取待处理 Job

后续可升级为：

- Redis Queue
- Cloud Tasks
- SQS
- RabbitMQ

## 5.4 Email Notification

处理完成后发送邮件：

- 处理成功通知
- 处理失败通知
- 输出路径
- 项目名称
- 处理摘要

---

# 六、Phase 1 MVP 工作流

```text
用户打开 OMI Astera Desktop App
        ↓
输入 License Key
        ↓
Desktop App 调用 Wix HTTP Functions 验证 License
        ↓
云端返回 Account、Plan、Dropbox 路径、配置
        ↓
用户创建本地项目
        ↓
Local Agent 监听项目目录
        ↓
NINA 或用户手动产生 FITS 文件
        ↓
File Watcher 检测到文件并确认写入完成
        ↓
Dropbox Desktop 自动同步文件到云端和预处理机器
        ↓
Desktop App / Wix API 创建 Processing Job
        ↓
Processing Worker 从预处理机器本地 Dropbox 目录读取文件并处理
        ↓
Worker 更新 Job 状态
        ↓
Desktop App 展示 pipeline 进度
        ↓
输出 Master 文件
        ↓
邮件通知客户
```

---

# 七、Phase 1 执行规划

## Milestone 1：桌面 App 骨架

目标：

- 建立 Electron + React + TypeScript 项目
- 实现主窗口、路由、左侧导航
- 按 prototype.png 搭建 Dashboard 基础布局
- 建立主题、组件、图标、状态卡片、日志面板

验收标准：

- App 可本地运行
- Dashboard 与原型图核心布局一致
- 页面包含 Dashboard、Projects、AI Planner、Files & Sync、Processing、Logs、Settings 入口

## Milestone 2：本地数据与项目系统

目标：

- 集成 SQLite
- 建立项目、文件、任务、日志数据表
- 实现 New Project / Open Project
- 自动创建本地项目目录

验收标准：

- 可以创建项目
- 可以重新打开项目
- 项目元数据可持久化
- Dashboard 可显示当前项目

## Milestone 3：License 与 Wix API

目标：

- 实现 License Key 输入与保存
- 建立 Wix HTTP Functions API 约定
- 接入 License 验证接口
- 返回 Account ID、Plan、有效期、Dropbox 路径

验收标准：

- License 有效时进入主界面
- License 无效时阻止核心功能
- Dashboard 显示账号、套餐、有效期

## Milestone 4：FITS 文件监听

目标：

- 监听项目目录
- 检测 `.fit` / `.fits`
- 判断文件稳定
- 写入本地文件索引
- 更新 Dashboard 统计

验收标准：

- 新 FITS 文件能被发现
- 未写完文件不会立刻上传
- 文件数量、总大小、日志能更新

## Milestone 5：Dropbox 同步

目标：

- 实现 Dropbox Sync Adapter
- 上传稳定 FITS 文件
- 维护上传状态
- 实现失败重试
- 展示 Last Sync 和 Storage 状态

验收标准：

- 文件能上传到客户专属 Dropbox 路径
- 上传失败可重试
- Dashboard 显示 Connected / Last Sync

## Milestone 6：Processing Job 与状态监控

目标：

- 通过 Wix API 创建 Processing Job
- 查询 Job 状态
- 显示 pipeline 节点
- 展示进度百分比、预计剩余时间、输出状态

验收标准：

- Desktop App 可创建 Job
- 可展示 Ingest 到 Completed 的状态变化
- 日志能记录关键处理事件

## Milestone 7：通知与打包

目标：

- 接入邮件通知
- 完成错误状态处理
- 实现基础自动更新预留
- 打包 Windows 安装包

验收标准：

- 处理完成后客户收到邮件
- App 可安装运行
- Phase 1 可以交付真实用户试用

---

# 八、Phase 2：AI Planner 规划

Phase 2 新增真实 AI Planner，不影响 Phase 1 收费闭环。

核心模块：

- Target Database
- Equipment Profile
- Location Profile
- Weather Provider Adapter
- Moon Phase Calculator
- Target Altitude Calculator
- Historical Imaging Data
- Planner Scoring Engine
- AI Explanation Layer

输出内容：

- 推荐目标
- 推荐分数
- 可拍摄时长
- 月光影响
- 天气影响
- Seeing 影响
- 推荐滤镜组合
- 推荐曝光方案
- 推荐理由

核心原则：

> 不是列出今晚能拍什么，而是判断今晚拍什么最值得。

---

# 九、Phase 3：Auto Capture Engine 规划

Phase 3 才进入 NINA 自动化。

未来模块：

- NINA Profile Adapter
- NINA Sequence Generator
- Capture Scheduler
- Execution Monitor
- Failure Recovery
- Multi-night Accumulation Planner
- Auto Processing Trigger

边界：

- 不在 Phase 1 修改 NINA 配置
- 不在 Phase 1 自动下发 NINA Sequence
- 不在 Phase 1 控制实际拍摄设备

---

# 十、Codex 执行原则

Codex 后续执行本项目时：

- 默认工作根目录为 `D:\AIAgent\OMI Astera`
- 优先围绕 Phase 1 MVP 实现
- 不提前实现 NINA 自动化
- 不把 AI Planner 真实算法塞进 MVP
- 桌面端优先实现真实可用的本地 Agent 和同步闭环
- 云端 API 优先按 Wix HTTP Functions 设计
- 重型图像处理服务独立于 Wix
- 每次新增模块前先检查现有文件结构
- 保持架构可扩展，但不为了未来功能拖慢 MVP
