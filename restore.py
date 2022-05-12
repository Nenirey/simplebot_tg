import os
import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
import zipfile
import urllib.parse
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')
DBXTOKEN = os.getenv('DBXTOKEN')
APP_KEY = os.getenv('APP_KEY')
ADDR = os.getenv('ADDR')
botzipdb = './'+urllib.parse.quote(ADDR, safe = '')+'.zip'


def db_init():
    try:
       con = psycopg2.connect(DATABASE_URL)
       cur = con.cursor()
       cur.execute("SELECT * FROM information_schema.tables WHERE table_name=%s", ('simplebot_db',))
       if bool(cur.rowcount):
          print("La tabla existe, restaurando...")
          cur.execute("SELECT id, name, data FROM simplebot_db")
          simple_data = cur.fetchone()
          if simple_data:
             open(botzipdb, 'wb').write(simple_data[2])
       else:
          print("La tabla no existe, creando...")
          cur.execute("CREATE TABLE simplebot_db (id bigint PRIMARY KEY, name TEXT, data BYTEA)")
          con.commit()
          cur.execute("ALTER TABLE simplebot_db ALTER COLUMN data SET STORAGE EXTERNAL")
          con.commit()
       cur.close()
    except Exception as error:
       print('Cause: {}'.format(error))
    finally:
       if con is not None:
           con.close()
           print('Database connection closed.')


def unzipfile(file_path, dir_path):
    pz = open(file_path, 'rb')
    packz = zipfile.ZipFile(pz)
    for name in packz.namelist():
        packz.extract(name, dir_path)
    pz.close()

def restore(backup_path):
    print("Downloading current " + backup_path + " from Dropbox, overwriting...")
    if not os.path.exists(os.path.dirname(backup_path)):
        os.makedirs(os.path.dirname(backup_path))
    try:
       if backup_path.startswith('.'):
           dbx_backup_path = backup_path.replace('.','',1)
       else:
           dbx_backup_path =backup_path
       metadata, res = dbx.files_download(path = dbx_backup_path)
       f = open(backup_path, 'wb')
       f.write(res.content)
       f.close()
    except:
       print('Error in restore '+backup_path)
       code = str(sys.exc_info())
       print(code)

if DBXTOKEN:
   if APP_KEY:
      dbx = dropbox.Dropbox(oauth2_refresh_token=DBXTOKEN, app_key=APP_KEY)
   else:
      dbx = dropbox.Dropbox(DBXTOKEN)
   # Check that the access token is valid
   try:
      dbx.users_get_current_account()
      restore(botzipdb)
      if os.path.isfile(botzipdb):
         unzipfile(botzipdb,'/')
   except AuthError:
       sys.exit("ERROR: Invalid access token; try re-generating an "
                "access token from the app console on the web.")
elif DATABASE_URL:
   db_init()
   if os.path.exists(botzipdb):
      unzipfile(botzipdb,'/')        

