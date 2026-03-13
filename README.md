# Garmin Connect Skill for OpenClaw

完整的佳明手表数据同步和读取解决方案，支持SQLite数据库存储，快速数据访问。

## ✨ 特性

- 🔄 **三种同步模式** - 定时（1小时）、按需（龙虾触发）、手动（前端按钮）
- 💾 **SQLite数据库存储** - 持久化所有健康数据
- ⚡ **快速数据读取** - 直接从数据库读取，无需API调用
- 📊 **完整健康指标** - 支持Body Battery、HRV、VO2 Max、健身年龄等
- 🌍 **双区域支持** - 中国大陆（garmin.cn）和全球（garmin.com）
- 🔐 **安全认证** - OAuth + 加密存储

## 📦 包含的数据

### 基础健康指标
- **步数** - 每日步数统计
- **卡路里** - 总卡路里、活动卡路里、BMR
- **距离** - 每日距离（公里）
- **爬楼** - 爬楼层数
- **活动时长** - 活动分钟数、中等/剧烈运动时长

### 心率数据
- **静息心率** - 休息时心率
- **最低/最高心率** - 当日心率范围

### 身体电量（Body Battery）
- **当前电量** - 实时身体电量（0-100）
- **最高/最低** - 当日最高和最低电量
- **充电/消耗** - 充电值和消耗值

### 压力水平
- **平均压力** - 日均压力水平（0-100）
- **最高压力** - 当日最高压力值

### 高级指标
- **HRV** - 心率变异性（昨晚）
- **VO2 Max** - 最大摄氧量
- **健身年龄** - 基于活动水平计算的生理年龄
- **呼吸率** - 平均呼吸频率

### 睡眠数据
- **睡眠时长** - 总睡眠时间（小时/分钟）
- **睡眠分数** - 综合睡眠评分（0-100）
- **睡眠阶段** - 深睡、REM、浅睡时长
- **清醒时间** - 夜间清醒时长
- **午睡记录** - 午睡次数、时长、详情

### 运动记录
- **运动列表** - 时间戳、类型、名称
- **运动数据** - 距离、时长、卡路里
- **心率数据** - 平均心率、最高心率

## 🚀 快速开始

### 1. 认证（一次性）

**中国大陆账号：**

```bash
cd ~/openclaw/skills/garmin-connect
python3 scripts/garmin-auth.py your-email@qq.com password --cn
```

**全球账号：**

```bash
python3 scripts/garmin-auth.py your-email@gmail.com password
```

认证成功后，凭证会加密保存到 `~/.garth/session.json`。

### 2. 初始化数据库

```bash
# 首次同步（自动创建数据库）
python3 ~/.clawdbot/garmin/sync_all.py --source=manual
```

数据库位置：`~/.clawdbot/garmin/data.db`

### 3. 查看数据

**从数据库读取（推荐）：**

```python
import sys
sys.path.insert(0, '~/openclaw/skills/garmin-connect/scripts')
from garmin_db_reader import GarminDataReader

reader = GarminDataReader()
today = reader.get_today_metrics()
print(f"步数: {today['steps']}")
print(f"身体电量: {today['body_battery_current']}")
```

**查看同步状态：**

```python
status = reader.get_sync_status()
print(f"最后同步: {status['last_sync_time']}")
print(f"数据记录数: {status['daily_metrics_count']}")
```

### 4. 启动自动同步

**systemd timer（推荐）：**

```bash
# 已自动配置，每1小时同步一次
sudo systemctl start garmin-sync.timer
sudo systemctl enable garmin-sync.timer

# 查看状态
systemctl status garmin-sync.timer
systemctl list-timers | grep garmin
```

## 📖 使用示例

### 在OpenClaw中使用

**方式1：数据库读取（快速）**

```python
import sys
sys.path.insert(0, '~/openclaw/skills/garmin-connect/scripts')
from garmin_db_reader import GarminDataReader, trigger_sync_if_needed

# 检查数据新鲜度，必要时触发同步
trigger_sync_if_needed(max_age_minutes=5)

# 读取今日数据
reader = GarminDataReader()
today = reader.get_today_metrics()

# 回答用户问题
print(f"你今天走了{today['steps']}步")
print(f"当前身体电量{today['body_battery_current']}%")
print(f"VO2 Max: {today['vo2_max']}")
print(f"健身年龄: {today['fitness_age']}岁")
```

**方式2：查询历史数据**

```python
# 最近7天的睡眠数据
sleep_history = reader.get_sleep_history(days=7)
for sleep in sleep_history:
    print(f"{sleep['date']}: {sleep['duration_hours']}h, 分数{sleep['sleep_score']}")

# 最近运动记录
workouts = reader.get_recent_workouts(limit=10)
for w in workouts:
    print(f"{w['name']}: {w['distance_km']}km")
```

**方式3：兼容旧API接口**

```python
from garmin_db_reader import get_daily_summary, get_sleep_data, get_workouts

# 参数garmin_client会被忽略，直接读数据库
data = get_daily_summary(None, '2026-03-13')
sleep = get_sleep_data(None, '2026-03-13')
workouts = get_workouts(None)
```

