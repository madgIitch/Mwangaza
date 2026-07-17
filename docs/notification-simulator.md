# Notification Simulator

Sprint 35 adds simulated multichannel notifications with an in-process outbox.

By default no message leaves the process and no network adapter is invoked.
Real adapters fail closed unless an explicit feature flag and separate secrets
are provided in a future approved flow.

The outbox stores channel, masked recipient, simulated content, alert id, status,
created timestamp and dedupe key. Reprocessing the same alert/channel/recipient
does not duplicate messages.

Only configured severities create notifications. The dashboard shows a simulated
preview and outbox count, not a real send button.
