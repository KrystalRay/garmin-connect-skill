---
name: garmin-connect
description: "Garmin Connect integration for OpenClaw. Sync Garmin data to workspace xlsx and infer daily muscle group (胸/背/肩膀/臀腿) from workouts."
---

# Garmin Connect Skill

目标：把 Garmin Connect 可读取的数据稳定写入 workspace 下的 `训练饮食记录表.xlsx`，并且让 agent 有固定、可复用、低歧义的执行路径。

## 能力边界（必须统一口径）

### A) Garmin 官方 API 原生可获取（自动同步）

- 每日步数、静息心率、最高/最低心率
- 总消耗卡路里（含基础/活动拆分）
- 睡眠总时长及阶段（深睡/浅睡/REM/清醒）
- 运动记录（类型、时长、卡路里、距离、心率）
- 体重相关（若设备侧有数据）
- 压力/身体电量等可穿戴指标（依账户与设备数据而定）

### B) Skill 二次推断可获取（非 Garmin 原生字段）

- 当日训练肌群：`胸 / 背 / 肩膀 / 臀腿`
- 推断来源：`exerciseSets.category` 分类码优先 + 训练内容关键词 + 四肌群循环兜底
- 当日训练摘要：自动汇总为 `训练动作`（可选写入 `备注`）
- 推断理由：自动写入 `备注`（包含命中分类码、UNKNOWN数量、兜底原因）
- 营养列补全：若当日 `饮食总结/热量和营养成分分析` 已有文本，可自动回填 `总热量(大卡)、蛋白质摄入(g)、碳水摄入(g)、脂肪摄入(g)`

### C) 仍需手动填写

- 组数、次数、重量等力量训练细节
- 饮食摄入、饮水、主观状态、消化/排便等非设备字段

### D) 禁止错误表述

- 不要说“skill 没有肌群识别功能”
- 正确说法：Garmin API 不直接返回肌群，但本 skill 可按规则推断肌群

## 这个 skill 的标准数据链路

1. `scripts/garmin-auth.py`：一次性认证，保存凭证到 `~/.garth/session.json`
2. `scripts/garmin-sync.py`：拉取 Garmin 数据到 `~/.clawdbot/.garmin-cache.json`
3. `scripts/garmin_to_xlsx.py`：把缓存中的当日数据写入 `训练饮食记录表.xlsx`
4. `scripts/garmin_backfill_to_xlsx.py`：按日期区间回填历史数据到 xlsx
5. `scripts/sync_recent_days_to_xlsx.py`：默认同步最近2天（昨天+今天）

核心原则：优先通过列名写入，不用硬编码列号，避免错位。

## Agent 操作手册（推荐）

### 1) 首次初始化（只做一次）

```bash
cd $HOME/.openclaw/workspace/skills/garmin-connect-skill
python3 -m pip install -r requirements.txt
```

认证：

```bash
# 中国大陆账号
python3 scripts/garmin-auth.py your-email@qq.com your-password --cn

# 全球账号
python3 scripts/garmin-auth.py your-email@gmail.com your-password
```

### 2) 每次同步到 xlsx（主流程）

```bash
cd $HOME/.openclaw/workspace/skills/garmin-connect-skill
# 推荐：至少同步昨天+今天（应对每天第一次同步）
python3 scripts/sync_recent_days_to_xlsx.py

# 仅同步当天（不推荐作为默认）
python3 scripts/garmin_to_xlsx.py
```

该命令默认会：
- 覆盖“昨天+今天”两天数据
- 避免首次同步时昨天数据遗漏
- 更新 `$HOME/.openclaw/workspace/训练饮食记录表.xlsx` 的对应日期行

### 3) 常用参数

