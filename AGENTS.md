# HomeCopy 工作约定

本仓库用于维护 HomeCopy 的整体工程。仓库根目录下实际项目位于 `HomeCopy/` 目录内，里面按平台拆分为：

- `HomeCopy/Common/`: 跨平台共享逻辑与共享 UI
- `HomeCopy/MacOS/`: macOS 客户端与本地 relay server 工程
- `HomeCopy/Windows/`: Windows 客户端与本地 relay server 工程

## 修改原则

1. 优先复用 `HomeCopy/Common/` 中的共享逻辑，不重复在两个平台各写一份。
2. 如果是平台特有实现，例如：
   - macOS 的原生热键注册
   - Windows 的原生全局热键与批处理构建脚本
   允许保留各自平台差异，但业务行为和 UI 表现应尽量一致。
3. 不随意改动 `build/`、`dist/`、日志、运行态配置文件，除非当前任务明确要求。
4. 修改 Windows 版本后，应同步到 `/Volumes/OMI-WinDev/AIAgent/HomeCopy`，方便在 Windows 机器上一键 build。

## 常用路径

- 仓库根目录：`/Users/tommyclaw/OMI/HomeCopy`
- 项目根目录：`/Users/tommyclaw/OMI/HomeCopy/HomeCopy`
- macOS 打包脚本：`/Users/tommyclaw/OMI/HomeCopy/HomeCopy/MacOS/package_macos.command`
- Windows 共享目录：`/Volumes/OMI-WinDev/AIAgent/HomeCopy`

## 常用操作

### 1. macOS 重打包

在仓库根目录执行：

```bash
bash /Users/tommyclaw/OMI/HomeCopy/HomeCopy/MacOS/package_macos.command
```

产物默认位于：

```text
/Users/tommyclaw/OMI/HomeCopy/HomeCopy/MacOS/dist/HomeCopyClient-macOS/HomeCopyClient.app
```

### 2. Windows 工程同步

推荐同步命令：

```bash
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'MacOS/build/' \
  --exclude 'MacOS/dist/' \
  --exclude 'Windows/build/' \
  --exclude 'Windows/dist/' \
  --exclude 'MacOS/.venv-packaging/' \
  --exclude 'Windows/.venv-packaging/' \
  --exclude 'MacOS/logs/' \
  --exclude 'Windows/logs/' \
  --exclude 'MacOS/configs/clients/client.local.json' \
  --exclude 'Windows/configs/clients/client.local.json' \
  /Users/tommyclaw/OMI/HomeCopy/HomeCopy/ \
  /Volumes/OMI-WinDev/AIAgent/HomeCopy/
```

### 3. Windows 构建

同步完成后，在 Windows 机器上运行：

```text
/Volumes/OMI-WinDev/AIAgent/HomeCopy/build_client.bat
```

## 验证重点

涉及客户端启动流程时，优先检查以下路径：

1. 局域网发现到远端 server
2. 无远端 server 时打开 setup dialog
3. 选择 `Start Local Relay`
4. 主窗口头部是否同时显示 client 区和 local relay 区
5. `Stop Server / Start Server` 是否能正常切换
6. 真正退出应用时，本地拉起的 server 是否一起停止

## 提交建议

- 提交信息尽量描述“做了什么行为修复或对齐”，避免只写笼统的 `update`。
- 涉及跨平台行为调整时，优先说明是否同时影响 Mac 和 Windows。
