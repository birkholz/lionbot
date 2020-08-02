import os


def status_successful(status_code):
    return status_code >= 200 and status_code < 300

def init_sentry(integrations=None):
    if not integrations:
        integrations = []

    if os.environ.get("SENTRY_DSN"):
        import sentry_sdk
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_DSN"),
            integrations=integrations
        )