import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

# рис.2 - uuid компа заранее вписывается сюда (узнать: python lab1_secure_reg.py --uuid)
UUID_ISH = "00000000-0000-0000-0000-000000000000"

# рис.3 - сам номер лицензии в коде не храним, только его хэш
LICENSE_HASH = "6df275bd07f338106de771e0a0262e62c07ece4f8f237a26d3309cc000479446"
SALT = "lr1-salt-2026"  # соль для хэша uuid

DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DB_FILE = os.path.join(DIR, "users.db")
CONFIG_FILE = os.path.join(DIR, "config.json")

TITLE = ("", 14, "bold")
RE_ID = r"[0-9]{4}"
RE_FIO = r"[А-ЯЁ][а-яё]+(-[А-ЯЁ][а-яё]+)? [А-ЯЁ][а-яё]+( [А-ЯЁ][а-яё]+)?"
RE_PHONE = r"\+7[0-9]{10}"
RE_EMAIL = r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

# стартовые записи для бд: id, пароль, фио, телефон, почта, адрес
START_USERS = [
    ("2001", "ivan01", "Иванов Иван Сергеевич", "+79031452871", "ivanov.ivan@mail.ru", "г. Москва, ул. Тверская, д. 15, кв. 8"),
    ("2002", "pavel7", "Петров Павел Андреевич", "+79157720314", "petrov.p@yandex.ru", "г. Москва, Ленинский пр-т, д. 42, кв. 113"),
    ("2003", "anna33", "Сидорова Анна Викторовна", "+79265583190", "a.sidorova@gmail.com", "г. Химки, ул. Победы, д. 7, кв. 21"),
    ("2004", "dima44", "Кузнецов Дмитрий Олегович", "+79094418265", "kuznetsov.dm@mail.ru", "г. Москва, ул. Профсоюзная, д. 64, кв. 37"),
    ("2005", "katya5", "Смирнова Екатерина Игоревна", "+79687203157", "smirnova.e@yandex.ru", "г. Королёв, ул. Циолковского, д. 3, кв. 50"),
    ("2006", "alex66", "Попов Алексей Николаевич", "+79852269044", "popov.alex@gmail.com", "г. Москва, ул. Бауманская, д. 28, кв. 4"),
    ("2007", "olga77", "Васильева Ольга Петровна", "+79163370582", "vasilieva.o@mail.ru", "г. Мытищи, Олимпийский пр-т, д. 19, кв. 76"),
    ("2008", "maks88", "Соколов Максим Дмитриевич", "+79250981436", "sokolov.m@yandex.ru", "г. Москва, Варшавское ш., д. 87, кв. 12"),
    ("2009", "tanya9", "Михайлова Татьяна Юрьевна", "+79037746129", "mikhailova.t@gmail.com", "г. Москва, ул. Новый Арбат, д. 11, кв. 205"),
    ("2010", "serg10", "Новиков Сергей Владимирович", "+79998812573", "novikov.s@mail.ru", "г. Люберцы, Октябрьский пр-т, д. 140, кв. 9"),
    ("2011", "nata11", "Фёдорова Наталья Алексеевна", "+79264405718", "fedorova.n@yandex.ru", "г. Москва, ул. Покровка, д. 5, кв. 31"),
    ("2012", "artem1", "Морозов Артём Евгеньевич", "+79151193860", "morozov.a@gmail.com", "г. Зеленоград, корп. 1204, кв. 58"),
    ("2013", "irina3", "Волкова Ирина Михайловна", "+79036628407", "volkova.i@mail.ru", "г. Москва, Кутузовский пр-т, д. 24, кв. 90"),
    ("2014", "kiri14", "Алексеев Кирилл Романович", "+79857314952", "alekseev.k@yandex.ru", "г. Одинцово, ул. Маршала Жукова, д. 36, кв. 14"),
    ("2015", "masha5", "Лебедева Мария Сергеевна", "+79689051273", "lebedeva.m@gmail.com", "г. Москва, ул. Сретенка, д. 9, кв. 3"),
    ("2016", "roma16", "Семёнов Роман Ильич", "+79162847630", "semenov.r@mail.ru", "г. Балашиха, ул. Советская, д. 22, кв. 67"),
    ("2017", "vika17", "Егорова Виктория Андреевна", "+79257730416", "egorova.v@yandex.ru", "г. Москва, Дмитровское ш., д. 51, кв. 120"),
    ("2018", "denis8", "Павлов Денис Константинович", "+79094486521", "pavlov.d@gmail.com", "г. Красногорск, ул. Ленина, д. 4, кв. 18"),
]


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def run(cmd):
    # на винде без всплывающего окна консоли
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                              stdin=subprocess.DEVNULL, creationflags=flags).stdout
    except Exception:
        return ""


