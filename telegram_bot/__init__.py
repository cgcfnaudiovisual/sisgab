# Ponto de entrada do pacote telegram_bot
from .client import init_bot, stop_bot, restart_bot, get_bot_token

def __getattr__(name: str):
    if name == "bot":
        from . import client
        return client.bot
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['init_bot', 'stop_bot', 'restart_bot', 'get_bot_token', 'bot']

