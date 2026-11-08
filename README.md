# 鸣潮声骸助手

按角色方案自动刷声骸、升级，并在每次调谐后判断该继续升级、上锁还是打废弃标记，避免把资源浪费在注定不毕业的声骸上。

运行在 [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves)（ok-ww）之上：刷本战斗、体力、背包和强化界面操作复用 ok-ww，本项目负责角色方案和判断逻辑。只通过截图识别和模拟键鼠操作游戏，不读内存、不改游戏文件。

> 使用第三方自动化工具违反《鸣潮》用户协议，有封号风险，请自行承担。

## 功能

- **角色方案**：每个角色一份方案，包含套装、刷取方式、C4/C3/C1 主词条（可多选）、必要和选要副词条、喂料优先级。
- **刷取**
  - C1/C3：刷指定无音区，可选“只用当日体力”或“当日体力 + 储存的结晶一起用完”。
  - C4：传送到指定 Boss 反复挑战。
- **升级与判断**：逐个升级背包里 0 级的目标声骸，每调谐出一条副词条就判断一次。

## 判断规则

必要词条：没有就算废；选要词条：不是必须，有更好；有效词条 = 必要 + 选要。

| 阶段 | 条件 | 结果 |
|---|---|---|
| 任何一步 | 还缺的必要词条数 > 剩余槽数 | 废弃 |
| 0 级 | 主词条不在所选范围 | 废弃，不花资源 |
| 第 1~2 条 | — | 继续 |
| 第 3 条后 | 必要 ≥ 1 且 有效 ≥ 2 | 继续，否则废弃 |
| 第 4 条 | 必要 | 继续 |
| | 选要 | 继续；前三条为 1 必要 1 选要且该必要是最低 1 档时废弃 |
| | 无效 | 前三条已三有效才继续，否则废弃 |
| 第 5 条后 | 必要词条全部都有 且 有效 ≥ 3 | 上锁 |
| | 否则 | 废弃 |

副词条档位表见 `echo_helper/stats.py`。

## 安装

1. 准备 ok-ww 源码与 Python 3.12 环境（ok-ww 只支持 3.12）：

   ```powershell
   git clone https://github.com/ok-oldking/ok-wuthering-waves.git D:\ok-wuthering-waves
   conda create -y -p D:\ok-wuthering-waves\.venv python=3.12
   cd D:\ok-wuthering-waves
   .\.venv\python.exe -m pip install -r requirements.txt
   ```

2. 把本项目的任务入口装进 ok-ww：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\install_to_okww.ps1 -OkwwPath D:\ok-wuthering-waves
   ```

   入口文件只引用本仓库代码，之后更新本仓库无需重新安装。

## 使用

1. 建角色方案：

   ```powershell
   D:\ok-wuthering-waves\.venv\python.exe .\tools\profile_editor.py
   ```

   三页依次填写：角色与刷取 → 主词条 → 副词条，保存后生成 `profiles/<角色名>.json`。

2. 游戏内准备（只需一次，游戏会记住）：
   - 背包声骸页筛选：五星 + 该角色套装 + 所需 COST（建议同时筛选主词条），排序选“等级”从低到高。
   - 培养页齿轮（强化设置）中开启“阶段放入”和“同时调谐”。

3. 以管理员身份启动 ok-ww（`D:\ok-wuthering-waves\.venv\python.exe main.py`），在任务列表中选择“🎯 声骸助手”，选好角色方案后开始。

## 喂料与安全

- 废弃的声骸由脚本打上游戏自带的废弃标记，毕业声骸上锁。
- “优先用已废弃的声骸”要求强化设置里存在“仅使用已弃置声骸”这类选项；找不到时任务会截图并停止，不会改用其他声骸。

## 开发

```powershell
python -m unittest discover -s tests -t .
```

`echo_helper/judge.py`、`parse.py`、`profile.py` 不依赖游戏，可直接测试；`okww_task.py` 只能在 ok-ww 进程中运行。

## 许可

AGPL-3.0（与 ok-ww 一致）。
