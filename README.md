# HomeCopy 仓库说明

这是 HomeCopy 的统一仓库。HomeCopy 是一个用于局域网内在不同机器之间发送短文本，并可直接写入对方剪贴板的桌面工具。

当前仓库结构不是把所有源码平铺在根目录，而是把真正项目内容放在 `HomeCopy/` 子目录中。

## 目录结构

```text
/Users/tommyclaw/OMI/Tools
├── AGENTS.md
├── README.md
└── HomeCopy/
    ├── Common/
    │   └── homecopy_shared/
    ├── MacOS/
    │   ├── homecopy/
    │   ├── package_macos.command
    │   └── requirements.txt
    └── Windows/
        ├── homecopy/
        ├── build_client.bat
        ├── scripts/
        └── requirements.txt
```

## 平台说明

### macOS

- GUI 客户端与本地 relay server 都在 `HomeCopy/MacOS/homecopy/`
- 打包脚本为 `HomeCopy/MacOS/package_macos.command`
- 打包后生成 `.app`

### Windows

- GUI 客户端与本地 relay server 都在 `HomeCopy/Windows/homecopy/`
- Windows 侧保留 `.bat` 与 `scripts/` 作为 build / start / stop 入口
- 打包后生成 `.exe`

### Common

`HomeCopy/Common/homecopy_shared/` 用来放跨平台共享逻辑，例如：

- 启动策略
- 共享主窗口
- 历史记录 UI 逻辑
- 统一格式化与状态展示

## 当前功能概览

- 局域网自动发现 relay server
- 找不到远端 server 时，可在客户端启动本地 relay
- 文本发送、接收与历史记录
- 本地剪贴板写入
- 设备列表与在线状态
- 头部区分 client 状态与 local relay 状态
- 本地 relay 的启动、停止与客户端数量显示

## 开发建议

1. 修改前优先判断是否能放进 `Common/`
2. 平台特有代码只保留与系统 API 相关的差异
3. UI 与业务行为尽量保持 Mac / Windows 一致
4. Windows 版本改动后，记得同步到共享目录，供 Windows 机器 build

## 常用命令

### macOS 打包

```bash
bash /Users/tommyclaw/OMI/Tools/HomeCopy/MacOS/package_macos.command
```

### Python 语法检查

```bash
python3 -m py_compile /Users/tommyclaw/OMI/Tools/HomeCopy/Common/homecopy_shared/main_window.py
```

### Windows 工程同步

```bash
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'MacOS/build/' \
  --exclude 'MacOS/dist/' \
  --exclude 'Windows/build/' \
  --exclude 'Windows/dist/' \
  /Users/tommyclaw/OMI/Tools/HomeCopy/ \
  /Volumes/OMI-WinDev/AIAgent/HomeCopy/
```

## 备注

- 仓库中可能会出现平台打包产物、日志、共享盘同步目录等上下文，请在修改时注意区分“源码”和“运行态文件”。
- 如果任务明确要求“以 Mac 当前版本为准对齐 Windows”，优先保证功能和界面行为一致，再处理内部代码整理。
