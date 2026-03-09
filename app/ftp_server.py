import logging
import os
import sqlite3

from pyftpdlib.authorizers import AuthenticationFailed, DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from werkzeug.security import check_password_hash


logger = logging.getLogger(__name__)


class SqliteAuthorizer(DummyAuthorizer):
    def __init__(self, db_path: str, root_dir: str):
        super().__init__()
        self.db_path = db_path
        self.root_dir = root_dir

    def _fetch_user(self, username: str):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT ftp_username, ftp_password_hash, ftp_enabled
                FROM users
                WHERE ftp_username = ?
                """,
                (username,),
            ).fetchone()
        return row

    def validate_authentication(self, username, password, handler):
        row = self._fetch_user(username)
        if not row:
            raise AuthenticationFailed("Authentication failed")

        _, ftp_password_hash, ftp_enabled = row
        if not ftp_enabled or not ftp_password_hash:
            raise AuthenticationFailed("FTP account disabled")

        if not check_password_hash(ftp_password_hash, password):
            raise AuthenticationFailed("Authentication failed")

    def has_user(self, username):
        return self._fetch_user(username) is not None

    def get_home_dir(self, username):
        return self.root_dir

    def get_perms(self, username):
        return "elr"


class ReadOnlyFtpHandler(FTPHandler):
    authorizer = None


def start_ftp_server(host: str, port: int, sqlite_db_path: str, root_dir: str) -> FTPServer:
    os.makedirs(root_dir, exist_ok=True)

    authorizer = SqliteAuthorizer(db_path=sqlite_db_path, root_dir=root_dir)
    ReadOnlyFtpHandler.authorizer = authorizer

    server = FTPServer((host, port), ReadOnlyFtpHandler)
    logger.info("FTP server listening on %s:%s (root=%s)", host, port, root_dir)
    return server