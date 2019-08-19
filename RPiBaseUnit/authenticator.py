import mysql.connector
from mysql.connector import errorcode
from tkinter import *


def authenticateUser(rfidTag):
    config = {
        'host': 'irg210authenticationserver.mysql.database.azure.com',
        'user': 'myadmin@irg210authenticationserver',
        'password': '.password123',
        'database': 'authentication'
    }
    try:
        conn = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Invalid username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM staff;", rfidTag)
        rows = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        for r in rows:
            if r[2] == str(rfidTag) and r[3] > 1:
                return True
        return False


def isAuthenticationValid(reader):
    id = reader.read_id()
    return authenticateUser(id)