### 数据库表结构

**daily_metrics（每日健康指标）：**

| 字段 | 说明 |
|------|------|
| date | 日期 |
| steps | 步数 |
| calories/active/bmr | 卡路里（总/活动/BMR） |
| heart_rate_resting/min/max | 心率（静息/最低/最高） |
| body_battery_current/highest/lowest | 身体电量（当前/最高/最低） |
| stress_average/max | 压力（平均/最高） |
| hrv_last_night | HRV（昨晚） |
| vo2_max | VO2 Max |
| fitness_age | 健身年龄 |
| last_sync_time | 最后同步时间 |

**sleep_data（睡眠数据）：**

| 字段 | 说明 |
|------|------|
| date | 日期 |
| duration_hours/minutes | 睡眠时长 |
| sleep_score | 睡眠分数 |
| deep_sleep_hours | 深睡时长 |
| rem_sleep_hours | REM时长 |
| light_sleep_hours | 浅睡时长 |
| nap_details | 午睡详情（JSON） |

**workouts（运动记录）：**

| 字段 | 说明 |
|------|------|
| timestamp | 时间戳 |
| type | 运动类型 |
| name | 运动名称 |
| distance_km | 距离 |
| duration_minutes | 时长 |
| calories | 卡路里 |
| heart_rate_avg/max | 心率（平均/最高） |

**sync_log（同步日志）：**

| 字段 | 说明 |
|------|------|
| sync_time | 同步时间 |
| trigger_source | 触发源（timer/lobster/manual） |
| status | 状态（success/error） |
| daily_count | 每日记录数 |
| workout_count | 运动记录数 |

## 🔄 三种同步触发方式

### 1. 系统定时（自动）

每1小时自动同步一次：

```bash
# 查看状态
systemctl status garmin-sync.timer

# 查看日志
sudo journalctl -u garmin-sync.service -f
```

### 2. 龙虾按需触发

当用户问"我刚才跑的咋样？"时：

```python
from garmin_db_reader import trigger_sync_if_needed

# 如果数据超过5分钟，自动触发同步
trigger_sync_if_needed(max_age_minutes=5)
```

然后读取数据库回答。

### 3. 手动触发

```bash
# 命令行
python3 ~/.clawdbot/garmin/sync_all.py --source=manual

# 前端按钮
POST /api/sync
```

## 🔧 故障排除

### 数据库不存在

**错误：** `FileNotFoundError: Database not found`

**解决：**

```bash
# 运行首次同步
python3 ~/.clawdbot/garmin/sync_all.py --source=manual
```

### 同步失败

**错误：** `Failed to connect to Garmin`

**解决：**

```bash
# 检查凭证
cat ~/.garth/session.json

# 重新认证
cd ~/openclaw/skills/garmin-connect
python3 scripts/garmin-auth.py your-email password
```

### 数据为空

**可能原因：**
- 佳明服务器没有新数据
- API返回空（例如当天没有运动记录）

**解决：**

```python
# 检查同步日志
import sqlite3
conn = sqlite3.connect('~/.clawdbot/garmin/data.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM sync_log ORDER BY sync_time DESC LIMIT 5")
print(cursor.fetchall())
```

### HRV为0

**可能原因：**
- HRV数据需要前一天的数据
- 佳明API字段可能变化

**解决：** 暂时跳过，后续版本会修复

## 📁 文件结构

```
~/.clawdbot/garmin/
├── data.db                    # SQLite数据库
├── sync_daemon.py             # 数据库管理模块
└── sync_all.py                # 完整同步脚本

~/openclaw/skills/garmin-connect/
├── scripts/
│   ├── garmin_db_reader.py    # 数据库读取器（新增）
│   ├── garmin-auth.py         # 认证
│   ├── garmin-sync.py         # API获取（兼容）
│   └── ...
└── SKILL.md                   # 详细文档

/lib/systemd/system/
├── garmin-sync.service        # 同步服务
└── garmin-sync.timer          # 定时器（1小时）
```

## 🆕 新旧版本对比

| 特性 | 旧版本 | 新版本 |
|------|--------|--------|
| 数据存储 | 无 | SQLite数据库 |
| 响应速度 | API调用（慢） | 数据库读取（快） |
| 同步触发 | cron（5分钟） | timer（1小时）+ 按需 |
| 数据完整性 | 基础指标 | 完整（含Body Battery等） |
| 消费者 | 仅skill | skill + 网页前端 |
| 历史数据 | 无 | 支持查询 |

## 📝 开发说明

### 添加新字段

1. 更新 `sync_daemon.py` 的数据库schema
2. 更新 `sync_all.py` 的数据获取逻辑
3. 更新 `garmin_db_reader.py` 的读取接口

### 测试

```bash
# 测试数据库读取
python3 scripts/garmin_db_reader.py

# 测试同步
python3 ~/.clawdbot/garmin/sync_all.py --source=manual

# 测试API兼容性
python3 scripts/garmin-sync.py
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**更新时间：** 2026-03-13
**版本：** 2.0（数据库架构）
