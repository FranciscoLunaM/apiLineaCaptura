import psycopg2
from dotenv import load_dotenv
from psycopg2 import DatabaseError
import os

load_dotenv();

hostname=os.getenv("HOSTNAMEQA")
database=os.getenv("DATABASEQA")
username=os.getenv("USERNAMEQA")
pwd=os.getenv("PWDQA")
port_id=os.getenv("PORTQA")

def obtenerConexion():
    try:
        return psycopg2.connect(
            host=hostname,
            dbname=database,
            user=username,
            password=pwd,
            port=port_id
        )

    except DatabaseError as error:
        raise error
