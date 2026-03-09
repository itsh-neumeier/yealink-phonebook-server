import threading

from . import create_app
from .ftp_server import start_ftp_server


def main() -> None:
    app = create_app()

    ftp_server = start_ftp_server(
        host=app.config["FTP_HOST"],
        port=app.config["FTP_PORT"],
        sqlite_db_path=app.config["SQLITE_DB_PATH"],
        root_dir=app.config["EXPORT_DIR"],
    )

    ftp_thread = threading.Thread(target=ftp_server.serve_forever, daemon=True)
    ftp_thread.start()

    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()