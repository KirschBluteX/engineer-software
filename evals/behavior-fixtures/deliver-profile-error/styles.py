ERROR_TEXT_STYLE = {"cursor": "text", "user_select": "text", "color": "error"}
PROFILE_ERROR_STYLE = {"cursor": "default", "user_select": "none", "color": "error"}


def contact_error_style() -> dict[str, str]:
    return ERROR_TEXT_STYLE


def profile_error_style() -> dict[str, str]:
    return PROFILE_ERROR_STYLE
