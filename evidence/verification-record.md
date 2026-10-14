# 核验记录

核验日期：2026-10-14（Asia/Shanghai）。

- 环境：Windows，Git 2.54.0.windows.1，Python 3.13.13。
- 归因条件：start 到 capture 期间只有脚本模拟的 Agent 写文件；不是产品内置撤销测试。
- 自动化：12 项真实临时 Git 仓库测试通过。初次通过日志 03-tests.txt；最终复核 05-final-tests.txt。
- 命令行入口：start / capture / undo 三步退出码均为 0，见 06-cli.txt。
- 演示：可运行 app.py 输出 102 → 1001 → 102；7 个演示断言通过。
- 暂存区：原 index 按字节一致，git diff --cached 输出一致；原暂存和未暂存内容均保留。
- 未跟踪文件：用户原有 notes.txt 保留；选中 Agent 新建文件删除。
- 选择性：保留未选中 feature.txt；后续再改 feature.txt 后，拒绝撤销且未写工作文件。
- 前后快照树 SHA、index SHA256、完整 diff 和命令退出码均在 04-demo-terminal.txt。
- 红灯记录：01-red.txt 为缺模块的初始错误；02-red-stub.txt 为占位实现 12 项错误。不是成功记录。
- 未实测：真实 Codex/Claude Code 会话、生产仓库、其他操作系统、hunk 级选择、复杂 attributes/LFS/过滤器、并发写入、断电恢复。

内容去重：用户指定续写已确认的 Git 教程；对照 chat-worktree，新增为脏工作区基线、差分快照与选择性反向补丁，不重写多 Agent worktree 教程。已核对本号安装包历史；旧会话接口只有引用占位，不能称完整历史零遗漏。

发布状态：draft；没有发布到 X，没有读取 Drive/Sheets。

来源（2026-10-14 核验）：
- https://git-scm.com/docs/git-diff （状态之间的差异）
- https://git-scm.com/docs/git-apply （reverse/check；默认作用于工作区）
- https://git-scm.com/docs/git （GIT_INDEX_FILE 环境变量）

配图对应句：开工前保存工作区基线，收工后比较增量；按文件选择撤销，保留原有工作。
配图为真实日志摘录的生成排版，不是终端截图。错误初稿已弃用，不作为交付。