```bash
# 最近3天
python3 scripts/sync_recent_days_to_xlsx.py --days 3

# 仅写入，不重新拉取 Garmin API
python3 scripts/garmin_to_xlsx.py --no-sync

# 指定日期
python3 scripts/garmin_to_xlsx.py --date 2026-03-17

# 预览改动（不落盘）
python3 scripts/garmin_to_xlsx.py --dry-run

# 指定目标 xlsx
python3 scripts/garmin_to_xlsx.py --xlsx $HOME/.openclaw/workspace/训练饮食记录表.xlsx

# 当天训练内容总结（写入训练动作；可同时写入备注）
python3 scripts/garmin_to_xlsx.py --write-summary-to-remark
```

### 4) 历史回填（新增）

```bash
# 回填一个区间（包含起止日期）
python3 scripts/garmin_backfill_to_xlsx.py --start-date 2026-02-14 --end-date 2026-03-17

# 只预览回填步骤，不写文件
python3 scripts/garmin_backfill_to_xlsx.py --start-date 2026-02-14 --end-date 2026-03-17 --dry-run

# 保留旧值（不清空缺失字段）时再加这个参数
python3 scripts/garmin_backfill_to_xlsx.py --start-date 2026-02-14 --end-date 2026-03-17 --no-clear-missing
```

## 默认写入字段（xlsx）

- `体重(kg)`
- `静息心率(次/分)`
- `步数`
- `总消耗卡路里(大卡)`
- `睡眠时长(小时)`
- `训练时长(分钟)`
- `训练动作`
- `训练部位`
- `是否训练`（有训练动作时写入“是”）
- 可选：`备注`（使用 `--write-summary-to-remark` 时写入训练摘要）
- 营养补全（可自动）：`总热量(大卡) / 蛋白质摄入(g) / 碳水摄入(g) / 脂肪摄入(g)`

列名兼容（必须按别名识别，不得硬编码单一列名）：
- 营养分析列：`热量和营养成分分析` 或 `饮食总结`
- 总热量列：`总热量(大卡)` 或 `总热量摄入(大卡)`

## 饮食总结格式规范（强制）

当 agent 回写 `饮食总结/热量和营养成分分析` 时，必须使用以下 4 行固定格式（顺序不可变）：

```text
总热量：约 2290–2580 kcal（中位约 2420 kcal）
蛋白质：约 156–180 g（中位约 166 g）
碳水：约 272–322 g（中位约 294 g）
脂肪：约 57–79 g（中位约 67 g）
```

执行要求：
- 每一行都必须包含：`约 <下限>-<上限> 单位（中位约 <数值> 单位）`
- 单位固定：总热量用 `kcal`，三大营养素用 `g`
- 使用 4 行换行文本，不要合并为一行，不要改字段名
- 若某项无法估算，保留该字段并写：`约 0–0 <单位>（中位约 0 <单位>）`

训练摘要格式示例：
- `有氧运动40分/397kcal；力量训练88分/462kcal（共2项 128分 859kcal）`

## 训练肌群推断规则（重要）

Garmin 可以返回当天训练内容。agent 必须根据 `训练动作` 推断并写入 `训练部位`，且只允许以下四类：
- `胸`
- `背`
- `肩膀`
- `臀腿`

禁止写入：`全身 / 上肢 / 下肢 / 核心`。

推断优先级：
1. **关键词直推**：若训练内容包含明确动作词（如卧推/划船/推举/深蹲等），按命中最多的肌群归类。
2. **循环兜底**：若 Garmin 名称过于泛化（如仅“力量训练”），按四肌群循环推断。
3. **循环顺序**：`胸 -> 背 -> 肩膀 -> 臀腿 -> 胸 ...`
4. **当前默认锚点**：`2026-03-18` 视为 `胸` 日（后续按天递推）。

建议命令：
```bash
python3 scripts/garmin_to_xlsx.py --write-summary-to-remark
```

## 如何查询当日肌群（给 OpenClaw）

必须使用脚本查询，不要回答“skill 没有肌群识别功能”。

