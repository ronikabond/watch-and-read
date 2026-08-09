"""Create the configured MySQL tables and load the starter catalogue."""

import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
SQL_FILES = ("database.sql", "seed.sql")
REQUIRED_ENV_VARS = (
    "DB_HOST",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
)


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return value


def sql_statements(file_name):
    script = (PROJECT_DIR / file_name).read_text(encoding="utf-8")
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def initialize_database():
    for variable_name in REQUIRED_ENV_VARS:
        get_required_env(variable_name)

    connection = mysql.connector.connect(
        host=get_required_env("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=get_required_env("DB_USER"),
        password=get_required_env("DB_PASSWORD"),
        database=get_required_env("DB_NAME"),
        connection_timeout=20,
        ssl_disabled=False,
    )

    cursor = connection.cursor()

    try:
        for file_name in SQL_FILES:
            for statement in sql_statements(file_name):
                cursor.execute(statement)

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("База данных готова: таблицы и каталог загружены.")
