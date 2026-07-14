from __future__ import annotations

from mwangaza._foundation import foundation_status


def render_dashboard() -> None:
    status = foundation_status()
    try:
        import streamlit as st
    except ModuleNotFoundError:
        print(f"{status.project} - {status.tagline}")
        print(f"Status: {status.status}")
        print("No real or simulated production data is displayed in Sprint 0.")
        return

    st.set_page_config(page_title=status.project, page_icon="M", layout="wide")
    st.title(status.project)
    st.caption(status.tagline)
    st.info("foundation stub")
    st.write(
        {
            "version": status.version,
            "remote_calls_enabled": status.remote_calls_enabled,
            "data_integration": "not implemented in Sprint 0",
        }
    )
