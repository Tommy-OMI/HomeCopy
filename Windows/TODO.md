# OMI Astera 待办清单

## 总目标

将 OMI Astera 建设成面向天文摄影用户的可收费 MVP 桌面控制平台：

```text
Wix OAuth 登录
  -> 通过 Wix HTTP Functions 激活 License
  -> Dropbox 共享目录 / 本地同步目录关联
  -> 检测 NINA 等拍摄软件输出到本地 Dropbox 目录中的 FITS 文件
  -> 本地跟踪任务 / 文件状态
  -> Dropbox Desktop 自动同步到预处理机器
  -> Python Processing Server 创建并执行预处理任务
  -> 交付 Master 输出文件并发送邮件通知
```

Phase 1 必须聚焦可收费的同步与云端处理闭环。AI Planner 和 NINA 自动化需要保留架构边界，但不在 MVP 中完整实现。

---

## Phase 1：MVP 桌面端 + 云端处理闭环

### Milestone 1：桌面 App 骨架

目标：创建可本地运行的 Electron 桌面 App，并展示 OMI Astera 控制台 Dashboard。

- [x] 创建 Electron + React + TypeScript + Vite 项目。
- [x] 构建主窗口和 preload 安全桥接。
- [x] 基于 `prototype.png` 实现专业暗色 Dashboard UI。
- [x] 实现左侧导航骨架。
- [x] 添加 Dashboard 状态卡、当前项目、处理 pipeline、AI Planner 占位和 Quick Actions。
- [x] 验证 `npm run typecheck`。
- [x] 验证 `npm run build`。
- [x] 提交并推送稳定桌面骨架。

### Milestone 2：本地数据与项目系统

目标：从静态 UI 过渡到本地持久化状态和项目目录管理。

- [x] 添加 SQLite 本地数据库。
- [x] 创建 `settings`、`license_cache`、`projects`、`files`、`jobs`、`logs` 数据表。
- [x] 添加 Project Manager 服务。
- [x] 实现 New Project 弹窗。
- [x] 创建本地项目目录结构。
- [x] 写入 `project.omi.json`。
- [x] 实现 Open Project。
- [x] 从本地数据读取 Dashboard 项目状态。
- [x] 添加本地日志记录。
- [ ] 核心 MVP 闭环稳定后，如有需要再添加项目列表 / 项目 Profile 页面。

### Milestone 3：登录、License 与 Dropbox 关联

目标：通过 Wix 完成用户认证，并激活可返回用户专属 Dropbox 共享目录的付费 License。

- [x] 实现 Wix Headless OAuth 2.0 + PKCE 登录流程。
- [x] 使用 anonymous visitor token 创建 Wix redirect session。
- [x] 打开 Wix 托管登录 / 注册页，而不是网站首页。
- [x] 捕获 `omiastro://auth` 和 Wix auth callback URL。
- [x] 使用 authorization code 换取 token。
- [x] 拉取 Wix member profile。
- [x] 显示登录用户头像和昵称。
- [x] 添加账号下拉菜单：Profile、Settings、Logout。
- [x] 添加 Settings 页面。
- [x] 添加 License 输入 UI。
- [x] 添加 Wix HTTP Function License 激活客户端。
- [x] 本地保存 License 状态。
- [ ] 最终确认 Wix License 激活接口的精确返回契约。
- [x] 保存返回的 Dropbox shared link 并暴露关联状态。
- [x] 允许用户选择或确认与 shared link 对应的本地 Dropbox 同步目录。
- [ ] 在 Dashboard 上显示激活状态和 Dropbox 关联状态。
- [ ] 添加 token refresh 流程。
- [ ] 强化 logout / session restore 行为。

### Milestone 4：FITS 文件检测与 Local Agent

目标：检测 NINA 或其他拍摄软件在本地 Dropbox 同步目录下生成的 FITS 文件。

- [x] 从 Dropbox `info.json` 检测本地 Dropbox 同步目录。
- [x] 添加 Files & Syncing 页面。
- [x] 显示 Dropbox 同步根目录下的一级拍摄文件夹。
- [x] 递归统计每个文件夹中的 `.fit` / `.fits` 文件。
- [x] 添加 Local Agent 服务。
- [x] 添加稳定文件检测。
- [x] 将检测到的 FITS 文件索引到 SQLite。
- [x] 跟踪文件状态：detected、stable、queued、synced、error。
- [x] 从索引的 FITS 文件更新 Dashboard light frame count 和 total size。
- [x] 为检测和索引写入本地日志。
- [x] 添加手动 rescan 操作。
- [x] 添加后台 watch mode。
- [ ] Files & Syncing 每个目标文件夹按通道显示 FITS 数和曝光时长。
- [ ] 添加 `omi_complete.json` 标记生成 / 识别 UI，用于确认目标已拍摄完成。

