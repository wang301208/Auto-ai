import logging


def get_client_logger():
    # 配置 logging before we do anything else.
    # Applicati在logs need 一个place 到live.
    client_logger = logging.getLogger("autoai_client_application")
    client_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    client_logger.addHandler(ch)

    return client_logger
