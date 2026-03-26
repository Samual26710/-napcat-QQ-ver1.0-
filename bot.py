import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
import uvicorn


def create_app():
    nonebot.init()
    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    nonebot.load_plugins("src/plugins")
    return nonebot.get_asgi()


app = create_app()


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
