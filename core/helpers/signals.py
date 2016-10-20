from flask.signals import Namespace

_signals = Namespace()

"""This event is emitted during some operation, like login and so on.
Along with the signal,
two parameter: event type and description are also sent."""
event_emitted = _signals.signal('event-emitted')
