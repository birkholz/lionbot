class DiscordError(Exception):
    """
    Exception raised when Discord rejects a message.
    """
    pass


class ValidationException(Exception):
    pass


class SubscriptionError(Exception):
    """
    Exception raised when a request to subscribe failed.
    """
    pass


class AuthenticationError(Exception):
    """
    Exception raised when failing to authenticate.
    """
    pass
