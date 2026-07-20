# Registrador central de handlers do Telegram Bot

def setup_handlers(bot):
    from .handlers_commands import register_commands
    from .handlers_settings import register_settings_handlers
    from .handlers_common import register_common_handlers

    register_commands(bot)
    register_settings_handlers(bot)
    register_common_handlers(bot)
