# AI 改坏代码，怎样只撤销它的改动？

@ChuyiChat 配套 Git 实操 Demo：在已有暂存修改、未暂存修改和未跟踪文件时，保存基线、捕获增量，并按文件选择性撤销。

**真实 Git 实验；Agent 写文件由脚本模拟，没有调用 Codex / Claude Code。教学实现，不是生产级备份工具。**

## 下载与运行

[点击下载完整实验包 ZIP](https://github.com/waiting9527/chuyichat-git-demo/raw/refs/heads/main/chuyichat-git-demo-public.zip)

解压后在含 demo.py 的目录打开终端。也可通过 Code → Download ZIP 下载仓库源码。

依赖：Git、Python 3；不需要第三方 Python 库。实测 Windows / Git 2.54.0.windows.1 / Python 3.13.13。

```powershell
python -X utf8 demo.py
python -X utf8 -m unittest discover -s . -v
python -X utf8 check_cli.py
```

Demo 每次新建 runs/随机编号/repo，不操作现有项目；运行后保留沙箱与快照，供检查。不要将生成的 runs 目录发布到仓库。

## 已验证

12 项自动化测试通过，7 项演示断言通过；程序输出 102 → 1001 → 102。保留用户原有暂存、未暂存、未跟踪内容；原索引字节一致。未选中的 Agent 文件修改保留；文件后续被编辑或暂存区变化时拒绝操作。

## 教程与证据

- [完整中文教程](article.md)
- [真实演示输出（本机路径已脱敏）](evidence/04-demo-terminal.txt)
- [最终测试记录（本机路径已脱敏）](evidence/05-final-tests.txt)
- [验证边界](evidence/verification-record.md)
- [5:2 文章封面](cover-5x2.png)
- [4:3 正文教程图](tutorial-4x3.png)
- x-article-richtext.html：下载后用浏览器打开，复制富文本；代码块粘贴兼容性未在 X 实测。

## 边界

没有事前基线不能可靠归因。start 与 capture 之间只允许一个写入者；检查和应用不是跨进程原子事务。按文件选择，不按 hunk。Agent 改动暂存区或 HEAD 时停止，不强行覆盖。全程不使用 reset --hard。

忽略文件、空目录、权限/模式变化、复杂 attributes/过滤器、LFS、子模块、符号链接与特殊索引设置不在保证范围。演示环境为 LF、关闭自动换行转换。基线将文件内容写入本地 Git 对象库，谨慎处理敏感文件。详见完整教程。

公开副本未附本机沙箱 .git、原索引或内部交付记录；原始记录留存本地。公开日志仅替换本机路径，未修改测试数量、时间、结果或补丁。重新运行 demo.py 即可生成完整新沙箱。
