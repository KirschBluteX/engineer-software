def accepts_contact(value: str) -> bool:
    local, separator, domain = value.partition("@")
    return bool(separator and local and "." in domain and len(domain.rsplit(".", 1)[1]) > 1)
