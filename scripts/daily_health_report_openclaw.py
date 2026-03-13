#!/usr/bin/env python3
"""健康简报 - 通过OpenClaw发送"""

import json
import sys
from datetime import datetime, time
from pathlib import Path

# 标记需要通过OpenClaw发送
ALERT_FILE = Path.home() / ".clawdbot" / "feishu_health_alert.json"

def load_garmin_data():
    """加载Garmin数据 - 从数据库读取（更准确）"""
    import sqlite3
    from datetime import datetime, timedelta

    db_path = Path.home() / ".clawdbot" / "garmin" / "data.db"
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取今天的数据（如果步数很少，用昨天的）
        beijing_tz = timedelta(hours=8)
        now = datetime.now()

        # 判断今天还是昨天
        hour = now.hour
        if hour < 5:
            # 凌晨0-5点，用昨天的数据
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            target_date = now.strftime("%Y-%m-%d")

        # 查询数据
        cursor.execute("""
            SELECT date, steps, calories, active_seconds,
                   heart_rate_resting, heart_rate_min, heart_rate_max
            FROM daily_metrics
            WHERE date = ?
        """, (target_date,))

        row = cursor.fetchone()
        if not row:
            return None

        date, steps, calories, active, hr_resting, hr_min, hr_max = row

        # 如果今天步数很少（<1000），尝试获取昨天的
        if steps < 1000:
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT date, steps, calories, active_seconds,
                       heart_rate_resting, heart_rate_min, heart_rate_max
                FROM daily_metrics
                WHERE date = ?
            """, (yesterday,))
            row2 = cursor.fetchone()
            if row2 and row2[1] > steps * 2:
                date, steps, calories, active, hr_resting, hr_min, hr_max = row2

        # 获取睡眠数据
        cursor.execute("""
            SELECT duration_hours, quality_percent
            FROM sleep_data
            WHERE date = ? OR date = ?
            ORDER BY date DESC
            LIMIT 1
        """, (date, (now - timedelta(days=1)).strftime("%Y-%m-%d")))
        sleep_row = cursor.fetchone()

        sleep = {}
        if sleep_row:
            sleep = {
                'duration_hours': sleep_row[0] or 0,
                'quality_percent': sleep_row[1] or 0
            }

        # 获取运动数据
        cursor.execute("""
            SELECT sport_name, duration_minutes, calories
            FROM workouts
            WHERE date = ?
            ORDER BY start_time DESC
        """, (date,))
        workout_rows = cursor.fetchall()

        workouts = []
        for wr in workout_rows:
            workouts.append({
                'name': wr[0],
                'duration_minutes': wr[1] or 0,
                'calories': wr[2] or 0
            })

        conn.close()

        # 组装数据（兼容旧格式）
        return {
            'date': date,
            'summary': {
                'steps': steps or 0,
                'calories': calories or 0,
                'heart_rate_resting': hr_resting or 0,
                'active_seconds': active or 0
            },
            'sleep': sleep,
            'workouts': workouts
        }

    except Exception as e:
        print(f"❌ 从数据库加载数据失败: {e}", file=sys.stderr)
        return None

def generate_morning_report(data):
    """早8点简报"""
    if not data:
        return None

    lines = []
    lines.append("🌅 早安健康简报")
    lines.append(f"📅 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append("")

    sleep = data.get('sleep', {})
    if sleep.get('duration_hours', 0) > 0:
        lines.append("😴 昨晚睡眠")
        lines.append(f"  • 时长：{sleep['duration_hours']} 小时")
        lines.append(f"  • 质量：{sleep['quality_percent']} 分")
        if sleep['quality_percent'] >= 80:
            lines.append("  • 评价：✅ 睡眠质量很好")
        elif sleep['quality_percent'] >= 60:
            lines.append("  • 评价：🟡 睡眠质量一般")
        else:
            lines.append("  • 评价：⚠️ 睡眠质量需改善")
    else:
        lines.append("😴 睡眠数据：暂无昨晚数据")

    lines.append("")
    lines.append("📊 今日初始状态")
    summary = data.get('summary', {})
    lines.append(f"  • 静息心率：{summary['heart_rate_resting']} bpm")
    lines.append(f"  • 昨日步数：{summary['steps']:,} 步")
    lines.append("")
    lines.append("💡 **今日建议**")

    # 睡眠不达标特别提醒
    sleep = data.get('sleep', {})
    if sleep.get('duration_hours', 0) > 0 and sleep['duration_hours'] < 7:
        lines.append("  ⚠️ **昨晚睡眠不足警告**")
        lines.append(f"  只睡了{sleep['duration_hours']}小时，低于推荐的7-8小时")
        lines.append("  睡眠不足会影响：")
        lines.append("  • 心血管健康")
        lines.append("  • 免疫力")
        lines.append("  • 注意力与记忆力")
        lines.append("")
        lines.append("  **今天务必要注意：**")
        lines.append("  • 中午抽空午休20-30分钟")
        lines.append("  • 今天早点睡（22:00前上床）")
        lines.append("  • 避免剧烈运动，以恢复为主")
        lines.append("  • 少喝咖啡，多喝水")
        lines.append("")
        lines.append("  长期睡眠不足会增加疾病风险，请重视！")
    elif sleep.get('quality_percent', 0) < 60 and sleep.get('duration_hours', 0) > 0:
        lines.append("  • 睡眠质量一般，今天注意休息")
    elif summary['steps'] < 8000:
        lines.append("  • 昨天运动量较少，今天多活动")

    lines.append("  • 保持充足饮水（2-3L）")
    lines.append("  • 注意工作间隙休息")
    lines.append("")
    lines.append("🦞 祝你今天精力充沛！")

    return "\n".join(lines)

def generate_evening_report(data):
    """晚10点简报"""
    if not data:
        return None

    lines = []
    lines.append("🌙 晚安健康简报")
    lines.append(f"📅 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append("")

    summary = data.get('summary', {})
    lines.append("📊 今日活动总结")
    lines.append(f"  • 步数：{summary['steps']:,} 步")

    if summary['steps'] >= 10000:
        lines.append("  • 步数评价：✅ 优秀！达标")
    elif summary['steps'] >= 8000:
        lines.append("  • 步数评价：🟡 良好，继续保持")
    else:
        lines.append("  • 步数评价：🟠 一般，明天多走")

    lines.append(f"  • 消耗卡路里：{summary['calories']:.0f} 卡")
    lines.append(f"  • 静息心率：{summary['heart_rate_resting']} bpm")
    lines.append("")

    workouts = data.get('workouts', [])
    if workouts:
        lines.append(f"🏋️ 今日运动 ({len(workouts)}次)")
        for workout in workouts[:5]:
            name = workout.get('name', 'Unnamed')
            duration = workout.get('duration_minutes', 0)
            calories = workout.get('calories', 0)
            lines.append(f"  • {name} - {duration}分钟, {calories}卡")
        lines.append("")

    lines.append("💡 明日建议")
    if summary['steps'] < 8000:
        lines.append("  • 今天运动量不足，明天目标10,000步")
    else:
        lines.append("  • 保持运动习惯，继续加油")
    lines.append("  • 早点休息，保证7-8小时睡眠")
    lines.append("")
    lines.append("🦞 晚安，好梦！")

    return "\n".join(lines)

def save_alert(message):
    """保存消息到alert文件，OpenClaw会读取并发送"""
    ALERT_FILE.parent.mkdir(exist_ok=True)

    alert = {
        "timestamp": datetime.now().isoformat(),
        "type": "health_report",
        "message": message
    }

    with open(ALERT_FILE, 'w') as f:
        json.dump(alert, f, indent=2, ensure_ascii=False)

    print(f"✅ 健康简报已保存: {ALERT_FILE}")

def main():
    """主函数"""
    data = load_garmin_data()
    if not data:
        print("❌ 无法加载Garmin数据")
        sys.exit(1)

    now = datetime.now()
    current_time = now.time()

    report = None
    report_type = None

    # 早报：6:00-12:00
    if time(6, 0) <= current_time < time(12, 0):
        report = generate_morning_report(data)
        report_type = "早报"
    # 晚报：18:00-23:59
    elif time(18, 0) <= current_time:
        report = generate_evening_report(data)
        report_type = "晚报"

    if report:
        print(f"📊 {report_type}已生成")
        print("=" * 50)
        print(report)
        print("=" * 50)

        # 保存到alert文件
        save_alert(report)
        print(f"✅ {report_type}将通过OpenClaw发送到飞书")
    else:
        print(f"⏰ 当前时间 {now.strftime('%H:%M')} 不在发送时段")

if __name__ == "__main__":
    main()
