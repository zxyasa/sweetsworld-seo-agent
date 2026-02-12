"""Configuration management for SEO automation agent."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


def _find_env_file() -> Path:
    """Find .env file in project root."""
    # Try current directory first
    current = Path(__file__).parent.parent / ".env"
    if current.exists():
        return current

    # Try parent directory
    parent = Path(__file__).parent.parent.parent / ".env"
    if parent.exists():
        return parent

    return current  # Return expected path even if not found


# Load environment variables from .env file
env_path = _find_env_file()
load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    # WordPress settings
    wp_base_url: str
    wp_username: str
    wp_app_password: str

    # Telegram settings (optional)
    telegram_bot_token: str
    telegram_chat_id: str

    # OpenAI settings (optional)
    openai_api_key: str
    openai_model: str
    use_ai_generation: bool

    # Google Search Console settings (optional)
    gsc_property_url: str
    gsc_credentials_file: str
    use_gsc_data: bool


def get_settings() -> Settings:
    """
    Load and validate settings from environment variables.

    Returns:
        Settings: Configuration object with all required settings

    Raises:
        RuntimeError: If required WordPress settings are missing
    """
    # Check if .env file exists
    if not env_path.exists():
        raise RuntimeError(
            f"❌ .env file not found at: {env_path}\n"
            f"   → Copy .env.example to .env: cp .env.example .env\n"
            f"   → Fill in your WordPress credentials\n"
            f"   → Get Application Password from: Users → Profile → Application Passwords"
        )

    # Load WordPress settings
    wp_base_url = os.getenv("WP_BASE_URL", "").strip().strip('"').strip("'")
    wp_username = os.getenv("WP_USERNAME", "").strip().strip('"').strip("'")
    wp_app_password = os.getenv("WP_APP_PASSWORD", "").strip().strip('"').strip("'")

    # Load Telegram settings (optional)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip().strip('"').strip("'")

    # Load OpenAI settings (optional)
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o").strip().strip('"').strip("'")
    use_ai_generation = os.getenv("USE_AI_GENERATION", "false").strip().lower() == "true"

    # Load GSC settings (optional)
    gsc_property_url = os.getenv("GSC_PROPERTY_URL", "").strip().strip('"').strip("'")
    gsc_credentials_file = os.getenv("GSC_CREDENTIALS_FILE", "gsc_credentials.json").strip().strip('"').strip("'")
    use_gsc_data = os.getenv("USE_GSC_DATA", "false").strip().lower() == "true"

    # Validate required WordPress settings
    missing_fields = []
    if not wp_base_url:
        missing_fields.append("WP_BASE_URL")
    if not wp_username:
        missing_fields.append("WP_USERNAME")
    if not wp_app_password:
        missing_fields.append("WP_APP_PASSWORD")

    if missing_fields:
        raise RuntimeError(
            f"❌ Missing required configuration in .env file:\n"
            f"   → {', '.join(missing_fields)}\n\n"
            f"   Please edit {env_path} and fill in:\n"
            f"   WP_BASE_URL=\"https://sweetsworld.com.au\"\n"
            f"   WP_USERNAME=\"your_username\"\n"
            f"   WP_APP_PASSWORD=\"xxxx xxxx xxxx xxxx\"\n\n"
            f"   Get Application Password from:\n"
            f"   WordPress Admin → Users → Profile → Application Passwords"
        )

    # Validate URL format
    if not wp_base_url.startswith(("http://", "https://")):
        raise RuntimeError(
            f"❌ Invalid WP_BASE_URL: {wp_base_url}\n"
            f"   → Must start with http:// or https://\n"
            f"   → Example: https://sweetsworld.com.au"
        )

    # Validate Application Password format (should have spaces)
    if " " not in wp_app_password:
        print(
            f"⚠️  Warning: WP_APP_PASSWORD might be incorrect\n"
            f"   → Application Password usually has spaces (e.g., 'xxxx xxxx xxxx xxxx')\n"
            f"   → Your password: '{wp_app_password}'\n"
        )

    return Settings(
        wp_base_url=wp_base_url,
        wp_username=wp_username,
        wp_app_password=wp_app_password,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        use_ai_generation=use_ai_generation,
        gsc_property_url=gsc_property_url,
        gsc_credentials_file=gsc_credentials_file,
        use_gsc_data=use_gsc_data,
    )