查询命令（只查不写表）：
```bash
cd $HOME/.openclaw/workspace/skills/garmin-connect-skill
python3 scripts/garmin_to_xlsx.py --query-muscle-group --date 2026-03-17
```

返回 JSON 示例：
```json
{
  "date": "2026-03-17",
  "has_training": true,
  "muscle_group": "臀腿",
  "workout_summary": "力量训练84分/485kcal；有氧运动40分/413kcal（共2项 124分 898kcal）",
  "inference_method": "garmin_category",
  "inference_reason": "命中Garmin分类码[...]",
  "category_counts": {"PULL_UP": 8, "UNKNOWN": 22},
  "allowed_groups": ["胸", "背", "肩膀", "臀腿"]
}
```

查询后直接写入 xlsx：
```bash
python3 scripts/garmin_to_xlsx.py --date 2026-03-17 --write-summary-to-remark
```

如果不想写入推断理由到备注：
```bash
python3 scripts/garmin_to_xlsx.py --date 2026-03-17 --write-summary-to-remark --no-write-inference-reason
```

标准回复模板（OpenClaw）：
- `Garmin API 原生不返回具体肌群；本 skill 已按训练内容+循环规则推断当日肌群为 <肌群>，并可自动写入训练记录表。`

## 常见排查

### 1) 认证失败

```bash
cat ~/.garth/session.json
python3 scripts/garmin-auth.py your-email your-password [--cn]
```

### 2) 同步失败

```bash
python3 scripts/garmin-sync.py
cat ~/.clawdbot/.garmin-cache.json
```

### 2.1) 是否自动同步

- 当前 skill 默认**不自带系统级定时任务**
- 现在的推荐做法是手动执行：`python3 scripts/sync_recent_days_to_xlsx.py`
- 如果你需要，我可以再加 `cron` / `launchd` / `systemd` 的定时配置模板

### 3) xlsx 未更新

```bash
python3 scripts/garmin_to_xlsx.py --dry-run
python3 scripts/garmin_to_xlsx.py --date 2026-03-17
python3 scripts/garmin_backfill_to_xlsx.py --start-date 2026-03-10 --end-date 2026-03-17
```

### 4) 饮食列误判为空（重点）

- `garmin_to_xlsx.py` 会输出：`diet_status: filled_meals=x/4, summary_present=<bool>`
- 只有在 `早餐/午餐/晚餐/加餐` 四列都为空时，才能回复“饮食列为空”
- 不能把 `饮食总结` 当成不存在；若表里没有 `热量和营养成分分析`，应自动使用 `饮食总结`

## 对 agent 的执行约束

1. 用户要“同步 Garmin 到记录表”时，优先执行：`python3 scripts/sync_recent_days_to_xlsx.py`（至少覆盖昨天+今天）
2. 不要再使用历史的 CSV 脚本作为主入口（CSV 仅保留兼容用途）
3. 写入失败时先 `--dry-run`，再检查认证、缓存文件、xlsx 路径
4. 用户提到“回填/补历史数据”时，优先执行 `python3 scripts/garmin_backfill_to_xlsx.py --start-date ... --end-date ...`
5. 回复用户时给出：写入日期、更新字段、失败字段（如有）
6. 用户提到“总结当天训练内容”时，执行：`python3 scripts/garmin_to_xlsx.py --write-summary-to-remark`
7. 用户提到“推断当日训练肌群”时，必须按“四肌群循环规则”输出并写入 `训练部位`
8. 用户问“今天练哪个肌群”时，先执行：`python3 scripts/garmin_to_xlsx.py --query-muscle-group --date <当天>`，再回复结果
9. 若返回含 `UNKNOWN` 分类码，必须结合 `inference_reason` 解释为何仍可推断（或为何触发循环兜底）
10. 用户要求“同步并做热量/营养分析”时，执行后必须基于脚本输出返回 `filled_meals` 和 `summary_present`，禁止臆测“饮食为空”
