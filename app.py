import os
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


load_dotenv()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


MEDIA_TYPE_NAMES = {
    "movie": "Фильм",
    "series": "Сериал",
    "book": "Книга",
    "anime": "Аниме",
    "comic": "Комикс",
    "manga": "Манга",
}

MEDIA_TYPE_FILTERS = (
    ("all", "Все"),
    ("movie", "Фильмы"),
    ("series", "Сериалы"),
    ("book", "Книги"),
    ("anime", "Аниме"),
    ("comic", "Комиксы"),
    ("manga", "Манга"),
)


MEDIA_COVER_FILENAMES = {
    "Интерстеллар": "interstellar.webp",
    "Начало": "inception.webp",
    "Паразиты": "parasite.webp",
    "Властелин колец: Братство кольца": "lotr-fellowship.webp",
    "Титаник": "titanic.webp",
    "Во все тяжкие": "breaking-bad.webp",
    "Очень странные дела": "stranger-things.webp",
    "Шерлок": "sherlock.webp",
    "Чернобыль": "chernobyl.webp",
    "1984": "1984.webp",
    "Мастер и Маргарита": "master-and-margarita.webp",
    "Убийство в Восточном экспрессе": "orient-express.webp",
    "Гарри Поттер и философский камень": "harry-potter-1.webp",
    "Атака титанов": "attack-on-titan.webp",
    "Стальной алхимик: Братство": "fullmetal-alchemist.webp",
    "Ковбой Бибоп": "cowboy-bebop.webp",
    "Унесённые призраками": "spirited-away.webp",
    "Хранители": "watchmen.webp",
    "Бэтмен: Год первый": "batman-year-one.webp",
    "Маус": "maus.webp",
    "Песочный человек": "sandman.webp",
    "Тетрадь смерти": "death-note.webp",
    "Берсерк": "berserk.webp",
    "Монстр": "monster.webp",
    "Ван-Пис": "one-piece.webp",
}


STATUS_NAMES = {
    "planned": "В планах",
    "in_progress": "Смотрю / читаю",
    "completed": "Завершено",
    "on_hold": "Отложено",
    "dropped": "Брошено",
}


def get_db_connection():
    """Создаёт подключение к базе данных MySQL."""

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

def is_ajax_request():
    """
    Проверяет, отправлен ли запрос через JavaScript.
    """

    return (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    )


def login_required(view_function):
    """
    Запрещает выполнять действие без авторизации.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            message = "Сначала войдите в аккаунт."

            if is_ajax_request():
                return jsonify(
                    success=False,
                    message=message,
                    login_url=url_for("login"),
                ), 401

            flash(message, "error")

            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view

def admin_required(view_function):
    """
    Разрешает открывать страницу только администратору.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash(
                "Сначала войдите в аккаунт.",
                "error",
            )

            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash(
                "У вас нет доступа к этой странице.",
                "error",
            )

            return redirect(url_for("catalog"))

        return view_function(*args, **kwargs)

    return wrapped_view


