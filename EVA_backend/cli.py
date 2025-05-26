"""
cli.py - EVA 项目的命令行入口脚本

这是一个用于管理和运行 EVA 项目的脚本，允许用户通过命令行执行常见操作，如启动服务器、进行数据库迁移、检查项目状态等。
"""
import click

@click.group(invoke_without_command=True)  # 添加 invoke_without_command=True 以允许在没有子命令的情况下运行
@click.option("-c", "--continuous", is_flag=True, help="Enable Continuous Mode")  # 添加 Continuous Mode 选项

@click.option(
    "--ai-settings",
    "-C",
    help="Specifies which ai_settings.yaml file to use, will also automatically skip the re-prompt.",
)  # 添加 AI 设置选项
@click.option(
    "--prompt-settings",
    "-P",
    help="Specifies which prompt_settings.yaml file to use.",
)  # 添加 Prompt 设置选项
@click.option(
    "-l",
    "--continuous-limit",
    type=int,
    help="Defines the number of times to run in continuous mode",
)  # 添加 Continuous 模式限制选项
@click.option("--speak", is_flag=True, help="Enable Speak Mode")  # 添加 Speak 模式选项
@click.option("--debug", is_flag=True, help="Enable Debug Mode")  # 添加 Debug 模式选项
@click.option(
    "--use-memory",
    "-m",
    "memory_type",
    type=str,
    help="Defines which Memory backend to use",
)  # 添加 Memory 后端选项
@click.option(
    "-b",
    "--browser-name",
    help="Specifies which web-browser to use when using selenium to scrape the web.",
)  # 添加 Browser 名称选项
@click.option(
    "--allow-downloads",
    is_flag=True,
    help="Dangerous: Allows Auto-GPT to download files natively.",
)  # 添加允许下载选项

@click.option(
    # TODO: this is a hidden option for now, necessary for integration testing.
    #   We should make this public once we're ready to roll out agent specific workspaces.
    "--workspace-directory",
    "-w",
    type=click.Path(),
    hidden=True,
)  # 添加工作区目录选项
@click.option(
    "--install-plugin-deps",
    is_flag=True,
    help="Installs external dependencies for 3rd party plugins.",
)  # 添加安装插件依赖选项
@click.pass_context
def main(
    ctx: click.Context,         # 添加上下文参数
    continuous: bool,           # 添加 Continuous 模式选项
    continuous_limit: int,      # 添加 Continuous 模式限制选项
    ai_settings: str,           # 添加 AI 设置选项
    prompt_settings: str,       # 添加 Prompt 设置选项
    speak: bool,                # 添加 Speak 模式选项
    debug: bool,                # 添加 Debug 模式选项
    memory_type: str,           # 添加 Memory 后端选项
    browser_name: str,          # 添加 Browser 名称选项
    allow_downloads: bool,      # 添加允许下载选项
    workspace_directory: str,   # 添加工作区目录选项
    install_plugin_deps: bool,  # 添加安装插件依赖选项
) -> None:
    """EVA 项目的命令行入口脚本"""
    
    from main import run_auto_gpt

    if ctx.invoked_subcommand is None:
        run_auto_gpt(
            continuous,
            continuous_limit,
            ai_settings,
            prompt_settings,
            speak,
            debug,
            memory_type,
            browser_name,
            allow_downloads,
            workspace_directory,
            install_plugin_deps,
        )


if __name__ == "__main__":
    main()
