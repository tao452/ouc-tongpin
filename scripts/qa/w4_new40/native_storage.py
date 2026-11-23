"""Optional localhost transport for an owned stack; same real MySQL/Redis assertions."""

import socket
import subprocess


def sql(suite, statement):
    import pymysql

    with pymysql.connect(host="127.0.0.1", port=int(suite.env["MYSQL_PORT"]),
                         user=suite.env["MYSQL_USER"], password=suite.env["MYSQL_PASSWORD"],
                         database=suite.env["MYSQL_DATABASE"], charset="utf8mb4",
                         autocommit=True, connect_timeout=10, read_timeout=30) as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(statement)
            except pymysql.MySQLError as error:
                # Keep the CLI transport's error contract, without logging SQL or credentials.
                raise subprocess.CalledProcessError(
                    1, ["owned-mysql"], stderr=f"ERROR {error.args[0]}") from None
            rows = cursor.fetchall()
    return "\n".join("\t".join("NULL" if item is None else str(item) for item in row)
                     for row in rows)


def redis(suite, *arguments):
    with socket.create_connection(("127.0.0.1", int(suite.env["W4_REDIS_PORT"])), 10) as sock:
        stream = sock.makefile("rb")

        def send(*parts):
            parts = [str(value).encode("utf-8") for value in parts]
            sock.sendall(b"*" + str(len(parts)).encode() + b"\r\n" + b"".join(
                b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n" for value in parts))

        def read():
            line = stream.readline()
            prefix, value = line[:1], line[1:-2]
            if prefix == b"-":
                raise ValueError("Redis rejected the owned test command")
            if prefix in {b"+", b":"}:
                return value.decode("utf-8")
            if prefix == b"$":
                size = int(value)
                if size == -1:
                    return ""
                result = stream.read(size)
                assert stream.read(2) == b"\r\n"
                return result.decode("utf-8")
            if prefix == b"*":
                return "\n".join(read() for _ in range(int(value)))
            raise ValueError("Invalid Redis protocol response")

        send("AUTH", suite.env["REDIS_PASSWORD"])
        assert read() == "OK"
        send(*arguments)
        return read()
