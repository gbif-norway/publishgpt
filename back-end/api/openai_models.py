"""Service-tier routing shared by publication and conversion workflows."""
from django.conf import settings


def model_service_tier(model, sol_tier=None):
    families = ("gpt-6.1-sol", "gpt-6-sol", "gpt-6-luna")
    family = next((name for name in families if model == name or model.startswith(name + "-")), None)
    if family == "gpt-6-luna":
        tier = getattr(settings, "OPENAI_LUNA_SERVICE_TIER", "flex")
    elif family:
        tier = sol_tier if sol_tier is not None else getattr(settings, "OPENAI_SOL_SERVICE_TIER", "flex")
    else:
        return "default"
    return tier if tier in {"flex", "default"} else "default"