def get_uuid():
    if sys.platform == "win32":
        # wmic как в методичке, в новых win11 его убрали - тогда через powershell
        for cmd in (["wmic", "csproduct", "get", "UUID"],
                    ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]):
            m = re.search(r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}", run(cmd), re.I)
            if m:
                return m.group().upper()
    elif sys.platform == "darwin":
        m = re.search(r'"IOPlatformUUID" = "(.+?)"', run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]))
        if m:
            return m.group(1).upper()
    elif os.path.exists("/etc/machine-id"):
        with open("/etc/machine-id") as f:
            return f.read().strip().upper()
    return ""


def uuid_hash(uuid):
    return sha256(SALT + uuid)


# проверки устройства возвращают текст ошибки или None, если все ок
def check_fig2():
    # рис.2: получить uuid устр -> сравнить с uuid исх из кода
    if get_uuid() != UUID_ISH.upper():
        return "UUID устройства не совпадает с исходным."
    return None


def check_fig3(root):
    # рис.3: читаем файл конфигураций
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, ValueError):
        config = {}

    # данные по uuid есть - сравниваем хэш из файла с хэшем uuid устройства
    if "uuid_hash" in config:
        if config["uuid_hash"] != uuid_hash(get_uuid()):
            return "Хэш UUID устройства не совпадает с файлом конфигураций."
        return None

    # данных нет - вводим номер лицензии
    lic = simpledialog.askstring("Активация", "Введите номер лицензии:", parent=root)
    if not lic or sha256(lic.strip().upper()) != LICENSE_HASH:
        return "Неверный номер лицензии."
    uuid = get_uuid()
    if not uuid:
        return "Не удалось получить UUID устройства."
    # лицензия верная - считаем хэш uuid и пишем в конфиг
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"uuid_hash": uuid_hash(uuid)}, f, indent=2)
    messagebox.showinfo("Активация", "Лицензия принята, программа привязана к этому компьютеру.", parent=root)
    return None


def hash_pass(password, salt):
    # пароль храним не открытым текстом, а хэшем с солью
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def open_db():
    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON")
    # логин/пароль в одной таблице, личные данные в другой
    con.execute("""CREATE TABLE IF NOT EXISTS users (
                       id        TEXT PRIMARY KEY,
                       pass_hash TEXT NOT NULL,
                       salt      TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS user_info (
                       id      TEXT PRIMARY KEY REFERENCES users(id),
                       fio     TEXT NOT NULL,
                       phone   TEXT NOT NULL UNIQUE,
                       email   TEXT NOT NULL UNIQUE,
                       address TEXT NOT NULL)""")
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for user in START_USERS:
            add_user(con, *user)
    return con


def add_user(con, uid, password, fio, phone, email, address):
    salt = secrets.token_hex(8)
    with con:
        con.execute("INSERT INTO users VALUES (?, ?, ?)", (uid, hash_pass(password, salt), salt))
        con.execute("INSERT INTO user_info VALUES (?, ?, ?, ?, ?)", (uid, fio, phone, email, address))


def find_duplicates(con, uid, phone, email):
    # на уникальность проверяем id, телефон и почту
    dup = []
    if con.execute("SELECT 1 FROM users WHERE id = ?", (uid,)).fetchone():
        dup.append(f"ID {uid} уже занят")
    if con.execute("SELECT 1 FROM user_info WHERE phone = ?", (phone,)).fetchone():
        dup.append(f"телефон {phone} уже зарегистрирован")
    if con.execute("SELECT 1 FROM user_info WHERE email = ?", (email,)).fetchone():
        dup.append(f"почта {email} уже зарегистрирована")
    return dup


