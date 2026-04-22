from app.services import ServiceFirstRunSetup


def bootstrap_from_env() -> None:
    ServiceFirstRunSetup().ensure_setup()


if __name__ == "__main__":
    bootstrap_from_env()
