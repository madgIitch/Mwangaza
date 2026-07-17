from __future__ import annotations

MIGRATION_NOTICE = """
# Mwangaza frontend migrated

The canonical dashboard is now the React/Vite PWA in `frontend/`.

Use:

```bash
npm run dev
uvicorn mwangaza.api.app:app --reload
```

This Streamlit entrypoint remains only as a compatibility shim during the
migration window. It does not render the operational dashboard.
"""


def main() -> None:
    try:
        import streamlit as st  # type: ignore[import-not-found]
    except Exception:
        print("Mwangaza dashboard moved to React/Vite. Run `npm run dev`.")
        return

    st.set_page_config(page_title="Mwangaza frontend migrated", layout="centered")
    st.markdown(MIGRATION_NOTICE)


if __name__ == "__main__":
    main()
