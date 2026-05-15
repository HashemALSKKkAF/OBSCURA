# obscura_config.py - Configuration management for OBSCURA: Loads API keys and settings from .env file with robust cleaning and support for quoted values.
import os
import socket
from dotenv import load_dotenv

load_dotenv()


def _clean_env(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        return None
    value = str(value).strip()
    # Support accidentally quoted values copied into .env
    if len(value) >= 2 and (
        (value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")
    ):
        value = value[1:-1].strip()
    return value


def find_tor_socks_port():
    """Probe for a reachable Tor SOCKS5 port (9050 or 9150)."""
    env_port = _clean_env("TOR_SOCKS_PORT")
    if env_port:
        return int(env_port)

    for port in [9150, 9050]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return port
        except Exception:
            continue
    return 9150  # Fallback to default


def find_tor_control_port():
    """Probe for a reachable Tor control port (9051 or 9151)."""
    env_port = _clean_env("TOR_CONTROL_PORT")
    if env_port:
        return int(env_port)

    for port in [9151, 9051]:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return port
        except Exception:
            continue
    return 9151  # Fallback to default


# Tor ports - defined early to avoid import issues
TOR_SOCKS_PORT = find_tor_socks_port()
TOR_CONTROL_PORT = find_tor_control_port()

# Configuration variables loaded from the .env file
OPENAI_API_KEY = _clean_env("OPENAI_API_KEY")
GOOGLE_API_KEY = _clean_env("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = _clean_env("ANTHROPIC_API_KEY")
OLLAMA_BASE_URL = _clean_env("OLLAMA_BASE_URL")
OPENROUTER_BASE_URL = _clean_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = _clean_env("OPENROUTER_API_KEY")
LLAMA_CPP_BASE_URL = _clean_env("LLAMA_CPP_BASE_URL")
