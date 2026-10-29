# Course Study Skills

[中文](README.md) | [English](README_EN.md)

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

教材默认使用简体中文讲解并保留英文知识标题；需要英文或其他语言的教材时，在请求中明确指定。作业答案的语言以题面或用户要求为准。

## 完整示例：同一讲的教材与作业

下面是一个可照着操作的假设场景，文件名和路径仅作示例，仓库不附带这些课程材料。假设第五讲讲条件概率，作业允许提交 Markdown；请替换成你的实际目录、题面与提交要求。

### 1. 准备资料，生成教材

将本讲资料放在同一个目录，保留原文件：

```text
/courses/probability/lecture5/
├── lecture.pdf        # 课件：定义、公式与课堂例题
├── transcript.txt     # 课堂转录，可能存在识别错误
├── demo.py            # 课堂示范代码
└── homework.pdf       # 本讲作业与提交要求
```

在 Codex 中发送：

```text
使用 $learning-notes，以 /courses/probability/lecture5 为本次工作范围，
阅读其中全部相关资料，生成能教懂初学者的完整 HTML 教材。
核对课堂转录，沿用课件的英文标题、记号和方法，保留来源定位。
可参考 homework.pdf 确定需要掌握的能力，本次只制作教材。
教材与来源索引放在该目录的 textbook/ 内，所有草稿也留在 lecture5 内。
```

预期得到 `textbook/index.html` 和 `textbook/textbook-index.json`。前者用于阅读，后者记录知识块的位置、相关来源及文件指纹；需要拆章或外部图片时才增加 `chapters/` 和 `assets/`。无法核实的内容应记为缺口，不能为了声称完整而编造结论。

先打开 HTML 检查教材是否覆盖本讲。以后可以在同一会话或新会话中继续；复用依靠目录内保存的教材与索引，不依赖前一次聊天记忆。

### 2. 用已有教材完成作业

发送第二条请求：

```text
使用 $kill-your-quizs，在 /courses/probability/lecture5 内完成 homework.pdf。
优先查阅 textbook/ 中已有的教材，按题号使用本课程的记号和方法。
先核对本次题面、评分要求与必要输入；需要课堂代码时读取 demo.py。
本例题面允许 Markdown，请只将必要答案写入 submit/answer.md。
全部输出留在 lecture5 内。
```

作业 skill 会先读题，再通过教材索引定位，例如查找 `Conditional probability（条件概率）`，读取相关段落及必要的前置解释，检查对应教材页和原资料的指纹。若本题给出 `P(A ∩ B) = 0.12`、`P(B) = 0.4` 并要求公式与结果，答案可写为 `P(A | B) = P(A ∩ B) / P(B) = 0.3`；无需把整章教学内容附进答案。证明题、解释题或实验题仍须保留题目要求的步骤与依据。

当教材有足够且适用的依据时，无需重新提取全部课件。题面、原始数据、指定代码和实际运行结果仍须按题目核对；教材不会替代这些输入。

### 3. 处理来源变化与缺口

假设老师替换了 `lecture.pdf`，更正了一个例子的条件。再次做作业时，可以明确说明：

```text
使用 $kill-your-quizs，继续在 /courses/probability/lecture5 内核对 homework.pdf。
lecture.pdf 已替换为老师更正后的版本。请核对受影响题目，必要时回查该课件，
更新 submit/answer.md；本次不更新教材。
```

相关来源的指纹变化会提示回查。skill 应核对受影响段落，使用有依据的更正完成作业；其他仍适用的内容可继续复用。教材未覆盖某题或没有索引时，也可直接查对应原资料，无需先重做整本教材。新增勘误文件应在请求中指出，因为旧索引的指纹只能检查它已经记录的文件。

希望以后作业也复用更新后的教材，再单独发送：

```text
使用 $learning-notes，更新 /courses/probability/lecture5/textbook/ 中的教材。
重新盘点 lecture5 内的资料，根据新版 lecture.pdf 核对并修订受影响章节，
复用仍适用的讲解，保留来源与未解决缺口，重新生成索引。
本次范围仍是 lecture5，保留原资料与已有作业答案。
```

更新需要实际核对内容；仅重新计算指纹不能证明旧正文已与新版课件一致。

### 4. 检查最终文件

单页教材的最小结果如下；只有确有需要时才增加章节、资源和题目要求的附件：

```text
/courses/probability/lecture5/
├── lecture.pdf
├── transcript.txt
├── demo.py
├── homework.pdf
├── textbook/
│   ├── index.html
│   └── textbook-index.json
├── .study-work/              # 制作过程中的草稿与提取文件
└── submit/
    └── answer.md            # 本例的唯一提交文件
```

阅读教材打开 `textbook/index.html`；提交作业只取题面要求的 `submit/` 文件。教材、索引、草稿和答案均留在 `lecture5/` 内，不会自动写入 `/courses/probability/`。若改为处理整门课程，需要明确指定课程目录作为新的范围。

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
