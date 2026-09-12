from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. In a real plant deployment behind a reverse proxy,
# make sure the proxy forwards the real client IP (X-Forwarded-For) and
# that FastAPI trusts it — otherwise every request appears to come from
# the proxy and rate limiting becomes meaningless.
limiter = Limiter(key_func=get_remote_address)
