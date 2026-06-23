"""Multi-channel notification layer (Phase 6).

A thin channel abstraction (``NotificationService``) sits over concrete
transports — email (SMTP), SMS (Twilio-ready), and push (FCM/APNs/web-ready) —
so the alert engine dispatches without knowing how delivery happens. Adding a
channel means adding a transport module and a method; nothing upstream changes.
"""
