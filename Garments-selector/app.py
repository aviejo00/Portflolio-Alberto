import os

import uvicorn


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8001"))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    uvicorn.run("main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
