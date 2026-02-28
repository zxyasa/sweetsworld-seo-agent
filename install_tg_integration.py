#!/usr/bin/env python3
"""
一键安装 tg_agent 集成脚本

这个脚本会自动更新 tg_agent 的配置文件，集成 sweetsworld-seo-agent
"""

import sys
from pathlib import Path

# 定义路径
TG_AGENT_DIR = Path("~/agents/agents/tg_agent").expanduser().resolve()
PROJECT_PROFILES_FILE = TG_AGENT_DIR / "project_profiles.py"
ALLOWLIST_FILE = TG_AGENT_DIR / "allowlist.yaml"
EXECUTOR_FILE = TG_AGENT_DIR / "executor.py"

def check_tg_agent_exists():
    """检查 tg_agent 目录是否存在"""
    if not TG_AGENT_DIR.exists():
        print(f"❌ tg_agent 目录不存在: {TG_AGENT_DIR}")
        print("   请确认路径是否正确")
        sys.exit(1)
    print(f"✅ 找到 tg_agent 目录: {TG_AGENT_DIR}")

def backup_file(file_path: Path):
    """备份文件"""
    if file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"   📋 已备份: {backup_path.name}")

def update_project_profiles():
    """更新 project_profiles.py"""
    print("\n📝 更新 project_profiles.py...")

    if not PROJECT_PROFILES_FILE.exists():
        print(f"   ❌ 文件不存在: {PROJECT_PROFILES_FILE}")
        return False

    backup_file(PROJECT_PROFILES_FILE)

    content = PROJECT_PROFILES_FILE.read_text()

    # 检查是否已经包含 sweetsworld 配置
    if "sweetsworld" in content:
        print("   ⚠️  sweetsworld 配置已存在，跳过")
        return True

    # 找到 PROJECTS 字典定义并添加 sweetsworld
    sweetsworld_config = '''    "sweetsworld": ProjectProfile(
        name="sweetsworld",
        aliases=("sweetsworld", "seo", "seo_agent"),
        repo_dir=Path("~/agents/agents/sweetsworld-seo-agent").expanduser().resolve(),
        entrypoint="src/run_mvp.py",
        venv_dir=".venv",
        output_log="seo.out",
        ps_grep_expr="[s]weetsworld.*python|seo.*python",
        pkill_expr="sweetsworld.*python",
    )'''

    # 在 stock1 配置后添加
    content = content.replace(
        '        pkill_expr="stock1.*python",\n    )\n}',
        f'        pkill_expr="stock1.*python",\n    ),\n{sweetsworld_config}\n}}'
    )

    PROJECT_PROFILES_FILE.write_text(content)
    print("   ✅ 已添加 sweetsworld 配置")
    return True

def update_allowlist():
    """更新 allowlist.yaml"""
    print("\n📝 更新 allowlist.yaml...")

    if not ALLOWLIST_FILE.exists():
        print(f"   ❌ 文件不存在: {ALLOWLIST_FILE}")
        return False

    backup_file(ALLOWLIST_FILE)

    content = ALLOWLIST_FILE.read_text()

    # 检查是否已经包含 seo actions
    if "seo_create" in content:
        print("   ⚠️  seo actions 已存在，跳过")
        return True

    # 添加 seo actions
    content = content.replace(
        "  - stock1_logs\n",
        """  - stock1_logs
  - seo_create
  - seo_batch
  - seo_status
  - seo_logs
"""
    )

    # 添加确认要求
    content = content.replace(
        "  - stock1_stop\n",
        """  - stock1_stop
  - seo_create
  - seo_batch
"""
    )

    ALLOWLIST_FILE.write_text(content)
    print("   ✅ 已添加 seo actions")
    return True

