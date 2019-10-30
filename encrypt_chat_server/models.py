import mysql.connector
from flask import jsonify, current_app, flash
import nacl.utils
import nacl.secret
import nacl.encoding
import nacl.pwhash
from nacl import encoding
from nacl.public import PrivateKey, Box


class Database:
    """
    init funktion setzt tabellen namen, system objekt, arrData und initialisiert die datenbankverbindung
    """

    def __init__(self):
        self.table_name = ""
        self.arrData = dict()

    """
    generische get funktion -> muss zur sicherheit noch ergänzt werden
    """

    def get(self, key):
        if key in self.arrData:
            return self.arrData[key]
        else:
            return 0

    """
    generische set funktion -> muss zur sicherheit noch ergänzt werden
    """

    def set(self, key, value):
        self.arrData[key] = value

    def get_id(self):
        return self.get("id")

    def get_user_id(self):
        return self.get("user_id")

    """
    gibt ein MySQLConnection Objekt zurück
    """

    def get_connection(self):
        host = current_app.config["DATABASE_HOST"]
        name = current_app.config["DATABASE_NAME"]
        user = current_app.config["DATABASE_USER"]
        password = current_app.config["DATABASE_PASSWORD"]
        return mysql.connector.connect(host=host, database=name, user=user,
                                       password=password)

    """
    lädt einen datensatz anhand der id oder user_id aus der datenbank
    ist keine id angegeben wird die komplette tabelle geladen
    """

    def load(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        table = self.table_name
        id = self.get("id")
        try:
            if int(id) > 0:
                sql = """SELECT * FROM {0} WHERE id = %s""".format(table)
                cursor = connection.cursor(prepared=True)
                cursor.execute(sql, [id])
            else:
                sql = """SELECT * FROM {0}""".format(table)
                cursor.execute(sql)
            result = dict()
            columns = tuple([str(d[0]) for d in cursor.description])
            for row in cursor:
                result = dict(zip(columns, row))
            self.arrData = result
            for key in self.arrData:
                try:
                    if isinstance(self.get(key), bytearray):
                        self.set(key, self.get(key).decode('utf-8'))
                except Exception as error:
                    print(error)
                    pass
            rows = cursor.rowcount
            if rows > 0:
                return True
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

        return False

    """
    generische update funktion
    verarbeitet die key,value pairs aus arrData in ein prepared statement mit platzhaltern
    und führt danach die query aus
    """

    def update(self):
        try:
            table = self.table_name
            id = self.get("id")
            data = self.arrData
            for key in data:
                try:
                    if isinstance(data[key], bytearray):
                        data[key] = data[key].decode('utf-8')
                except Exception as error:
                    print(error)
                    pass
            update_string = ""
            columns = data.keys()
            max_keys = len(data.keys())
            i = 1
            for column in columns:
                update_string += column
                update_string += " = "
                update_string += " %s"
                if i < max_keys:
                    update_string += ", "
                i += 1
            data["last_id"] = id
            values = list(data.values())
            sql = """UPDATE {0} SET {1} WHERE id = %s """.format(table, update_string)
            connection = self.get_connection()
            cursor = connection.cursor(prepared=True)
            cursor.execute(sql, values)
            rows = cursor.rowcount
            connection.commit()
            if rows > 0:
                return True
        except Exception as error:
            print(error)
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

        return False

    """
    generische insert methode
    verarbeitet die key,value pairs aus arrData in ein prepared statement mit platzhaltern
    und führt danach die query aus
    """

    def insert(self):
        try:
            table = self.table_name
            data = self.arrData
            columns = ','.join(data.keys())
            placeholders = ','.join(['%s'] * len(data))
            values = list(data.values())
            sql = """INSERT INTO {0} ({1}) VALUES ({2});""".format(table, columns, placeholders)
            connection = self.get_connection()
            cursor = connection.cursor(prepared=True)
            cursor.execute(sql, values)
            rows = cursor.rowcount
            connection.commit()
            if rows > 0:
                return True
        except Exception as error:
            print("")
        finally:
            if connection.is_connected:
                cursor.close()
                connection.close()
        return False

    """
    generische speicher methode anhand der id wird überprüft ob der datensatz aus der Datenbank
    geladen wurde. Wenn dem so ist sollte die id > 0 sein und somit wird ein update() ausgeführt
    andernfalls wird insert() aufgerufen
    """

    def save(self):
        if self.get("id") > 0:
            return self.update()
        else:
            return self.insert()

    def get_json_response(self):
        return jsonify(self.arrData)

    def username_exists(self, name):
        connection = self.get_connection()
        table = self.table_name
        sql = """SELECT id FROM {0} WHERE username = %s AND ctrl_active = 1""".format(table)
        cursor = connection.cursor(prepared=True)
        cursor.execute(sql, [name])
        rows = cursor.fetchone()
        cursor.close()
        connection.close()
        cursor.close()
        if rows is not None:
            return rows[0]
        return 0


class KeyPair(Database):

    def __init__(self):
        super().__init__()
        self.table_name = "keypair"

    def get_private_key(self):
        return self.get("private_key")

    def get_public_key(self):
        return self.get("public_key")

    def set_private_key(self, value):
        self.set("private_key", value)

    def set_public_key(self, value):
        self.set("public_key", value)


class Encryption:

    def create_random_token(self, length):
        return nacl.utils.random(length)

    def bin_2_hex(self, value):
        return nacl.encoding.HexEncoder.encode(value)

    def hex_2_bin(self, value):
        return nacl.encoding.HexEncoder.decode(value)

    def create_sym_key(self):
        return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

    """
    liefert den schlüssel zum symmetrischen verschlüsseln
    """

    def get_sym_key(self):
        return nacl.encoding.Base64Encoder.decode(current_app.config["SYM_KEY"])

    """
    symmetrische verschlüsselungsmethode
    """

    def encrypt(self, data):
        try:
            box = nacl.secret.SecretBox(self.get_sym_key())
            return nacl.encoding.Base64Encoder.encode(box.encrypt(data))
        except Exception as error:
            return False

    """
    symmetrische entschlüsselungsmethode
    """

    def decrypt(self, data):
        try:
            box = nacl.secret.SecretBox(self.get_sym_key())
            return box.decrypt(nacl.encoding.Base64Encoder.decode(data))
        except Exception as error:
            return False

    """
    liefert einen password hash zurück (argon2id)
    """

    def hash_password(self, password):
        return nacl.pwhash.argon2id.str(password.encode())

    def validate_hash(self, hash_string, string):
        try:
            if nacl.pwhash.verify(bytes(hash_string, encoding="utf8"), bytes(string, encoding="utf8")):
                return True
        except Exception as error:
            print(error)
            pass
        return False

    def as_base_64(self, data):
        return nacl.encoding.Base64Encoder.encode(data)

    def get_key_pair(self):
        secret_key = PrivateKey.generate()
        public_key = secret_key.public_key
        public_key_encrypted = self.encrypt(public_key.encode(encoder=encoding.RawEncoder))
        private_key_encrypted = self.encrypt(secret_key.encode(encoder=encoding.RawEncoder))
        key_pair = KeyPair()
        key_pair.set_private_key(private_key_encrypted)
        key_pair.set_public_key(public_key_encrypted)
        return key_pair
