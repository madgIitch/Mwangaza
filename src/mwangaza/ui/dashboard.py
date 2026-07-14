from __future__ import annotations

from mwangaza._foundation import foundation_status
from mwangaza.config import ConfigurationError, load_settings
from mwangaza.gee.auth import check_gee_auth


def render_dashboard() -> None:
    status = foundation_status()
    settings = None
    config_error = None
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        config_error = exc
    gee = check_gee_auth(settings) if settings is not None else None

    try:
        import streamlit as st
    except ModuleNotFoundError:
        print(f"{status.project} - {status.tagline}")
        print(f"Status: {status.status}")
        if settings is not None:
            print(f"Configuration: ok ({settings.environment})")
            print(f"Countries: {', '.join(settings.enabled_countries)}")
            print(
                "Climatology: "
                f"{settings.climatology_start_year}-{settings.climatology_end_year}"
            )
        if config_error is not None:
            print(f"Configuration: invalid ({config_error})")
        if gee is not None:
            print(f"GEE: {gee.status} configured={gee.configured} attempts={gee.attempts}")
        print("No real or simulated production data is displayed in Sprint 0.")
        return

    st.set_page_config(page_title=status.project, page_icon="M", layout="wide")
    st.title(status.project)
    st.caption(status.tagline)
    st.info("foundation stub")
    if settings is not None:
        st.success("configuration ok")
        st.write(settings.to_public_dict())
    if config_error is not None:
        st.error("configuration invalid")
        st.write(config_error.to_public_dict())
    if gee is not None:
        st.write(
            {
                "gee.status": gee.status,
                "configured": gee.configured,
                "attempts": gee.attempts,
                "message": gee.message,
            }
        )
    st.write(
        {
            "version": status.version,
            "remote_calls_enabled": status.remote_calls_enabled,
            "data_integration": "not implemented in Sprint 0",
        }
    )