def pass_ok(p):
    # 6 символов, латиница и цифры, нужны и те и другие
    return len(p) == 6 and p.isascii() and p.isalnum() and not p.isdigit() and not p.isalpha()


def norm_phone(phone):
    # 8 (916) 123-45-67 -> +79161234567
    phone = re.sub(r"[ ()-]", "", phone)
    if re.fullmatch(r"8[0-9]{10}", phone):
        phone = "+7" + phone[1:]
    return phone


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ЛР1 - регистрация пользователей")
        self.resizable(False, False)
        self.show_start()
        self.eval("tk::PlaceWindow . center")

    def clear(self):
        for w in self.winfo_children():
            w.destroy()
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        return frame

    def show_start(self):
        f = self.clear()
        ttk.Label(f, text="Проверка ключевого признака устройства", font=TITLE).pack(pady=(0, 12))
        ttk.Button(f, text="Рис. 2 - UUID вписан в код программы",
                   command=lambda: self.check_device(2)).pack(fill="x", pady=2)
        ttk.Button(f, text="Рис. 3 - номер лицензии + хэш UUID в config.json",
                   command=lambda: self.check_device(3)).pack(fill="x", pady=2)

    def check_device(self, fig):
        error = check_fig2() if fig == 2 else check_fig3(self)
        if error:
            # не совпадает - работа завершается
            messagebox.showerror("Завершение работы", error + "\nРабота программы завершается.", parent=self)
            self.destroy()
            return
        self.con = open_db()
        self.show_login()

    def show_login(self):
        f = self.clear()
        ttk.Label(f, text="Вход в систему", font=TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 12))
        ttk.Label(f, text="ID (4 цифры):").grid(row=1, column=0, sticky="w")
        ttk.Label(f, text="Пароль (6 символов):").grid(row=2, column=0, sticky="w")
        self.e_id = ttk.Entry(f, width=22)
        self.e_pass = ttk.Entry(f, width=22, show="*")
        self.e_id.grid(row=1, column=1, padx=(8, 0), pady=3)
        self.e_pass.grid(row=2, column=1, padx=(8, 0), pady=3)
        self.e_pass.bind("<Return>", lambda e: self.login())

        btns = ttk.Frame(f)
        btns.grid(row=3, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btns, text="Войти", command=self.login).pack(side="left")
        ttk.Button(btns, text="Регистрация", command=self.show_register).pack(side="left", padx=6)
        ttk.Button(btns, text="Выход", command=self.destroy).pack(side="left")
        self.e_id.focus()

    def login(self):
        uid, password = self.e_id.get().strip(), self.e_pass.get().strip()
        if not re.fullmatch(RE_ID, uid):
            messagebox.showerror("Ошибка", "ID - ровно 4 цифры.", parent=self)
            return
        if not pass_ok(password):
            messagebox.showerror("Ошибка", "Пароль - 6 символов: латинские буквы и цифры.", parent=self)
            return

        row = self.con.execute("SELECT pass_hash, salt FROM users WHERE id = ?", (uid,)).fetchone()
        # пользователь зарегистрирован? нет - на регистрацию
        if row is None:
            messagebox.showinfo("Вход", f"Пользователь с ID {uid} не зарегистрирован.\n"
                                        "Заполните данные для регистрации.", parent=self)
            self.show_register(uid)
        elif hash_pass(password, row[1]) != row[0]:
            messagebox.showerror("Ошибка", "Неверный пароль.", parent=self)
        else:
            messagebox.showinfo("Вход", "Вход выполнен успешно.", parent=self)
            self.show_main(uid)

    def show_register(self, uid=""):
        f = self.clear()
        ttk.Label(f, text="Регистрация пользователя", font=TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 12))
        fields = [("id", "ID (4 цифры)"), ("pass", "Пароль (6 символов)"), ("pass2", "Повтор пароля"),
                  ("fio", "ФИО"), ("phone", "Телефон"), ("email", "Эл. почта"), ("address", "Адрес регистрации")]
        self.reg = {}
        for i, (key, text) in enumerate(fields, 1):
            ttk.Label(f, text=text + ":").grid(row=i, column=0, sticky="w")
            self.reg[key] = ttk.Entry(f, width=40, show="*" if key.startswith("pass") else "")
            self.reg[key].grid(row=i, column=1, padx=(8, 0), pady=3)
        self.reg["id"].insert(0, uid)

        btns = ttk.Frame(f)
        btns.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btns, text="Зарегистрироваться", command=self.register).pack(side="left")
        ttk.Button(btns, text="Назад", command=self.show_login).pack(side="left", padx=6)
        (self.reg["pass"] if uid else self.reg["id"]).focus()

    def register(self):
        d = {key: e.get().strip() for key, e in self.reg.items()}
        d["fio"] = " ".join(d["fio"].split())
        d["phone"] = norm_phone(d["phone"])
        d["email"] = d["email"].lower()

        # проверка допустимых значений
        errors = []
        if not re.fullmatch(RE_ID, d["id"]):
            errors.append("ID - ровно 4 цифры")
        if not pass_ok(d["pass"]):
            errors.append("пароль - 6 символов: латинские буквы и цифры")
        elif d["pass"] != d["pass2"]:
            errors.append("пароли не совпадают")
        if not re.fullmatch(RE_FIO, d["fio"]):
            errors.append("ФИО - русскими буквами с заглавной, например: Иванов Иван Иванович")
        if not re.fullmatch(RE_PHONE, d["phone"]):
            errors.append("телефон - в формате +7XXXXXXXXXX или 8XXXXXXXXXX")
        if not re.fullmatch(RE_EMAIL, d["email"]):
            errors.append("почта - в формате name@mail.ru")
        if len(d["address"]) < 10:
            errors.append("адрес - не короче 10 символов")
        if errors:
            messagebox.showerror("Недопустимые значения", "\n".join("• " + e for e in errors), parent=self)
            return

        # данные уникальны? нет - отказ, остаемся на форме для коррекции
        dup = find_duplicates(self.con, d["id"], d["phone"], d["email"])
        if dup:
            messagebox.showerror("Отказ в регистрации", "Данные не уникальны:\n" +
                                 "\n".join("• " + e for e in dup), parent=self)
            return

        # да - регистрируем и открываем главную форму
        add_user(self.con, d["id"], d["pass"], d["fio"], d["phone"], d["email"], d["address"])
        messagebox.showinfo("Регистрация", "Пользователь успешно зарегистрирован.", parent=self)
        self.show_main(d["id"])

    def show_main(self, uid):
        f = self.clear()
        fio = self.con.execute("SELECT fio FROM user_info WHERE id = ?", (uid,)).fetchone()[0]
        ttk.Label(f, text="Главная форма", font=TITLE).pack(anchor="w")
        ttk.Label(f, text=f"Вы вошли как: {fio} (ID {uid})").pack(anchor="w", pady=(2, 10))

        cols = {"id": ("ID", 50), "fio": ("ФИО", 230), "phone": ("Телефон", 120),
                "email": ("Эл. почта", 190), "address": ("Адрес регистрации", 340)}
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        tree = ttk.Treeview(box, columns=list(cols), show="headings", height=12)
        for c, (text, width) in cols.items():
            tree.heading(c, text=text)
            tree.column(c, width=width)
        rows = self.con.execute("SELECT id, fio, phone, email, address FROM user_info ORDER BY id").fetchall()
        for row in rows:
            item = tree.insert("", "end", values=row)
            if row[0] == uid:
                tree.selection_set(item)
                tree.see(item)
        scroll = ttk.Scrollbar(box, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Label(btns, text=f"Всего пользователей: {len(rows)}").pack(side="left")
        ttk.Button(btns, text="Выход", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Сменить пользователя", command=self.show_login).pack(side="right", padx=6)


if __name__ == "__main__":
    if "--uuid" in sys.argv:
        print(get_uuid() or "UUID не определен")
    else:
        App().mainloop()