### Milestone 5：Dropbox 本地同步适配

目标：将 Dropbox Desktop 作为 MVP 文件传输方案，同时让实现保持可替换。OMI Astera 不调用 Dropbox API 上传 / 下载，所有同步交给 Dropbox 客户端。

- [ ] 定义 `SyncAdapter` 接口。
- [ ] 实现 MVP 用的 Dropbox local-folder adapter。
- [ ] 将 Dropbox shared link 与检测到的本地 Dropbox 路径关联。
- [ ] 在处理前跟踪本地文件 readiness。
- [ ] 记录 last sync / last check 时间。
- [ ] 显示 Dropbox connected 和 association 状态。
- [ ] 添加失败 / 重试状态占位。

### Milestone 6：Python Processing Server 与 Runner 部署闭环

目标：在预处理 Windows 机器上建立可重复发布、启动、验证、观察错误的服务端闭环。服务端第一阶段用命令行启动，不注册 Windows Service。

- [x] 新增 `server/processing-server` Python CLI 骨架。
- [x] 支持 `omi-processing health`。
- [x] 支持扫描本地 Dropbox 根目录下的目标文件夹。
- [x] 支持按通道统计 FITS 数和曝光时长。
- [x] 支持 `omi_complete.json` + 文件稳定时间的 ready 判定。
- [x] 新增基础单元测试。
- [x] 新增 GitHub self-hosted runner bootstrap workflow。
- [ ] 在预处理机器创建 `D:\OMI\config\processing-server.yaml`。
- [x] Push 后确认 self-hosted runner 执行成功。
- [ ] 用真实 FITS 数据验证 scan 输出。
- [ ] 增加真实预处理 pipeline 入口。
- [ ] 增加处理日志、输出目录和失败报告。

### Milestone 7：Processing Job 与状态监控

目标：通过 Wix API 和未来 Processing Server 创建并监控云端处理任务。

- [x] 定义 Processing Job model。
- [ ] 添加用于项目 / Job 创建的 Wix API client。
- [x] 添加 Processing 页面。
- [x] 从 detected / stable FITS 文件夹创建本地处理任务。
- [ ] 轮询 Job 状态。
- [ ] 显示 pipeline 进度。
- [x] 将 Job 状态保存到 SQLite。
- [x] 记录 processing 事件日志。
- [ ] 暴露 output folder / open result 操作。

### Milestone 8：通知、打包与 MVP Ready

目标：打包可交付给第一批真实用户试用的 Windows 桌面版本。

- [ ] 添加生产构建打包。
- [ ] 添加 Windows installer 配置。
- [ ] 添加 App icon 和 metadata。
- [ ] 添加 error boundary 和用户可理解的失败状态。
- [ ] 添加基础 auto-update 占位。
- [ ] 确认云端完成后发送邮件通知。
- [ ] 验证干净安装和首次启动流程。
- [ ] 创建 MVP 测试清单。

---

## Phase 2：AI Planner

目标：推荐“今晚最值得拍什么”，而不是只列出“今晚能拍什么”。

- [ ] 定义设备 profile model。
- [ ] 定义地点 profile model。
- [ ] 添加天气 provider adapter。
- [ ] 添加月相 / 目标高度计算。
- [ ] 添加目标数据库来源。
- [ ] 添加评分引擎。
- [ ] 添加 AI explanation layer。
- [ ] 用真实 planner 输出替换 Dashboard mock 数据。

---

## Phase 3：Auto Capture Engine

目标：为未来 NINA 自动化预留能力，但不把它加入 MVP。

- [ ] 定义 NINA profile adapter 边界。
- [ ] 定义 sequence generation model。
- [ ] 定义 scheduler 和 failure recovery 概念。
- [ ] 保持 Phase 1 实现不直接控制实际拍摄设备。

---

## 当前执行队列

1. [x] 完成 Milestone 3 Dropbox association 状态。
2. [x] 将 Milestone 4 FITS indexing 写入 SQLite。
3. [x] 在 Files & Syncing 添加手动 rescan。
4. [x] 从 indexed FITS files 更新 Dashboard 统计。
5. [x] 添加后台 watch mode。
6. [x] 添加 Processing 页面骨架和 job model。
7. [x] 添加 Python Processing Server CLI 骨架和 runner bootstrap workflow。
8. [ ] 在预处理机器配置 `D:\OMI\config\processing-server.yaml` 并验证 GitHub Actions runner 日志。
9. [ ] 客户端 Files & Syncing 增加通道级 FITS 数 / 曝光时长展示。

## 提交策略

每完成一个稳定的纵向切片后提交并推送：

- Todo / documentation baseline。
- Login / License / Dropbox association 改进。
- FITS indexing / rescan。
- Dashboard stats integration。
- Background watcher。
- Processing job model。
- Processing server runner bootstrap。