def update_executor():
    """更新 executor.py"""
    print("\n📝 更新 executor.py...")

    if not EXECUTOR_FILE.exists():
        print(f"   ❌ 文件不存在: {EXECUTOR_FILE}")
        return False

    backup_file(EXECUTOR_FILE)

    content = EXECUTOR_FILE.read_text()

    # 检查是否已经包含 seo actions
    if "seo_create" in content:
        print("   ⚠️  seo action handlers 已存在，跳过")
        return True

    # 添加 seo action handlers
    seo_handlers = '''
    elif action == "seo_create":
        """创建单篇 SEO 文章"""
        import sys
        sys.path.insert(0, str(BASE / "sweetsworld-seo-agent" / "src"))

        try:
            from autogen_integration import create_seo_article

            title = params.get("title", "")
            slug = params.get("slug", "")
            keyword = params.get("primary_keyword", "")
            category = params.get("category_hint", "Products")

            if not title or not slug or not keyword:
                return "❌ 缺少必需参数: title, slug, primary_keyword"

            result = create_seo_article(
                title=title,
                slug=slug,
                primary_keyword=keyword,
                category_hint=category,
                use_ai=True,
                use_gsc=True
            )

            if result["status"] == "success":
                return f"✅ SEO 文章已创建！\\n📝 标题: {title}\\n🔗 链接: {result['post_link']}\\n📊 模式: {result['mode']}\\n📏 字数: {result['characters']} 字符"
            else:
                return f"❌ 创建失败: {result['message']}"

        except Exception as e:
            return f"❌ SEO 创建失败: {str(e)}"

    elif action == "seo_batch":
        """批量创建 SEO 文章（从 topics.csv）"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        activate = f"source {shlex.quote(profile.venv_dir)}/bin/activate && " if profile.venv_dir else ""
        cmd = (
            f"cd {shlex.quote(str(profile.repo_dir))} && "
            f"{activate}python {shlex.quote(profile.entrypoint)}"
        )
        return _run(cmd, timeout=300)  # SEO 生成可能需要更长时间

    elif action == "seo_status":
        """查看 sweetsworld SEO agent 状态"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        topics_csv = profile.repo_dir / "topics.csv"
        env_file = profile.repo_dir / ".env"

        status_parts = []
        status_parts.append(f"📁 项目路径: {profile.repo_dir}")
        status_parts.append(f"🔧 .env 配置: {'✅ 存在' if env_file.exists() else '❌ 缺失'}")
        status_parts.append(f"📋 topics.csv: {'✅ 存在' if topics_csv.exists() else '❌ 缺失'}")

        if topics_csv.exists():
            lines = _run(f"wc -l {shlex.quote(str(topics_csv))}")
            status_parts.append(f"📝 Topics 数量: {lines}")

        return "\\n".join(status_parts)

    elif action == "seo_logs":
        """查看 SEO agent 最近的日志"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        log_path = _safe_path(str(profile.output_log_path()))
        if not log_path.exists():
            return "❌ 日志文件不存在（还没有运行过 seo_batch）"

        return _run(f"tail -n 100 {shlex.quote(str(log_path))}")
'''

    # 在 return 语句之前添加
    content = content.replace(
        '    return f"❌ 未实现的动作: {action}"',
        seo_handlers + '\n    return f"❌ 未实现的动作: {action}"'
    )

    EXECUTOR_FILE.write_text(content)
    print("   ✅ 已添加 seo action handlers")
    return True

def main():
    print("=" * 60)
    print("🤖 sweetsworld-seo-agent → tg_agent 集成安装器")
    print("=" * 60)

    # 检查 tg_agent 是否存在
    check_tg_agent_exists()

    # 更新配置文件
    success = True
    success = update_project_profiles() and success
    success = update_allowlist() and success
    success = update_executor() and success

    if success:
        print("\n" + "=" * 60)
        print("✅ 集成安装完成！")
        print("=" * 60)
        print("\n📋 后续步骤：")
        print("1. 重启 tg_agent:")
        print("   cd ~/agents/agents/tg_agent")
        print("   pkill -f 'bot.py'")
        print("   source .venv/bin/activate")
        print("   nohup python bot.py > bot.stdout.log 2> bot.stderr.log &")
        print("\n2. 在 Telegram 中测试:")
        print("   - 发送: 'SEO agent 状态'")
        print("   - 发送: '批量生成 SEO 文章'")
        print("\n💡 查看完整文档:")
        print("   TG_AGENT_INTEGRATION.md")
    else:
        print("\n" + "=" * 60)
        print("⚠️  安装过程中遇到问题")
        print("=" * 60)
        print("请检查上面的错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
