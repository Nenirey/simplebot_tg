import os
import sys
from telethon.sessions import StringSession
from telethon import TelegramClient as TC
import asyncio
import zipfile
import urllib.parse

ADDR = os.getenv('ADDR')
TGTOKEN = os.getenv('TGTOKEN')
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
botzipdb = './'+urllib.parse.quote(ADDR, safe = '')+'.zip'
loop = asyncio.new_event_loop()


def unzipfile(file_path, dir_path):
    pz = open(file_path, 'rb')
    packz = zipfile.ZipFile(pz)
    for name in packz.namelist():
        packz.extract(name, dir_path)
    pz.close()

       
async def cloud_db():
    try:
       client = TC(StringSession(TGTOKEN), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       storage_msg = await client.get_messages('me', search='simplebot_tg_db\n'+ADDR)
       if storage_msg.total>0:
          db = await client.download_media(storage_msg[-1], file=botzipdb)
          print("Db downloaded "+str(db))
       else:
          print("TG Cloud db not exists")
       await client.disconnect()
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       print(estr)
       
def async_cloud_db():
    loop.run_until_complete(cloud_db())
    
if TGTOKEN:
   async_cloud_db()
   if os.path.exists(botzipdb):
      unzipfile(botzipdb,'/')
