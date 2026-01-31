"""Service for managing application settings."""
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Settings
from app.modules.settings.schemas import SettingsUpdate, SettingsResponse
from app.modules.settings.encryption import encrypt_value, decrypt_value, mask_value


# Keys that should be encrypted
ENCRYPTED_KEYS = {"tmdb_api_key", "radarr_api_key", "sonarr_api_key"}


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> SettingsResponse:
        """Get all settings with masked sensitive values."""
        settings = {s.key: s for s in self.db.query(Settings).all()}

        return SettingsResponse(
            tmdb_api_key_masked=self._get_masked(settings, "tmdb_api_key"),
            radarr_url=self._get_plain(settings, "radarr_url"),
            radarr_api_key_masked=self._get_masked(settings, "radarr_api_key"),
            radarr_root_folder=self._get_plain(settings, "radarr_root_folder"),
            sonarr_url=self._get_plain(settings, "sonarr_url"),
            sonarr_api_key_masked=self._get_masked(settings, "sonarr_api_key"),
            sonarr_root_folder=self._get_plain(settings, "sonarr_root_folder"),
            has_tmdb="tmdb_api_key" in settings,
            has_radarr="radarr_url" in settings and "radarr_api_key" in settings,
            has_sonarr="sonarr_url" in settings and "sonarr_api_key" in settings,
        )

    def update_settings(self, update: SettingsUpdate) -> None:
        """Update settings from request."""
        for key, value in update.model_dump(exclude_none=True).items():
            self._set_value(key, value)
        self.db.commit()

    def get_raw_value(self, key: str) -> Optional[str]:
        """Get decrypted value for internal use."""
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if not setting:
            return None
        if setting.encrypted:
            return decrypt_value(setting.value)
        return setting.value

    def _get_masked(self, settings: dict, key: str) -> Optional[str]:
        """Get masked value for display."""
        if key not in settings:
            return None
        value = settings[key].value
        if settings[key].encrypted:
            value = decrypt_value(value)
        return mask_value(value)

    def _get_plain(self, settings: dict, key: str) -> Optional[str]:
        """Get plain value (for non-sensitive fields)."""
        if key not in settings:
            return None
        return settings[key].value

    def _set_value(self, key: str, value: str) -> None:
        """Set a setting value, encrypting if needed."""
        encrypted = key in ENCRYPTED_KEYS
        if encrypted:
            value = encrypt_value(value)

        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            setting.encrypted = encrypted
        else:
            setting = Settings(key=key, value=value, encrypted=encrypted)
            self.db.add(setting)
