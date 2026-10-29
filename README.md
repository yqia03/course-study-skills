# Course Study Skills

把课程资料整理成能学懂的教材，再用同一套教材完成作业。两个 skill 保持独立，采用相同的目录约定和来源索引。

| Skill | 用途 | 默认成品 |
| --- | --- | --- |
| [learning-notes](skills/learning-notes/SKILL.md) | 核验课程资料，生成面向初学者的完整 HTML 教材 | `textbook/index.html` 与 `textbook/textbook-index.json` |
| [kill-your-quizs](skills/kill-your-quizs/SKILL.md) | 按题目和课堂方法完成作业，保持最小完整答案 | `submit/` 内的必要文件 |

## 一起使用

先制作教材：

```text
用 $learning-notes，把 /课程/lecture5 内的全部相关资料做成完整教材。
```

以后做同一范围的作业：

```text
用 $kill-your-quizs，在 /课程/lecture5 内完成 homework.pdf，按题面格式交付。
```

作业 skill 会先读本次题面与必要输入，再查教材索引，只提取相关知识块。来源或教材页发生变化、内容有缺口或题目要求原始代码时，回查对应资料。没有教材时可直接完成作业，不要求先生成整本教材。

这样减少的是重复提取和无关正文进入上下文的机会；实际节省取决于资料大小、题目范围和来源变化情况，不承诺固定的时间或 token 降幅。

## 目录边界

```text
lecture5/
├── lecture.pdf
├── homework.pdf
├── textbook/
│   ├── index.html
│   ├── textbook-index.json
│   ├── chapters/             # 需要拆章时
│   └── assets/               # 需要外部资源时
├── .study-work/              # 草稿、提取文本和构建清单
└── submit/                   # 必要答案与附件
```

指定 `lecture5/` 就在其中工作，不能自动到父目录建立教材、缓存或答案目录。脚本检查解析 `..` 和符号链接后的实际路径。用户明确指定其他输入或输出位置时，按对应授权分别处理，不扩大其他文件的范围。

完整教材指本次授权范围的完整教学内容。全课程教材应以用户明确指定的课程目录为根；读取其他位置的共享教材需要明确指定其位置，作业输出仍留在当前任务目录。

## 安装

```bash
git clone https://github.com/yqia03/course-study-skills.git
cd course-study-skills
```

每个 `skills/<技能名>/` 都是可单独安装的完整目录，包含所需脚本、引用文件及许可证，不依赖另一个 skill 的安装位置。将需要的整个目录复制到你的技能目录；Codex 默认位置为 `~/.codex/skills/`。如果已安装同名 skill，先备份或对比自己的修改，再更新。

例如，以下命令从仓库根目录执行；遇到已有安装会停止，不覆盖：

```bash
python3 - <<'PY'
import os
import shutil
from pathlib import Path

target = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
names = ('learning-notes', 'kill-your-quizs')
existing = [str(target / name) for name in names if (target / name).exists()]
if existing:
    raise SystemExit('先备份或对比已有安装：' + ', '.join(existing))
target.mkdir(parents=True, exist_ok=True)
for name in names:
    shutil.copytree(Path('skills') / name, target / name)
PY
```

打开新会话后使用原有的 `$learning-notes`、`$kill-your-quizs` 名称。

## 脚本与兼容性

脚本需要 Python 3.10+，只使用标准库；读取 PDF、Office、媒体及浏览器视觉核验依赖所在环境已有工具。构建器保留原有的离线搜索、折叠目录、公式和图像规则。

- [构建与来源映射](skills/learning-notes/references/textbook-handoff.md)：构建时传 `--scope-root` 与 `--catalog`，产生轻量索引。
- [按需查阅](skills/kill-your-quizs/references/textbook-reuse.md)：按标题、别名查找并读取单个知识块，检查相关页面与来源指纹。
- 旧 HTML 无索引也能定向查阅，但需回查对应来源。旧文件不会被自动删除或移动。
- `coverage` 记录范围完成情况；文件指纹只证明版本是否变化，不证明教学结论正确。
- 更新前的构建命令需要补上 `--scope-root`；默认成品由根目录的 `<目录名>-学习教材.html` 改为 `textbook/index.html`。

从仓库根目录运行验证：

```bash
python3 -B -m unittest discover -s tests -v
```

仓库只收录技能与合成测试资料，不包含课程材料、真实作业或个人学号。身份字段仅在题面要求时使用用户明确提供的值。

## 来源与许可证

`kill-your-quizs` 基于 [vect-G/lecture-to-hw](https://github.com/vect-G/lecture-to-hw) 的本地修订版，保留原有 MIT 版权声明。仓库采用 [MIT License](LICENSE)，每个可独立安装的 skill 也带有许可证副本。
