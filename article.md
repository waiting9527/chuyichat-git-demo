# AI 改坏代码，怎样只撤销它的改动？

用 Codex、Claude Code 改代码前，你可能已经有三种工作：写了一半但没暂存的代码、已经 git add 的代码，以及还没进 Git 的新文件。

这时直接把 `git diff HEAD` 存成补丁，再反向应用，会把自己的修改也算进去。Git 的 diff 不记录“谁写的”，只能比较状态。解决办法是：开工前保存工作区基线，收工后再保存一次，只比较这两个状态。

这份 Demo 用真实 Git 仓库验证这条链路。Agent 的写文件动作由脚本模拟，没有调用 Codex 或 Claude Code，也不能据此宣称两款产品的内置撤销功能已经通过测试。

1. 准备一个能放心试错的环境

安装 Git 和 Python 3，在终端确认：

```powershell
git --version
python --version
```

下载 ZIP，解压后在 `chuyichat-git-demo` 文件夹打开终端，运行：

```powershell
python -X utf8 demo.py
python -X utf8 -m unittest discover -s . -v
```

不用安装 Python 第三方库。每次运行 Demo 都创建新的 `runs/随机编号/repo`，不会拿你现有的项目做试验。实测环境是 Windows、Git 2.54.0.windows.1、Python 3.13.13；其他系统未实测。

2. 先看懂“原有工作”

Demo 先提交一个能运行的 Python 程序，再人为制造脏工作区：

- `app.py`：`TAX = 2` 已暂存；文件末尾还有没暂存的用户注释。
- `notes.txt`：用户原来的未跟踪草稿。

真实输出：

```text
MM app.py
?? notes.txt
```

`MM` 的第一列表示暂存区有变化，第二列表示工作区又有变化。此时运行 `app.py` 输出 `102`。

3. 在让 Agent 开工之前保存基线

包里的 `guard.py` 提供三个动作：`start`、`capture`、`undo`。以你自己创建的练习仓库为例，先进入解压目录，再运行下面命令。把路径替换成你的练习路径；会话目录必须在仓库外，并且尚不存在：

```powershell
python guard.py start --repo "D:/practice/repo" --session "D:/practice/session-001"
```

它复制真实索引到临时文件，通过 `GIT_INDEX_FILE` 让 Git 只操作临时索引，然后执行 `git add -A`、`git write-tree`。这样，基线包含已跟踪文件和未被忽略的未跟踪文件，而原来的暂存区保持不变。

快照用独立的 `refs/agent-demo/...` 引用保存，不提交到当前分支。会话目录另外保存原索引、文件哈希和状态记录。它会在本地 Git 对象库写入文件内容，因此不要在含敏感文件的真实仓库里直接照跑。

4. 让 Agent 工作，再捕获本轮增量

这段时间暂停自己的编辑、格式化器和其他 Agent。让唯一的写入者只修改文件，不执行 add、commit、切分支等 Git 操作。提示词只是约定，脚本还会检查索引和 HEAD 是否改变。

Demo 模拟三项修改：把计算逻辑改坏、新建 `agent-new.txt`、打开 `feature.txt` 中的功能。程序输出由 `102` 变为 `1001`。

收工后执行：

```powershell
python guard.py capture --repo "D:/practice/repo" --session "D:/practice/session-001"
```

打开会话目录的 `candidate.patch` 检查。原来的税率修改和用户注释已经在 before 中，因此它们不应作为新增/删除行出现在本轮增量里；出现在上下文行是正常的。

核心差别是：

```text
git diff HEAD       = 自己原有修改 + 本轮修改
before → after      = 这段时间内的候选修改
```

只有确认这段时间没有其他写入者，才能把候选修改归于本轮 Agent。没有 before，就无法靠一个混合 diff 可靠还原作者；先备份现场，再人工审查，别强行自动撤销。

5. 只撤销选中的文件

Demo 选择撤销坏掉的 `app.py` 和 Agent 新建的文件，保留 `feature.txt` 的功能修改：

```powershell
python guard.py undo --repo "D:/practice/repo" --session "D:/practice/session-001" app.py agent-new.txt
```

脚本先确认 HEAD、原索引未变，且选中文件的当前内容仍等于 capture 时的内容。然后生成 `selected.patch`，依次执行：

```powershell
git apply --reverse --check selected.patch
git apply --reverse selected.patch
```

上面两条是底层原理；日常练习请用脚本入口，因为单独执行它们没有脚本的文件哈希检查。这里不使用 `--index` 或 `--cached`，让反向补丁只作用于工作区。Demo 全程没有使用 `reset --hard`。

这个版本按文件选择：可以撤销 A、保留 B；不能在同一个文件中勾选某几个 Agent hunk。选中 app.py 会撤销该文件捕获到的全部增量，保留开工前就存在的用户内容。

6. 验收看内容和暂存区，不看“是否变干净”

真实演示输出：

```text
102 → 1001 → 102

MM app.py
 M feature.txt
?? notes.txt

PASS original index byte-for-byte unchanged
PASS staged diff unchanged
RESULT: 7/7 demo assertions passed
```

`MM app.py` 还在，才说明用户原来的两层工作没有被清掉。`notes.txt` 保留；选中的 Agent 新文件删除；未选中的功能修改保留。脚本对文件字节、原索引字节和暂存 diff 做了断言。

自动化测试真实结果是 12 项通过，覆盖：完整撤销、选择性保留、已有未跟踪文件被改、删除文件恢复、二进制新增文件撤销、后续同文件编辑、后续其他文件编辑、Agent 暂存、用户后续暂存、非法选择、缺失基线和重复撤销。完整记录在 ZIP 的 `evidence/03-tests.txt`，演示原始终端输出在 `evidence/04-demo-terminal.txt`。

7. 遇到拒绝，停下来检查

Demo 在 capture 后又修改 `feature.txt`，撤销时真实返回：

```text
EXPECTED REFUSAL: file changed AFTER capture: feature.txt
PASS refusal wrote no working files
```

同一文件后来又写了东西，即使 Git 觉得某个补丁还能套上，也先停止。若暂存区被 Agent 或用户改过，也停止；这份 Demo 不自动拆分混合暂存内容。不要为了让它通过而强制恢复索引或覆盖文件。

适用边界：这是练习工具，不是生产级备份。只验证普通仓库、普通文件、LF 内容和关闭自动换行转换的演示环境；支持的二进制场景也仅按测试记录理解。忽略文件、空目录、权限/模式变化、全局或仓库外 attributes、过滤器、LFS、子模块、符号链接、特殊索引配置不在保证范围。原有忽略文件不会进入快照，不能用它恢复 `.env` 等文件。仓库内 `.gitattributes`、已跟踪子模块/符号链接等部分情况会主动拒绝，但并未穷尽检测所有特殊环境。

检查和应用不是跨进程原子事务；期间必须停下其他写入者。断电、磁盘失败、应用后校验失败时保留现场和会话目录，先人工排查；别反复重试。目录改名按删除/新增处理，需成对审查。不要随意清理会话目录与快照引用，基线包含旧文件内容；不要把这些对象或证据包直接推到公开远端。解压后应重新跑 Demo，旧会话记录含生成机器的绝对路径，不能直接当成新会话续用。

这套方法的价值是把“选择性撤销”变成可检查的过程：有基线，有增量，有预检，有保留原有工作的验收。

参考：[Git diff](https://git-scm.com/docs/git-diff)、[Git apply](https://git-scm.com/docs/git-apply)、[GIT_INDEX_FILE](https://git-scm.com/docs/git)。核验日期：2026-10-14。本文实测限于上述脚本、环境与测试场景。
