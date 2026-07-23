"""Generate a bcrypt password hash for a manually bootstrapped user."""
from getpass import getpass

from app.core.security import hash_password


def main() -> None:
    """Prompt for a password without echoing it and print its bcrypt hash."""
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    print(hash_password(password))


if __name__ == "__main__":
    main()