@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/catalog")
def catalog():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            title,
            media_type,
            description,
            genre,
            release_year
        FROM media_items
        ORDER BY id
        """
    )

    media_items = cursor.fetchall()

    library_media_ids = set()

    if session.get("user_id"):
        cursor.execute(
            """
            SELECT media_id
            FROM user_library
            WHERE user_id = %s
            """,
            (session["user_id"],),
        )

        library_rows = cursor.fetchall()

        library_media_ids = {
            row["media_id"]
            for row in library_rows
        }

    cursor.close()
    connection.close()

    for item in media_items:
        item["media_type_name"] = MEDIA_TYPE_NAMES.get(
            item["media_type"],
            item["media_type"],
        )

        item["cover_filename"] = MEDIA_COVER_FILENAMES.get(
            item["title"]
        )

    genre_filters = sorted(
        {
            item["genre"]
            for item in media_items
            if item["genre"]
        },
        key=str.casefold,
    )

    return render_template(
        "index.html",
        media_items=media_items,
        library_media_ids=library_media_ids,
        media_type_filters=MEDIA_TYPE_FILTERS,
        genre_filters=genre_filters,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("catalog"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if len(username) < 3:
            flash(
                "Имя пользователя должно содержать минимум 3 символа.",
                "error",
            )

            return render_template(
                "register.html",
                username=username,
                email=email,
            )

        if "@" not in email:
            flash(
                "Введите корректный адрес электронной почты.",
                "error",
            )

            return render_template(
                "register.html",
                username=username,
                email=email,
            )

        if len(password) < 8:
            flash(
                "Пароль должен содержать минимум 8 символов.",
                "error",
            )

            return render_template(
                "register.html",
                username=username,
                email=email,
            )

        if password != password_confirm:
            flash(
                "Введённые пароли не совпадают.",
                "error",
            )

            return render_template(
                "register.html",
                username=username,
                email=email,
            )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s OR email = %s
            """,
            (username, email),
        )

        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            connection.close()

            flash(
                "Пользователь с таким именем или почтой уже существует.",
                "error",
            )

            return render_template(
                "register.html",
                username=username,
                email=email,
            )

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash,
                role
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                username,
                email,
                password_hash,
                "user",
            ),
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Аккаунт создан. Теперь можно войти.",
            "success",
        )

        return redirect(url_for("login"))

    return render_template(
        "register.html",
        username="",
        email="",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("catalog"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash(
                "Введите электронную почту и пароль.",
                "error",
            )

            return render_template(
                "login.html",
                email=email,
            )

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                password_hash,
                role
            FROM users
            WHERE email = %s
            """,
            (email,),
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user is None or not check_password_hash(
            user["password_hash"],
            password,
        ):
            flash(
                "Неверная электронная почта или пароль.",
                "error",
            )

            return render_template(
                "login.html",
                email=email,
            )

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        flash(
            f"Добро пожаловать, {user['username']}!",
            "success",
        )

        return redirect(url_for("catalog"))

    return render_template(
        "login.html",
        email="",
    )


@app.route("/logout")
def logout():
    session.clear()

    flash(
        "Вы вышли из аккаунта.",
        "success",
    )

    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            media_items.id,
            media_items.title,
            media_items.media_type,
            media_items.description,
            media_items.genre,
            media_items.release_year,
            COUNT(user_library.id) AS library_count
        FROM media_items
        LEFT JOIN user_library
            ON user_library.media_id = media_items.id
        GROUP BY
            media_items.id,
            media_items.title,
            media_items.media_type,
            media_items.description,
            media_items.genre,
            media_items.release_year
        ORDER BY media_items.id DESC
        """
    )

    media_items = cursor.fetchall()

    cursor.close()
    connection.close()

    for item in media_items:
        item["media_type_name"] = MEDIA_TYPE_NAMES.get(
            item["media_type"],
            item["media_type"],
        )

    genre_filters = sorted(
        {
            item["genre"]
            for item in media_items
            if item["genre"]
         },
        key=str.casefold,
    )

    return render_template(
        "admin.html",
        media_items=media_items,
        media_type_options=MEDIA_TYPE_NAMES,
        genre_filters=genre_filters,
    )


@app.route(
    "/admin/media/add",
    methods=["POST"],
)
@admin_required
def admin_add_media():
    title = request.form.get("title", "").strip()
    media_type = request.form.get(
        "media_type",
        "",
    ).strip()
    description = request.form.get(
        "description",
        "",
    ).strip()
    genre = request.form.get("genre", "").strip()
    release_year_text = request.form.get(
        "release_year",
        "",
    ).strip()

    if (
        not title
        or not description
        or not genre
        or not release_year_text
    ):
        flash(
            "Заполните все поля произведения.",
            "error",
        )

        return redirect(url_for("admin"))

    if media_type not in MEDIA_TYPE_NAMES:
        flash(
            "Выбран неизвестный тип произведения.",
            "error",
        )

        return redirect(url_for("admin"))

    try:
        release_year = int(release_year_text)
    except ValueError:
        flash(
            "Год выпуска должен быть целым числом.",
            "error",
        )

        return redirect(url_for("admin"))

    if release_year < 1 or release_year > 2100:
        flash(
            "Укажите год выпуска от 1 до 2100.",
            "error",
        )

        return redirect(url_for("admin"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id
        FROM media_items
        WHERE
            title = %s
            AND media_type = %s
        """,
        (
            title,
            media_type,
        ),
    )

    existing_item = cursor.fetchone()

    if existing_item:
        cursor.close()
        connection.close()

        flash(
            "Такое произведение уже есть в каталоге.",
            "error",
        )

        return redirect(url_for("admin"))

    cursor.execute(
        """
        INSERT INTO media_items (
            title,
            media_type,
            description,
            genre,
            release_year
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            title,
            media_type,
            description,
            genre,
            release_year,
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        f"«{title}» добавлено в общий каталог.",
        "success",
    )

    return redirect(url_for("admin"))


@app.route(
    "/admin/media/delete/<int:media_id>",
    methods=["POST"],
)
@admin_required
def admin_delete_media(media_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            title
        FROM media_items
        WHERE id = %s
        """,
        (media_id,),
    )

    media_item = cursor.fetchone()

    if media_item is None:
        cursor.close()
        connection.close()

        flash(
            "Произведение не найдено.",
            "error",
        )

        return redirect(url_for("admin"))

    cursor.execute(
        """
        DELETE FROM user_library
        WHERE media_id = %s
        """,
        (media_id,),
    )

    cursor.execute(
        """
        DELETE FROM media_items
        WHERE id = %s
        """,
        (media_id,),
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        f"«{media_item['title']}» удалено из каталога.",
        "success",
    )

    return redirect(url_for("admin"))

@app.route(
    "/admin/media/edit/<int:media_id>",
    methods=["GET", "POST"],
)
@admin_required
def admin_edit_media(media_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            id,
            title,
            media_type,
            description,
            genre,
            release_year
        FROM media_items
        WHERE id = %s
        """,
        (media_id,),
    )

    media_item = cursor.fetchone()

    if media_item is None:
        cursor.close()
        connection.close()

        flash(
            "Произведение не найдено.",
            "error",
        )

        return redirect(url_for("admin"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        media_type = request.form.get(
            "media_type",
            "",
        ).strip()
        description = request.form.get(
            "description",
            "",
        ).strip()
        genre = request.form.get("genre", "").strip()
        release_year_text = request.form.get(
            "release_year",
            "",
        ).strip()

        submitted_item = {
            "id": media_id,
            "title": title,
            "media_type": media_type,
            "description": description,
            "genre": genre,
            "release_year": release_year_text,
        }

        error_message = None
        release_year = None

        if (
            not title
            or not description
            or not genre
            or not release_year_text
        ):
            error_message = "Заполните все поля произведения."

        elif media_type not in MEDIA_TYPE_NAMES:
            error_message = (
                "Выбран неизвестный тип произведения."
            )

        else:
            try:
                release_year = int(release_year_text)
            except ValueError:
                error_message = (
                    "Год выпуска должен быть целым числом."
                )

        if (
            error_message is None
            and (
                release_year < 1
                or release_year > 2100
            )
        ):
            error_message = (
                "Укажите год выпуска от 1 до 2100."
            )

        if error_message:
            cursor.close()
            connection.close()

            flash(error_message, "error")

            return render_template(
                "admin_edit.html",
                media_item=submitted_item,
                media_type_options=MEDIA_TYPE_NAMES,
            )

        cursor.execute(
            """
            SELECT id
            FROM media_items
            WHERE
                title = %s
                AND media_type = %s
                AND id <> %s
            """,
            (
                title,
                media_type,
                media_id,
            ),
        )

        duplicate_item = cursor.fetchone()

        if duplicate_item:
            cursor.close()
            connection.close()

            flash(
                "Произведение с таким названием и типом "
                "уже есть в каталоге.",
                "error",
            )

            return render_template(
                "admin_edit.html",
                media_item=submitted_item,
                media_type_options=MEDIA_TYPE_NAMES,
            )

        cursor.execute(
            """
            UPDATE media_items
            SET
                title = %s,
                media_type = %s,
                description = %s,
                genre = %s,
                release_year = %s
            WHERE id = %s
            """,
            (
                title,
                media_type,
                description,
                genre,
                release_year,
                media_id,
            ),
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            f"Изменения для «{title}» сохранены.",
            "success",
        )

        return redirect(url_for("admin"))

    cursor.close()
    connection.close()

    return render_template(
        "admin_edit.html",
        media_item=media_item,
        media_type_options=MEDIA_TYPE_NAMES,
    )


@app.route("/library")
@login_required
def library():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            media_items.id,
            media_items.title,
            media_items.media_type,
            media_items.description,
            media_items.genre,
            media_items.release_year,
            user_library.status,
            user_library.rating,
            user_library.added_at
        FROM user_library
        INNER JOIN media_items
            ON media_items.id = user_library.media_id
        WHERE user_library.user_id = %s
        ORDER BY user_library.added_at DESC
        """,
        (session["user_id"],),
    )

    library_items = cursor.fetchall()

    cursor.close()
    connection.close()

    for item in library_items:
        item["media_type_name"] = MEDIA_TYPE_NAMES.get(
               item["media_type"],
               item["media_type"],
        )

        item["cover_filename"] = MEDIA_COVER_FILENAMES.get(
            item["title"]
        )

        item["status_name"] = STATUS_NAMES.get(
            item["status"],
            item["status"],
        )

        if item["rating"] is None:
            item["rating_text"] = "Без оценки"
            item["rating_percent"] = 0
        else:
            rating_stars = item["rating"] / 2

            rating_number = (
                f"{rating_stars:g}"
                   .replace(".", ",")
            )

            item["rating_text"] = (
                  f"{rating_number} из 5"
            )

            item["rating_percent"] = (
                item["rating"] * 10
             )
    genre_filters = sorted(
        {
            item["genre"]
            for item in library_items
            if item["genre"]
        },
        key=str.casefold,
    )
    return render_template(
        "library.html",
        library_items=library_items,
        status_options=STATUS_NAMES,
        media_type_filters=MEDIA_TYPE_FILTERS,
        genre_filters=genre_filters,
    )
@app.route(
    "/library/add/<int:media_id>",
    methods=["POST"],
)
@login_required
def add_to_library(media_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, title
        FROM media_items
        WHERE id = %s
        """,
        (media_id,),
    )

    media_item = cursor.fetchone()

    if media_item is None:
        cursor.close()
        connection.close()

        message = "Произведение не найдено."

        if is_ajax_request():
            return jsonify(
                success=False,
                message=message,
            ), 404

        flash(message, "error")

        return redirect(url_for("catalog"))

    cursor.execute(
        """
        SELECT id
        FROM user_library
        WHERE user_id = %s AND media_id = %s
        """,
        (
            session["user_id"],
            media_id,
        ),
    )

    existing_item = cursor.fetchone()

    if existing_item:
        cursor.close()
        connection.close()

        message = (
            "Это произведение уже находится "
            "в вашей медиатеке."
        )

        if is_ajax_request():
            return jsonify(
                success=False,
                message=message,
            ), 409

        flash(message, "error")

        return redirect(url_for("catalog"))

    cursor.execute(
        """
        INSERT INTO user_library (
            user_id,
            media_id,
            status
        )
        VALUES (%s, %s, %s)
        """,
        (
            session["user_id"],
            media_id,
            "planned",
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()

    message = (
        f"«{media_item['title']}» "
        "добавлено в медиатеку."
    )

    # Для JavaScript возвращаем данные без перенаправления
    if is_ajax_request():
        return jsonify(
            success=True,
            message=message,
        )

    # Запасной вариант, если JavaScript отключён
    flash(message, "success")

    return redirect(url_for("catalog"))

    # Проверяем, не добавлено ли оно ранее
    cursor.execute(
        """
        SELECT id
        FROM user_library
        WHERE user_id = %s AND media_id = %s
        """,
        (
            session["user_id"],
            media_id,
        ),
    )

    existing_item = cursor.fetchone()

    if existing_item:
        cursor.close()
        connection.close()

        flash(
            "Это произведение уже находится в вашей медиатеке.",
            "error",
        )

        return redirect(url_for("library"))

    cursor.execute(
        """
        INSERT INTO user_library (
            user_id,
            media_id,
            status
        )
        VALUES (%s, %s, %s)
        """,
        (
            session["user_id"],
            media_id,
            "planned",
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        f"«{media_item['title']}» добавлено в медиатеку.",
        "success",
    )

    return redirect(url_for("catalog") + "#catalog")

@app.route(
    "/library/update/<int:media_id>",
    methods=["POST"],
)
@login_required
def update_library_item(media_id):
    status = request.form.get("status", "").strip()
    rating_text = request.form.get("rating", "").strip()

    # Проверяем выбранный статус
    if status not in STATUS_NAMES:
        message = "Выбран неизвестный статус."

        if is_ajax_request():
            return jsonify(
                success=False,
                message=message,
            ), 400

        flash(message, "error")

        return redirect(url_for("library"))

    # Пустая оценка разрешена
    rating = None

    if rating_text:
        try:
            rating = int(rating_text)
        except ValueError:
            message = "Оценка должна быть целым числом."

            if is_ajax_request():
                return jsonify(
                    success=False,
                    message=message,
                ), 400

            flash(message, "error")

            return redirect(url_for("library"))

        if rating < 1 or rating > 10:
            message = "Оценка должна быть от 1 до 10."

            if is_ajax_request():
                return jsonify(
                    success=False,
                    message=message,
                ), 400

            flash(message, "error")

            return redirect(url_for("library"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Проверяем, что запись принадлежит текущему пользователю
    cursor.execute(
        """
        SELECT
            user_library.id,
            media_items.title
        FROM user_library
        INNER JOIN media_items
            ON media_items.id = user_library.media_id
        WHERE
            user_library.user_id = %s
            AND user_library.media_id = %s
        """,
        (
            session["user_id"],
            media_id,
        ),
    )

    library_item = cursor.fetchone()

    if library_item is None:
        cursor.close()
        connection.close()

        message = "Произведение не найдено в вашей медиатеке."

        if is_ajax_request():
            return jsonify(
                success=False,
                message=message,
            ), 404

        flash(message, "error")

        return redirect(url_for("library"))

    cursor.execute(
        """
        UPDATE user_library
        SET
            status = %s,
            rating = %s
        WHERE
            user_id = %s
            AND media_id = %s
        """,
        (
            status,
            rating,
            session["user_id"],
            media_id,
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()

    message = (
        f"Изменения для «{library_item['title']}» сохранены."
    )

    if is_ajax_request():
        return jsonify(
            success=True,
            message=message,
            status=status,
            status_name=STATUS_NAMES[status],
            rating=rating,
        )

    flash(message, "success")

    return redirect(url_for("library"))

@app.route(
    "/library/remove/<int:media_id>",
    methods=["POST"],
)
@login_required
def remove_from_library(media_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Ищем произведение только в медиатеке
    # текущего пользователя
    cursor.execute(
        """
        SELECT
            user_library.id,
            media_items.title
        FROM user_library
        INNER JOIN media_items
            ON media_items.id = user_library.media_id
        WHERE
            user_library.user_id = %s
            AND user_library.media_id = %s
        """,
        (
            session["user_id"],
            media_id,
        ),
    )

    library_item = cursor.fetchone()

    if library_item is None:
        cursor.close()
        connection.close()

        message = "Произведение не найдено в вашей медиатеке."

        if is_ajax_request():
            return jsonify(
                success=False,
                message=message,
            ), 404

        flash(message, "error")

        return redirect(url_for("library"))

    cursor.execute(
        """
        DELETE FROM user_library
        WHERE
            user_id = %s
            AND media_id = %s
        """,
        (
            session["user_id"],
            media_id,
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()

    message = (
        f"«{library_item['title']}» "
        "удалено из медиатеки."
    )

    if is_ajax_request():
        return jsonify(
            success=True,
            message=message,
        )

    flash(message, "success")

    return redirect(url_for("library"))

if __name__ == "__main__":
    app.run(debug=True)
