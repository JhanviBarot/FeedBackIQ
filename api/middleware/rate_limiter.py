from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

RATE_LIMITS = {
    "auth": "10/minute",
    "analyse": "5/minute",
    "action_plan": "10/minute",
    "general": "60/minute",
}
