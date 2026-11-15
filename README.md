# boss-zhipin-assistant

BOSS 直聘自动化投递助手 —— 一个面向 WorkBuddy 智能体的求职投递 Skill。

先通过问答采集你的求职意向（城市 / 方向 / 薪资下限 / 本轮份数 / 希望投与不希望投），再由**智能体（AI 自身）对每份 JD 做语义终审**，通过后在真实页面当场点击「立即沟通」完成投递，投递结束后自动生成成果汇报页。

## 核心特性

- **零硬编码筛选**：代码里没有任何「该投 / 不该投」的写死规则，所有筛选标准都来自你在 `user_profile.json` 中填写的个人信息。
- **AI 语义终审（零外部 API）**：最终「该不该投」由运行本技能的智能体自身完成语义判断，不依赖关键词匹配，也不调用任何外部 LLM API。
- **实时单卡投递**：智能体驱动浏览器，一张卡一张卡地「表面粗看 → 点开读 JD → 语义判断 → 当场投递」，判断与投递在同一个 live 页面态完成，绝不预采集批量候选。
- **推荐页优先**：默认从 BOSS 推荐页（个性化 feed）逐条行走，穷尽后再用关键词搜索补刀。
- **安全护栏**：城市 / 薪资硬门槛、已投去重、送达回读校验、日上限检测、连续失败熔断、未知弹窗整批停手交人工。

## 前置依赖

本 Skill 必须配合以下环境使用：

1. **一台已登录 BOSS 直聘的浏览器**（Chrome / Edge / Brave 等 Chromium 内核浏览器均可）。
2. **Kimi WebBridge 插件**（本地端口 `10086`）——用于控制浏览器，复用你已有的登录态，无需另装浏览器或切换账号。

   > 安装地址：https://www.kimi.com/zh-cn/features/webbridge

> ⚠️ 本 Skill 直接操控你真实浏览器中的 BOSS 直聘账号完成真实投递，请理性使用。

## 安装

### 方式一（推荐）：一句话自动安装

无需手动下载或复制文件。复制下面这段话，直接发给 **WorkBuddy 智能体**，它会自动拉取本仓库、复制到技能目录并完成安装：

```text
请帮我安装一个 WorkBuddy 技能：boss-zhipin-assistant（BOSS直聘自动化投递助手）。
GitHub 仓库地址：https://github.com/CloudBrainNet/boss-zhipin-assistant
请把整个仓库克隆下来，复制到 ~/.workbuddy/skills/boss-zhipin-assistant 目录，
并把 user_profile.example.json 复制为 user_profile.json。
完成后告诉我安装结果，以及使用前还需要做哪些配置。
```

安装完成后，在 WorkBuddy 的「技能」页面即可看到该技能。之后你只要说「帮我投 BOSS 直聘的 XX 岗位」之类的指令，它就会自动触发。

### 方式二：手动安装

将本目录复制到 WorkBuddy 的用户技能目录：

```bash
# 克隆仓库
git clone https://github.com/CloudBrainNet/boss-zhipin-assistant.git
# 复制到技能目录（Windows 为 %USERPROFILE%\.workbuddy\skills\boss-zhipin-assistant）
cp -r boss-zhipin-assistant ~/.workbuddy/skills/boss-zhipin-assistant
# 复制个人档案模板
cp ~/.workbuddy/skills/boss-zhipin-assistant/user_profile.example.json \
   ~/.workbuddy/skills/boss-zhipin-assistant/user_profile.json
```

## 使用

> 💡 **最快上手**：安装后，直接对 WorkBuddy 智能体说一句话，例如「帮我在 BOSS 直聘上投 XX 方向的岗位，月薪 ≥7K」，它会通过问答采集你的求职意向、自动生成个人档案并开始投递——**不需要你手动编辑任何文件**。

### 1. 填写个人档案（可选，也可交给智能体）

复制技能目录下的 `user_profile.example.json` 为 `user_profile.json`，然后填写。重点是 `role_summary`（一句话自述求职方向，AI 审核的核心依据）、`prefer` / `avoid`（希望投 / 不希望投清单）。文件内含示例模板，全部字段为自由文本，换一个求职者只需改这个文件，代码一行不动。

> ⚠️ `user_profile.json` 已加入 `.gitignore`，不会提交到仓库，请放心填写真实信息。

### 2. 环境准备

打开常用浏览器 → 确认已安装并连接 Kimi WebBridge 插件 → 登录 BOSS 直聘账号。

### 3. 运行

实时逐条行走投递（推荐路径）：

```powershell
$skill = "$HOME\.workbuddy\skills\boss-zhipin-assistant"

# ① 进 BOSS 推荐页，呈现下一张岗位卡的表面（标题/薪资/城市/行业）
python "$skill\scripts\_live_driver.py" walk
# ② 表面命中 → 打开它读 JD（一次只开一张）
python "$skill\scripts\_live_driver.py" open <jobId>
# ③ 智能体读 JD 后若 APPROVE，当场投递
python "$skill\scripts\_live_driver.py" deliver <jobId> [公司] [薪资] [行业] [方向]
# ④ 投完/略过 → 推进到下一张卡
python "$skill\scripts\_live_driver.py" walk --next
```

收尾闭环（生成投递成果汇报 + 打赏二合一页）：

```powershell
python "$skill\scripts\phase_stream.py" --mode report --workdir .
```

详细命令说明与「推荐页优先」「单卡游标制」等规则，见 [SKILL.md](./SKILL.md)。

## 目录结构

```
boss-zhipin-assistant/
├── SKILL.md               # 技能说明（完整使用手册）
├── user_profile.example.json  # ★ 个人档案模板（复制为 user_profile.json 后填写）
├── boss_applied.json      # 历史投递样本占位（不参与运行）
├── assets/                # 赞赏码图片（可选，默认不含真实收款码）
├── scripts/               # 核心脚本
│   ├── _live_driver.py    # 实时单卡投递驱动（walk/open/deliver/reject）
│   ├── phase_stream.py    # 投递原语 + 收尾汇报/核对/诊断
│   ├── webbridge_client.py# WebBridge 共享客户端
│   ├── config_v3.py       # 档案加载 + 薪资解析 + 动态审核提示词
│   ├── env_check.py       # 环境检测（浏览器/WebBridge/登录态）
│   └── cleanup.py         # 缓存清理
└── references/            # DOM 结构、操作手册、坑记录、薪资解密等参考
```

## 免责声明

- 本工具仅用于辅助求职者更精准地投递岗位、解放重复性机械操作，**请理性使用、对自己负责，也对招聘方负责**。
- 请勿用于无脑海投、虚假投递、绕过平台反滥用机制等行为。
- 使用本工具产生的任何后果（包括但不限于账号风控、封禁、求职结果）由使用者自行承担。
- 本项目与 BOSS 直聘（北京华品博睿网络技术有限公司）无任何关联，仅作为第三方自动化工具供学习交流。

## License

MIT License
