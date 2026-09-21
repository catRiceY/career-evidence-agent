from career_agent.observability import export_settings_from_environment


def test_langfuse_settings_use_current_otlp_endpoint_and_basic_auth():
    settings = export_settings_from_environment({
        "LANGFUSE_HOST": "https://cloud.langfuse.com/",
        "LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-test",
    })
    assert settings is not None
    assert settings.endpoint == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert settings.headers["Authorization"].startswith("Basic ")
    assert settings.headers["x-langfuse-ingestion-version"] == "4"


def test_explicit_otlp_exporter_is_supported_without_langfuse():
    settings = export_settings_from_environment({"CAREER_AGENT_OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318/v1/traces/"})
    assert settings is not None
    assert settings.endpoint == "http://localhost:4318/v1/traces"


def test_local_mode_has_no_exporter_without_any_credentials():
    assert export_settings_from_environment({}) is None
