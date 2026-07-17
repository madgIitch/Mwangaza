# Sprint 35 - Notification Simulator

## Resultado

- Se agrego `mwangaza.notifications` con outbox simulado, dedupe y masking.
- Filtro de severidad y adapter real fallando cerrado por defecto.
- Dashboard muestra preview simulada y estado de outbox.

## Validaciones

- `uv run python -m unittest tests.notifications.test_notification_simulator`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-35-notification-simulator`
