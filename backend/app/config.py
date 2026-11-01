"""Configuration settings from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    # App
    app_env: str = "dev"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./data/hireguard.db"

    # CORS
    # Comma-separated list in .env, e.g. CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM (OpenAI-compatible)
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    llm_fallback_models: str = ""  # comma-separated
    llm_temperature: float = 0.0
    llm_cache_enabled: bool = True
    llm_max_attempts: int = 2

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    imap_host: str = ""          # empty = use Mailpit API instead of IMAP
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    hr_mailbox: str = "hr@fictional-company.test"

    # Interview scheduling (local time)
    work_day_start: int = 9
    work_day_end: int = 17
    lunch_start: int = 12
    lunch_end: int = 13
    work_days: str = "0,1,2,3,4"   # Monday=0 ... Sunday=6
    interview_minutes: int = 60
    # Interview blocks: interviews only happen here. Format "weekday:start-end", weekday Monday=0.
    # Default: Tuesday 14-17, Wednesday 10-12, Thursday 14-17
    interview_blocks: str = "1:14-17,2:10-12,3:14-17"
    max_interviews_per_day: int = 3
    min_notice_hours: int = 12      # never offer a time less than 12h from now
    offer_link_days: int = 7        # how long a scheduling link stays valid
    times_shown_to_candidate: int = 6
    interview_location: str = "Fictional Company HQ, Room B (or a video link sent by HR)"
    # Follow-ups: remind candidates who did not answer (HR approves every reminder)
    followup_after_hours: int = 48      # a reminder becomes "due" after this much silence
    followup_max_reminders: int = 2     # after that, HR decides (e.g. close the application)
    # Job posts: where candidates apply (the inbox HR Buddy reads)
    hr_contact_email: str = "hr@fictional-company.test"
    company_name: str = "Fictional Company"
    # Employees & leave (fictional company policy, see demo_data/handbook.md)
    annual_leave_days: int = 30         # paid leave days per calendar year
    sick_alert_days: int = 60           # above this, HR is alerted (sick leave is never refused for staffing)
    team_min_presence: float = 0.70     # a team should keep at least 70% of its people at work

    # Login sessions
    session_hours: int = 8
    cookie_secure: bool = False   # set True when served over HTTPS

    # Limits
    max_upload_mb: int = 5
    max_video_mb: int = 100
    portal_token_ttl_hours: int = 72

    # Email triage
    # Comma-separated senders (emails or @domains) whose messages are always important
    vip_senders: str = "director@fictional-company.test,ceo@fictional-company.test"
    demo_emails_dir: str = "./demo_data/emails"
    # Where candidates open their interview link
    frontend_url: str = "http://localhost:5173"

    # Mailpit web API (dev inbox). In docker-compose: http://mailpit:8025
    mailpit_api_url: str = "http://localhost:8025"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def vip_sender_list(self) -> list[str]:
        return [v.strip().lower() for v in self.vip_senders.split(",") if v.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
