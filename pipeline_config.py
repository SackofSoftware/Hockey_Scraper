#!/usr/bin/env python3
"""
Pipeline Configuration System
Configuration for any league/season with customizable settings
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os


@dataclass
class PipelineConfig:
    """Configuration for hockey stats pipeline"""

    # ========================================================================
    # CORE SETTINGS
    # ========================================================================

    season_id: str = "10776"

    # Database settings
    database_path: str = "hockey_stats_{season_id}.db"
    create_backup: bool = True
    backup_path: Optional[str] = None

    # ========================================================================
    # API SETTINGS
    # ========================================================================

    # GameSheet API settings
    api_base_url: str = "https://gamesheetstats.com/api"
    api_delay: float = 0.1  # seconds between requests
    max_retries: int = 3
    timeout: int = 15  # seconds

    # ========================================================================
    # IMPORT SETTINGS
    # ========================================================================

    # Data import batch sizes
    import_batch_size: int = 100
    enable_progress_bar: bool = True
    show_detailed_progress: bool = True

    # Division filtering
    import_all_divisions: bool = True
    specific_division_ids: Optional[list] = None

    # ========================================================================
    # STATS CALCULATION SETTINGS
    # ========================================================================

    # Enable/disable specific calculations
    calculate_basic_stats: bool = True
    calculate_advanced_metrics: bool = True
    calculate_sos: bool = True
    calculate_h2h: bool = True
    calculate_rest_differential: bool = True
    calculate_recent_form: bool = True

    # ========================================================================
    # DATA QUALITY SETTINGS
    # ========================================================================

    # Quality thresholds
    min_quality_score: float = 0.8
    flag_suspicious_stats: bool = True
    auto_fix_simple_issues: bool = False

    # Confidence scoring
    enable_confidence_scoring: bool = True
    flag_low_confidence_players: bool = True
    low_confidence_threshold: float = 0.5

    # ========================================================================
    # API SERVER SETTINGS
    # ========================================================================

    # Server configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    enable_cors: bool = True
    enable_caching: bool = False  # Future feature
    enable_swagger: bool = True

    # ========================================================================
    # LOGGING SETTINGS
    # ========================================================================

    # Logging configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_to_file: bool = True
    log_file_path: str = "pipeline_{season_id}.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ========================================================================
    # PERFORMANCE SETTINGS
    # ========================================================================

    # Memory management
    commit_frequency: int = 100  # Commit every N operations
    vacuum_database: bool = True  # Optimize database after import

    # Parallel box score fetching (async aiohttp)
    parallel_box_scores: bool = True
    box_score_concurrency: int = 20       # concurrent API requests
    box_score_chunk_size: int = 500       # games per chunk

    # ========================================================================
    # OUTPUT SETTINGS
    # ========================================================================

    # Report generation
    generate_reports: bool = True
    reports_directory: str = "reports"
    export_json: bool = False
    export_csv: bool = False

    # ========================================================================
    # ADVANCED OPTIONS
    # ========================================================================

    # Experimental features
    enable_experimental_features: bool = False

    # Custom extensions
    custom_plugins: list = field(default_factory=list)

    # ========================================================================
    # CLUB SCRAPING SETTINGS
    # ========================================================================

    # Club website scraping (SportsEngine sites)
    scrape_clubs: bool = False  # Optional phase — disabled by default
    clubs_config_path: str = "config/ssc_clubs.json"
    clubs_output_dir: str = "data/clubs"
    club_scrape_headless: bool = True
    club_rate_limit_ms: int = 1000
    club_max_pages_per_club: int = 200

    # Club-to-GameSheet reconciliation
    reconcile_clubs: bool = True  # Link club data to GameSheet data after import

    def __post_init__(self):
        """Post-initialization processing"""
        # Format paths with season_id
        self.database_path = self.database_path.format(season_id=self.season_id)
        self.log_file_path = self.log_file_path.format(season_id=self.season_id)

        # Set backup path if enabled
        if self.create_backup and not self.backup_path:
            self.backup_path = f"{self.database_path}.backup"

    @classmethod
    def for_season(cls, season_id: str, **kwargs) -> 'PipelineConfig':
        """
        Create configuration for specific season with optional overrides

        Args:
            season_id: GameSheet season ID
            **kwargs: Override any configuration values

        Returns:
            PipelineConfig instance

        Example:
            >>> config = PipelineConfig.for_season("10776", api_delay=0.2)
        """
        return cls(season_id=season_id, **kwargs)

    @classmethod
    def from_file(cls, config_file: str) -> 'PipelineConfig':
        """
        Load configuration from JSON or YAML file

        Args:
            config_file: Path to configuration file

        Returns:
            PipelineConfig instance
        """
        import json

        with open(config_file, 'r') as f:
            if config_file.endswith('.json'):
                data = json.load(f)
            elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                import yaml
                data = yaml.safe_load(f)
            else:
                raise ValueError("Config file must be .json or .yaml")

        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        from dataclasses import asdict
        return asdict(self)

    def save(self, output_path: str):
        """
        Save configuration to file

        Args:
            output_path: Path to save configuration (JSON or YAML)
        """
        import json

        data = self.to_dict()

        with open(output_path, 'w') as f:
            if output_path.endswith('.json'):
                json.dump(data, f, indent=2)
            elif output_path.endswith('.yaml') or output_path.endswith('.yml'):
                import yaml
                yaml.dump(data, f, default_flow_style=False)
            else:
                raise ValueError("Output file must be .json or .yaml")

    def validate(self) -> tuple[bool, list]:
        """
        Validate configuration settings

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate season_id
        if not self.season_id or not self.season_id.isdigit():
            errors.append("season_id must be a numeric string")

        # Validate API settings
        if self.api_delay < 0:
            errors.append("api_delay must be positive")

        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")

        # Validate quality thresholds
        if not (0.0 <= self.min_quality_score <= 1.0):
            errors.append("min_quality_score must be between 0.0 and 1.0")

        if not (0.0 <= self.low_confidence_threshold <= 1.0):
            errors.append("low_confidence_threshold must be between 0.0 and 1.0")

        # Validate port
        if not (1 <= self.api_port <= 65535):
            errors.append("api_port must be between 1 and 65535")

        return (len(errors) == 0, errors)

    def __str__(self) -> str:
        """String representation"""
        return f"PipelineConfig(season_id={self.season_id}, database={self.database_path})"


# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

class PresetConfigs:
    """Preset configurations for common use cases"""

    @staticmethod
    def development(season_id: str = "10776") -> PipelineConfig:
        """Development configuration with verbose logging"""
        return PipelineConfig(
            season_id=season_id,
            log_level="DEBUG",
            show_detailed_progress=True,
            enable_progress_bar=True,
            api_delay=0.2,  # More conservative
            vacuum_database=False,  # Faster for dev
        )

    @staticmethod
    def production(season_id: str = "10776") -> PipelineConfig:
        """Production configuration optimized for performance"""
        return PipelineConfig(
            season_id=season_id,
            log_level="INFO",
            show_detailed_progress=False,
            enable_progress_bar=False,
            api_delay=0.05,  # Faster
            vacuum_database=True,
            create_backup=True,
        )

    @staticmethod
    def testing(season_id: str = "10776") -> PipelineConfig:
        """Testing configuration with limited data"""
        return PipelineConfig(
            season_id=season_id,
            import_all_divisions=False,
            specific_division_ids=[60038],  # Just one division
            log_level="DEBUG",
            create_backup=False,
        )

    @staticmethod
    def minimal(season_id: str = "10776") -> PipelineConfig:
        """Minimal configuration - basic stats only"""
        return PipelineConfig(
            season_id=season_id,
            calculate_advanced_metrics=False,
            calculate_sos=False,
            calculate_h2h=False,
            flag_suspicious_stats=False,
            vacuum_database=False,
            log_level="WARNING",
        )

    @staticmethod
    def bshl(season_id: str = "10776") -> PipelineConfig:
        """Bay State Hockey League configuration"""
        return PipelineConfig(
            season_id=season_id,
            database_path="hockey_stats.db",
            log_level="INFO",
            show_detailed_progress=True,
            enable_progress_bar=True,
            vacuum_database=True,
        )

    @staticmethod
    def ehf(season_id: str = "10477") -> PipelineConfig:
        """Eastern Hockey Federation configuration"""
        return PipelineConfig(
            season_id=season_id,
            database_path="hockey_stats.db",
            log_level="INFO",
            show_detailed_progress=True,
            enable_progress_bar=True,
            vacuum_database=True,
        )


def main():
    """Example usage and configuration validation"""
    import sys

    print("Pipeline Configuration Examples")
    print("=" * 70)

    # Example 1: Default configuration
    print("\n1. Default Configuration:")
    config = PipelineConfig(season_id="10776")
    print(f"   {config}")
    is_valid, errors = config.validate()
    print(f"   Valid: {is_valid}")
    if errors:
        for error in errors:
            print(f"   - {error}")

    # Example 2: Development preset
    print("\n2. Development Preset:")
    dev_config = PresetConfigs.development("10776")
    print(f"   Log level: {dev_config.log_level}")
    print(f"   API delay: {dev_config.api_delay}s")
    print(f"   Progress bar: {dev_config.enable_progress_bar}")

    # Example 3: Production preset
    print("\n3. Production Preset:")
    prod_config = PresetConfigs.production("10776")
    print(f"   Log level: {prod_config.log_level}")
    print(f"   API delay: {prod_config.api_delay}s")
    print(f"   Vacuum DB: {prod_config.vacuum_database}")

    # Example 4: Custom configuration
    print("\n4. Custom Configuration:")
    custom_config = PipelineConfig.for_season(
        "10776",
        api_delay=0.15,
        min_quality_score=0.9,
        api_port=8080
    )
    print(f"   Database: {custom_config.database_path}")
    print(f"   API delay: {custom_config.api_delay}s")
    print(f"   Min quality: {custom_config.min_quality_score}")

    # Example 5: Save/load configuration
    print("\n5. Save/Load Configuration:")
    output_path = "pipeline_config_example.json"
    custom_config.save(output_path)
    print(f"   Saved to: {output_path}")

    if os.path.exists(output_path):
        loaded_config = PipelineConfig.from_file(output_path)
        print(f"   Loaded: {loaded_config}")
        os.remove(output_path)
        print(f"   Cleaned up example file")

    print("\n" + "=" * 70)
    print("Configuration system ready!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
