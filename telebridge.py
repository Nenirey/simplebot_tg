import simplebot
import deltachat
from simplebot.bot import DeltaBot, Replies
from deltachat import Chat, Contact, Message
from deltachat import account_hookimpl
from typing import Optional
import sys
import os
from os.path import expanduser
import psutil
from telethon.sessions import StringSession
from telethon import TelegramClient as TC
from telethon import functions, types
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, SendMessageRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.types import InputPeerEmpty, WebDocument, WebDocumentNoProxy, InputWebFileLocation
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from telethon import utils, errors
from telethon.errors import SessionPasswordNeededError
import asyncio
import re
import time
import json
import urllib.parse
from datetime import datetime
from threading import Event, Thread
import copy
#For telegram sticker stuff
import lottie
from lottie.importers import importers
from lottie.exporters import exporters
from lottie.utils.stripper import float_strip, heavy_strip
#For secure cloud storage
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from dropbox import DropboxOAuth2FlowNoRedirect
import zipfile
import base64

version = "0.2.1"
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
login_hash = os.getenv('LOGIN_HASH')
admin_addr = os.getenv('ADMIN')
bot_home = expanduser("~")

global phonedb
phonedb = {}

global smsdb
smsdb = {}

global hashdb
hashdb = {}

global clientdb
clientdb = {}

global logindb
logindb = {}

global messagedb
#{contac_addr:{dc_id:{dc_msg:tg_msg}}}
messagedb = {}

global unreaddb
#{'dc_id:dc_msg':[contact,tg_id,tg_msg]}
unreaddb = {}

global autochatsdb
#{contact_addr:{dc_id:tg_id}}
autochatsdb = {}

global chatdb
chatdb = {}

global auto_load_task
auto_load_task = None

global encode_bot_addr
encode_bot_addr = ''

global SYNC_ENABLED
SYNC_ENABLED = 0

global UPDATE_DELAY
UPDATE_DELAY = 16

global authorize_url
authorize_url = None

loop = asyncio.new_event_loop()

#Secure save storage to use in non persistent storage
DBXTOKEN = os.getenv('DBXTOKEN')
APP_KEY = os.getenv('APP_KEY')
global LOGINFILE
LOGINFILE = ''
global AUTOCHATFILE
AUTOCHATFILE = ''

if DBXTOKEN:
   if APP_KEY:
      auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, use_pkce=True, token_access_type='offline')
      dbx = dropbox.Dropbox(oauth2_refresh_token=DBXTOKEN, app_key=APP_KEY)
   else:
      dbx = dropbox.Dropbox(DBXTOKEN)
   # Check that the access token is valid
   try:
      dbx.users_get_current_account()
   except AuthError:
       print("ERROR: Invalid access token; try re-generating an "
                "access token from the app console on the web.")


def backup(backup_path):
    with open(backup_path, 'rb') as f:
        print("Uploading " + backup_path + " to Dropbox...")
        if backup_path.startswith('.'):
           dbx_backup_path = backup_path.replace('.','',1)
        else:
           dbx_backup_path =backup_path
        try:
            dbx.files_upload(f.read(), dbx_backup_path, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                #sys.exit("ERROR: Cannot back up; insufficient space.")
                print("ERROR: Cannot back up; insufficient space.", err)
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()

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
       print("Error in restore " + backup_path)

def zipdir(dir_path,file_path):
    zf = zipfile.ZipFile(file_path, "w")
    for dirname, subdirs, files in os.walk(dir_path):
        if dirname.endswith('account.db-blobs'):
           continue
        zf.write(dirname)
        print(dirname)
        for filename in files:
            #if filename=='account.db-wal' or filename=='account.db-shm' or filename=='bot.log':
            #   continue
            print(filename)
            zf.write(os.path.join(dirname, filename))
    zf.close()
    return file_path

def unzipfile(file_path, dir_path):
    pz = open(file_path, 'rb')
    packz = zipfile.ZipFile(pz)
    for name in packz.namelist():
        packz.extract(name, dir_path)
    pz.close()

def savelogin():
    if not os.path.exists(os.path.dirname(LOGINFILE)):
       os.makedirs(os.path.dirname(LOGINFILE))
    tf = open(LOGINFILE, 'w')
    json.dump(logindb, tf)
    tf.close()
    if DBXTOKEN:
       backup(LOGINFILE)
    os.remove(LOGINFILE)

def loadlogin():
    if DBXTOKEN:
       restore(LOGINFILE)
    if os.path.isfile(LOGINFILE):
       tf = open(LOGINFILE,'r')
       global logindb
       logindb=json.load(tf)
       tf.close()
       os.remove(LOGINFILE)
       for (key,_) in logindb.items():
           loop.run_until_complete(load_delta_chats(contacto=key))
           time.sleep(5)
    else:
       print("File "+LOGINFILE+" not exists!!!")

def saveautochats():
    if not os.path.exists(os.path.dirname(AUTOCHATFILE)):
       os.makedirs(os.path.dirname(AUTOCHATFILE))
    tf = open(AUTOCHATFILE, 'w')
    json.dump(autochatsdb, tf)
    tf.close()
    if DBXTOKEN:
       backup(AUTOCHATFILE)
    os.remove(AUTOCHATFILE)

def loadautochats():
    if DBXTOKEN:
       restore(AUTOCHATFILE)
    if os.path.isfile(AUTOCHATFILE):
       tf = open(AUTOCHATFILE,'r')
       global autochatsdb
       autochatsdb=json.load(tf)
       tf.close()
       os.remove(AUTOCHATFILE)
    else:
       print("File "+AUTOCHATFILE+" not exists!!!")

def backup_db():
    #bot.account.stop_io()
    print('Backup...')
    zipfile = zipdir(bot_home+'/.simplebot/', encode_bot_addr+'.zip')
    #bot.account.start_io()
    if os.path.getsize('./'+zipfile)>22:
       backup('./'+zipfile)
    else:
       print('Invalid zip file!')
    os.remove('./'+zipfile)

#end secure save storage

def fixautochatsdb(bot):
    cids = []
    dchats = bot.account.get_chats()
    for c in dchats:
        cids.append(str(c.id))
    #print('Chats guardados: '+str(cids))
    tmpdict = copy.deepcopy(autochatsdb)
    for (key, value) in tmpdict.items():
        for (inkey, invalue) in value.items():
            if str(inkey) not in cids:
               print('El chat '+str(inkey)+' no existe en el bot')
               del autochatsdb[key][inkey]


class AccountPlugin:
      #def __init__(self, bot:DeltaBot) -> None:
      #    self.bot = bot
      @account_hookimpl
      def ac_chat_modified(self, chat):
          print('Chat modificado/creado: '+chat.get_name())
          if chat.is_group():
             if DBXTOKEN:
                backup_db()

      @account_hookimpl
      def ac_process_ffi_event(self, ffi_event):
          #print(ffi_event)
          if ffi_event.name == "DC_EVENT_WARNING":
             #print('Evento warning detectado!', ffi_event)
             if ffi_event.data2 and ffi_event.data2.find("Daily user sending quota exceeded")>=0:
                print('Limite diario de mensajes alcanzado!')

          if ffi_event.name == "DC_EVENT_MSG_READ":
             msg = str(ffi_event.data1)+':'+str(ffi_event.data2)
             print(msg)
             if msg in unreaddb:
                async_read_unread(unreaddb[msg][0], unreaddb[msg][1], unreaddb[msg][2])
                del unreaddb[msg]


@simplebot.hookimpl(tryfirst=True)
def deltabot_incoming_message(message, replies) -> Optional[bool]:
    """Check that the sender is not in the black or white list."""
    sender_addr = message.get_sender_contact().addr
    if white_list and sender_addr!=admin_addr and sender_addr not in white_list:
       print('Usuario '+str(sender_addr)+' no esta en la lista blanca')
       return True
    if black_list and sender_addr!=admin_addr and sender_addr in black_list:
       print('Usuario '+str(message.get_sender_contact().addr)+' esta en la lista negra')
       return True
    """
    if message.chat.is_group():
       if get_tg_id(message.chat, bot):
          contactos = message.chat.get_contacts()
          if len(contactos)>2:
             if contactos.index(message.get_sender_contact())>1:
                print('Mensaje de en un usuario no propietario del grupo')
                return True
       else:
          print('Bot en un grupo que no es de telegram!')
          return True
    """
    return None

@simplebot.hookimpl
def deltabot_member_added(chat, contact, actor, message, replies, bot) -> None:
    if actor:
       print('Miembro '+str(contact.addr)+' agregado por '+str(actor.addr)+' chat: '+str(chat.get_name()))
    else:
       print('My self!')

@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.account.add_account_plugin(AccountPlugin())
    bot.account.set_config("displayname","Telegram Bridge")
    bot.account.set_avatar("telegram.jpeg")
    bot.account.set_config("delete_device_after","21600")
    global MAX_MSG_LOAD
    global MAX_MSG_LOAD_AUTO
    global MAX_AUTO_CHATS
    global MAX_SIZE_DOWN
    global MIN_SIZE_DOWN
    global CAN_IMP
    global SYNC_ENABLED
    global UPDATE_DELAY
    global white_list
    global black_list
    global unreaddb
    MAX_MSG_LOAD = bot.get('MAX_MSG_LOAD') or 5
    MAX_MSG_LOAD = int(MAX_MSG_LOAD)
    MAX_MSG_LOAD_AUTO = bot.get('MAX_MSG_LOAD_AUTO') or 5
    MAX_MSG_LOAD_AUTO = int(MAX_MSG_LOAD_AUTO)
    MAX_AUTO_CHATS = bot.get('MAX_AUTO_CHATS') or 10
    MAX_AUTO_CHATS = int(MAX_AUTO_CHATS)
    MAX_SIZE_DOWN = bot.get('MAX_SIZE_DOWN') or 20485760
    MAX_SIZE_DOWN = int(MAX_SIZE_DOWN)
    MIN_SIZE_DOWN = bot.get('MIN_SIZE_DOWN') or 655360
    MIN_SIZE_DOWN = int(MIN_SIZE_DOWN)
    CAN_IMP = bot.get('CAN_IMP') or 0
    CAN_IMP = int(CAN_IMP)
    UPDATE_DELAY = bot.get('UPDATE_DELAY') or 16
    UPDATE_DELAY = int(UPDATE_DELAY)
    SYNC_ENABLED = bot.get('SYNC_ENABLED') or 0
    SYNC_ENABLED = int(SYNC_ENABLED)
    if SYNC_ENABLED:
       bot.account.set_config("mdns_enabled","1")
    #use env to add to the lists like "user1@domine.com user2@domine.com" with out ""
    white_list = os.getenv('WHITE_LIST') or bot.get('WHITE_LIST')
    black_list = os.getenv('BLACK_LIST') or bot.get('BLACK_LIST')
    if white_list:
       white_list = white_list.split()
    if black_list:
       black_list = black_list.split()
    unreaddb = json.loads(bot.get('UNREADDB') or '{}')
    bot.commands.register(name = "/eval" ,func = eval_func, admin = True)
    bot.commands.register(name = "/start" ,func = start_updater, admin = True)
    bot.commands.register(name = "/stop" ,func = stop_updater, admin = True)
    bot.commands.register(name = "/more" ,func = async_load_chat_messages)
    bot.commands.register(name = "/load" ,func = async_updater)
    bot.commands.register(name = "/exec" ,func = async_run, admin = True)
    bot.commands.register(name = "/login" ,func = async_login_num)
    bot.commands.register(name = "/sms" ,func = async_login_code)
    bot.commands.register(name = "/pass" ,func = async_login_2fa)
    bot.commands.register(name = "/token" ,func = async_login_session)
    bot.commands.register(name = "/logout" ,func = logout_tg)
    bot.commands.register(name = "/remove" ,func = remove_chat)
    bot.commands.register(name = "/down" ,func = async_down_chat_messages)
    bot.commands.register(name = "/comment" ,func = async_comment_chat_messages)
    bot.commands.register(name = "/c" ,func = async_click_button)
    bot.commands.register(name = "/b" ,func = async_send_cmd)
    bot.commands.register(name = "/search" ,func = async_search_chats)
    bot.commands.register(name = "/join" ,func = async_join_chats)
    bot.commands.register(name = "/preview" ,func = async_preview_chats)
    bot.commands.register(name = "/auto" ,func = async_add_auto_chats)
    bot.commands.register(name = "/inline" ,func = async_inline_cmd)
    bot.commands.register(name = "/list" ,func = list_chats)
    bot.commands.register(name = "/forward" ,func = async_forward_message)
    bot.commands.register(name = "/pin" ,func = async_pin_messages)
    bot.commands.register(name = "/news" ,func = async_chat_news)
    bot.commands.register(name = "/info" ,func = async_chat_info)
    bot.commands.register(name = "/setting" ,func = bot_settings, admin = True)
    bot.commands.register(name = "/react" ,func = async_react_button)
    bot.commands.register(name = "/link2" ,func = link_to, admin = True)
    bot.commands.register(name = "/dbxtoken" ,func = get_dbxtoken, admin = True)

@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    bridge_init = Event()
    Thread(
        target=start_background_loop,
        args=(bridge_init,),
        daemon=True,
    ).start()
    bridge_init.wait()
    global auto_load_task
    auto_load_task = asyncio.run_coroutine_threadsafe(auto_load(bot=bot, message = Message, replies = Replies),tloop)
    global bot_addr
    bot_addr = bot.account.get_config('addr')
    global encode_bot_addr
    encode_bot_addr = urllib.parse.quote(bot_addr, safe='')
    global LOGINFILE
    LOGINFILE = './'+encode_bot_addr+'/logindb.json'
    global AUTOCHATFILE
    AUTOCHATFILE = './'+encode_bot_addr+'/autochatsdb.json'
    loadlogin()
    loadautochats()
    fixautochatsdb(bot)
    if admin_addr:
       bot.get_chat(admin_addr).send_text('El bot '+bot_addr+' se ha iniciado correctamente')


def get_dbxtoken(bot, replies, message, payload):
    "Get fresh Dropbox Token (DBXTOKEN)"
    global authorize_url
    if APP_KEY:
       authorize_url = auth_flow.start()
       replies.add(text='Por favor acceda a la siguiente URI, presione [Allow o Permitir], copie el codigo de autorizacion y envielo aqui:\n\n'+str(authorize_url))
    else:
       replies.add(text='Debe colocar su APP_KEY de Dropbox en las variables de entorno, para poder generar nuevos codigos de acceso.')

def hide_spoiler(s_text,offset,tlen):
    h_text = '▚'*tlen
    mystring = h_text.join([s_text[:offset],s_text[offset+tlen:]])
    return mystring

def broadcast_message(bot, msg):
    for (user,_) in logindb.items():
        try:
           bot.get_chat(user).send_text(msg)
        except:
           print('Error sending broadcast to '+user)

def register_msg(contacto, dc_id, dc_msg, tg_msg):
   global messagedb
   #{contac_addr:{dc_id:{dc_msg:tg_msg}}}
   if contacto not in messagedb:
      messagedb[contacto] = {}
   if dc_id not in messagedb[contacto]:
      messagedb[contacto][dc_id] = {}
   messagedb[contacto][dc_id][dc_msg] = tg_msg

def is_register_msg(contacto, dc_id, dc_msg):
   if contacto in messagedb:
      if dc_id in messagedb[contacto]:
         if dc_msg in messagedb[contacto][dc_id]:
            t_reply = messagedb[contacto][dc_id][dc_msg]
            return t_reply
         else:
            return
      else:
         return
   else:
      return

def find_register_msg(contacto, dc_id, tg_msg):
   if contacto in messagedb:
      if dc_id in messagedb[contacto]:
         if tg_msg in messagedb[contacto][dc_id].values():
            for (key, value) in messagedb[contacto][dc_id].items():
                if value == tg_msg:
                   d_reply = key
                   return d_reply
         else:
            return
      else:
         return
   else:
      return

def get_tg_id(chat, bot):
    f_id = bot.get(str(chat.id))
    if f_id:
       tg_ids = [f_id]
    else:
       dchat = chat.get_name()
       tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
       if len(tg_ids)>0:
          bot.set(str(chat.id),tg_ids[-1])
    if len(tg_ids)>0:
       if tg_ids[-1].lstrip('-').isnumeric():
          f_id = int(tg_ids[-1])
       else:
          f_id = tg_ids[-1]
       return f_id
    else:
       return None

def print_dep_message(loader):
    if not loader.failed_modules:
        return
    sys.stderr.write("Make sure you have the correct dependencies installed\n")
    for failed, dep in loader.failed_modules.items():
        sys.stderr.write("For %s install %s\n" % (failed, dep))

async def convertsticker(infilepath,outfilepath):
    importer = None
    suf =  os.path.splitext(infilepath)[1][1:]
    print(suf)
    for p in importers:
        if suf in p.extensions:
           importer = p
           break
    exporter = exporters.get(os.path.splitext(outfilepath)[1][1:])
    if not exporter:
       print_dep_message(exporters)

    an = importer.process(infilepath)
    an.scale(128,128)
    exporter.process(an, outfilepath, lossless=False, method=3, quality=50, skip_frames=10)

async def read_unread(contacto,target,tg_id):
    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       mensajes = await client.get_messages(target, ids=[int(tg_id)])
       await mensajes[0].mark_read()
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print('Error marcando mensaje como leido\n'+code)

def async_read_unread(contacto, target, tg_id):
    loop.run_until_complete(read_unread(contacto, target, tg_id))

async def chat_news(bot, payload, replies, message):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ver sus chats!')
       return
    if message.get_sender_contact().addr not in chatdb:
       chatdb[message.get_sender_contact().addr] = {}
    try:
       if not os.path.exists(message.get_sender_contact().addr):
          os.mkdir(message.get_sender_contact().addr)
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       me = await client.get_me()
       my_id = me.id
       all_chats = await client.get_dialogs(ignore_migrated = True)
       chat_list = ''
       chat_count = 0
       is_full = (payload.lower().find('full')>=0)
       is_img = (payload.lower().find('img')>=0)
       is_private = (payload.lower().find('private')>=0)
       global bot_addr
       for d in all_chats:
           if d.unread_count>0:
              no_leidos = str(d.unread_count)
           else:
              if not is_full:
                 continue
              no_leidos = ''
           if hasattr(d.entity,'username') and d.entity.username:
              uname = str(d.entity.username)
           else:
              uname = 'None'
           if is_private:
              tchat = await client(functions.messages.GetPeerDialogsRequest(peers=[d.id]))
              if hasattr(tchat,'chats') and tchat.chats:
                 continue
           ttitle = "Unknown"
           last_message = ""
           send_by = ""
           profile_photo = ""
           if hasattr(d,'title'):
              ttitle = d.title
           tid = str(d.id)
           if True:
              titulo = str(ttitle)
              if my_id == d.id:
                 titulo = 'Mensajes guardados'
              if str(d.id) in chatdb[message.get_sender_contact().addr]:
                 comando = '<br><a href="mailto:'+bot_addr+'?body=/remove_'+str(d.id)+'">❌ Desvilcular</a>'
              else:
                 comando = '<br><a href="mailto:'+bot_addr+'?body=/load_'+str(d.id)+'">✅ Cargar</a>'
              try:
                  profile_letter = '<div style="font-size:50px;color:white;background:#7777ff;border-radius:25px;width:50px;height:50px"><center>'+titulo[0]+'</center></div>'
                  if is_img:
                     profile_photo = '<img src="data:image/jpeg;base64,{}" alt="{}" style="width:50px;height:50px;border-radius:25px"/>'.format(base64.b64encode(await client.download_profile_photo(d.id,bytes,download_big=False)).decode(),titulo)
                  else:
                     profile_photo = profile_letter
              except:
                  profile_photo = profile_letter
              if hasattr(d,'message') and d.message:
                 if hasattr(d.message,'from_id') and d.message.from_id:
                    if hasattr(d.message.from_id,'user_id') and d.message.from_id.user_id:
                       try:
                          full_pchat = await client(functions.users.GetFullUserRequest(id = d.message.from_id.user_id))
                          if hasattr(full_pchat,'users') and full_pchat.users:
                             send_by = '<br><b>'+str(full_pchat.users[0].first_name)+'</b>'
                       except:
                          print('Error obteniendo entidad '+str(d.message.from_id.user_id))
                          try:
                             pchat = await client.get_entity(d.message.from_id.user_id)
                             if hasattr(pchat, 'first_name') and pchat.first_name:
                                send_by = '<br><b>'+str(pchat.first_name)+'</b>'
                          except:
                             continue
                 if hasattr(d.message,'message') and d.message.message:
                    #last_message += send_by
                    last_message += d.message.message.replace('\n',' ')
                    if len(last_message)>50:
                       last_message = last_message[0:50]+'...'
                    else:
                       last_message = last_message
                 else:
                    last_message = '[imagen/archivo]'
              chat_count +=1
              chat_list += '<table><tr><td>'+profile_photo+'</td><td><b>'+titulo+'</b> <a style="color:white;background:red;border-radius:15px"> '+no_leidos+' </a>'+send_by+'<br>'+last_message+comando+'</td></tr></table><hr>'
              #bubbles
              #chat_list += '<br><div style="border-radius:3px;color:white;background:#7777ff">'+profile_photo+'<b>'+titulo+'</b> <a style="color:white;background:red;border-radius:15px">'+no_leidos+'</a>'+send_by+'<br>'+last_message+comando+'</div>'
              #img = await client.download_profile_photo(d.entity, message.get_sender_contact().addr)
       await client.disconnect()
       replies.add(text=str(chat_count)+' chats',html=chat_list)
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_chat_news(bot, payload, replies, message):
    """See a list of all your chats status/unread from telegram. Example: /news
    you can pass the parameter private to see only the private chat like: /news private
    you can pass the parameter full to see a full chat list like: /news full
    pass the img parameter to see the chats profile photos like: /news img"""
    loop.run_until_complete(chat_news(bot, payload, replies, message))


def link_to(bot, payload, replies, message):
    """Link chat with a Telegram chat"""
    if payload:
       tchat = payload.replace('@','')
       bot.set(str(message.chat.id), tchat)
       if DBXTOKEN:
          backup_db()
       replies.add(text='Se ha asociado el chat de Telegram '+payload+' con este chat')
    else:
       replies.add(text='Debe proporcionar una id de chat de Telegram, ejemplo: @deltachat2')

async def chat_info(bot, payload, replies, message):
    f_id = get_tg_id(message.chat, bot)
    if not f_id:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ver información del chat!')
       return
    if message.get_sender_contact().addr not in chatdb:
       chatdb[message.get_sender_contact().addr] = {}
    try:
       if not os.path.exists(message.get_sender_contact().addr):
          os.mkdir(message.get_sender_contact().addr)

       if f_id:
          #TODO show more chat information
          client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
          await client.connect()
          await client.get_dialogs()
          tinfo =""
          img = None
          if message.quote:
             t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
             if not t_reply:
                replies.add(text='No se encontró la referencia de este mensaje con el de Telegram', quote=message)
             else:
                mensaje = await client.get_messages(f_id, ids=[t_reply])
                if mensaje and mensaje[0]:
                   if mensaje[0].from_id:
                      if isinstance(mensaje[0].from_id, types.PeerUser):
                         full = await client(GetFullUserRequest(mensaje[0].from_id))
                         tinfo += "Por usuario:"
                         if full.users[0].username:
                            tinfo += "\n@👤: @"+str(full.users[0].username)
                         if full.users[0].first_name:
                            tinfo += "\nNombre: "+str(full.users[0].first_name)
                         if full.users[0].last_name:
                            tinfo += "\nApellidos: "+str(full.users[0].last_name)
                         tinfo += "\n🆔️: "+str(mensaje[0].from_id.user_id)
                         img = await client.download_profile_photo(mensaje[0].from_id.user_id)
                      elif isinstance(mensaje[0].from_id, types.PeerChannel):
                         full = await client(functions.channels.GetFullChannelRequest(channel = mensaje[0].from_id))
                         tinfo += "Por grupo/canal:"
                         if hasattr(full,'post_author') and full.post_author:
                            tinfo += "\nAutor: "+full.post_author
                         img = await client.download_profile_photo(mensaje[0].from_id.channel_id)
                      elif isinstance(mensaje[0].from_id, types.PeerChat):
                         full = await client(functions.messages.GetFullChatRequest(chat_id = mensaje[0].from_id))
                         tinfo += "Por chat:"
                      if hasattr(full,'about') and full.about:
                         tinfo += "\nBiografia: "+str(full.about)
                   tinfo += "\n\nMensaje:"
                   tinfo += "\nTelegram mensaje id: "+str(t_reply)
                   tinfo += "\nDeltaChat mensaje id: "+str(message.quote.id)
                   tinfo += "\nFecha de envio (UTC): "+str(mensaje[0].date)
                   replies.add(text=tinfo, html=mensaje[0].stringify(), filename=img, quote=message)
                else:
                   replies.add(text="El mensaje fue eliminado?")
             await client.disconnect()
             return
          pchat = await client.get_input_entity(f_id)

          if isinstance(pchat, types.InputPeerChannel):
             full_pchat = await client(functions.channels.GetFullChannelRequest(channel = pchat))
             if hasattr(full_pchat,'chats') and full_pchat.chats and len(full_pchat.chats)>0:
                tinfo += "\nTitulo: "+full_pchat.chats[0].title
                if hasattr(full_pchat.chats[0],'participants_count') and full_pchat.chats[0].participants_count:
                   tinfo += "\nParticipantes: "+str(full_pchat.chats[0].participants_count)
          elif isinstance(pchat, types.InputPeerUser) or isinstance(pchat, types.InputPeerSelf):
               full_pchat = await client(functions.users.GetFullUserRequest(id = pchat))
               if hasattr(full_pchat,'users') and full_pchat.users:
                  tinfo += "\nNombre: "+full_pchat.users[0].first_name
                  if full_pchat.users[0].last_name:
                     tinfo += "\nApellidos: "+full_pchat.users[0].last_name
                  if hasattr(full_pchat.users[0],"username") and full_pchat.users[0].username:
                     tinfo+="\n@: "+full_pchat.users[0].username
          elif isinstance(pchat, types.InputPeerChat):
               print('Hemos encontrado un InputPeerChat: '+str(f_id))
               full_pchat = await client(functions.messages.GetFullChatRequest(chat_id=pchat.id))
               if hasattr(full_pchat,'chats') and full_pchat.chats and len(full_pchat.chats)>0:
                  tinfo = full_pchat.chats[0].title
               if hasattr(full_pchat,'user') and full_pchat.user:
                   tinfo = full_pchat.user.first_name
          try:
             img = await client.download_profile_photo(f_id, message.get_sender_contact().addr)
          except:
             img = None
             print("Error descargando foto de perfil de "+str(f_id))
          await client.disconnect()
          replies.add(text=tinfo, html = "<code>"+str(full_pchat)+"</code>", filename = img, quote=message)
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_chat_info(bot, payload, replies, message):
    """Show message information from telegram. Example: reply a message with /info"""
    loop.run_until_complete(chat_info(bot, payload, replies, message))

async def pin_messages(bot, message, replies):
    if not message.quote:
       replies.add(text = "Debe responder a un mensaje para fijarlo")
       return
    f_id = get_tg_id(message.chat, bot)
    if not f_id:
       replies.add(text = "Este no es un chat de telegram!")
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
       if t_reply:
          await client.pin_message(f_id, t_reply)
          replies.add(text = 'Mensaje fijado!')
       else:
          replies.add(text = 'No se puede fijar el mensaje porque no esta asociado a un mensaje de Telegram!')
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_pin_messages(bot, message, replies):
    """Pin message in chats with right permission repling it, example:
    /pin
    """
    loop.run_until_complete(pin_messages(bot, message, replies))


async def forward_message(bot, message, replies, payload):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para reenviar mensajes!')
       return
    f_id = get_tg_id(message.chat, bot)
    if not f_id:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    parametros = payload.split()
    m_id = None
    d_id = None
    if len(parametros)>1:
       if parametros[0].isnumeric():
          m_id = int(parametros[0])
          s = payload.replace(parametros[0]+' ','',1)
          s = s.replace(' ','_')
          if s.isnumeric():
             d_id = int(s)
          else:
             d_id = s

    if not m_id or not d_id:
       replies.add('Debe proporcionar el id del mensaje a reenviar, un espacio y el id del chat destino, ejemplo: /forward 1234 deltachat2')
       return
    try:
       #replies.add(text='Reanviando mensaje... '+str(m_id)+' a '+str(d_id)+' de '+str(f_id))
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       await client.forward_messages(d_id, m_id, f_id)
       replies.add(text='Mensaje reenviado!')
       await client.disconnect()
    except Exception as e:
       code = str(sys.exc_info())
       print(code)
       replies.add(text=code)

def async_forward_message(bot, message, replies, payload):
    """Forward message to other chats using the message id and chat id, example:
    /forward 3648 me
    this forward the message id 3648 to your saved messages
    """
    loop.run_until_complete(forward_message(bot, message, replies, payload))


def list_chats(replies, message, payload):
    """Show your linked deltachat/telegram chats. Example /list"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para listar sus chats!')
       return
    if message.get_sender_contact().addr not in chatdb:
       chatdb[message.get_sender_contact().addr] = {}
    chat_list = ''
    for (key, value) in chatdb[message.get_sender_contact().addr].items():
        chat_list+='\n\n'+value+'\n❌ Desvincular: /remove_'+key
    replies.add(text = chat_list)

async def add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    alloweddb ={'deltachat2':''}
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para automatizar chats')
       return
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       is_channel = False
       is_user = False
       is_allowed = False
       tchat = await client(functions.messages.GetPeerDialogsRequest(peers=[target] ))
       if hasattr(tchat,'chats') and tchat.chats and hasattr(tchat.chats[0],'broadcast'):
          if tchat.chats[0].broadcast:
             is_channel = True
          if hasattr(tchat.chats[0],'username') and tchat.chats[0].username:
             if tchat.chats[0].username in alloweddb:
                is_allowed = True
       else:
          is_user = True
       sin_leer = tchat.dialogs[0].unread_count
       await client.disconnect()
    except Exception as e:
       code = str(sys.exc_info())
       print(code)
       replies.add(text = code)
       return
    if message.get_sender_contact().addr in chatdb:
       if is_channel or is_user or is_allowed or bot.is_admin(message.get_sender_contact()):
          #{contact_addr:{chat_id:chat_type}}
          if message.get_sender_contact().addr not in autochatsdb:
             autochatsdb[message.get_sender_contact().addr]={}
          if str(message.chat.id) in autochatsdb[message.get_sender_contact().addr]:
             del autochatsdb[message.get_sender_contact().addr][str(message.chat.id)]
             replies.add(text='Se ha desactivado la automatizacion en este chat ('+str(len(autochatsdb[message.get_sender_contact().addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer!')
          else:
             if len(autochatsdb[message.get_sender_contact().addr])>=MAX_AUTO_CHATS and not bot.is_admin(message.get_sender_contact()):
                autochatsdb[message.get_sender_contact().addr][str(message.chat.id)]=target
                for (key,_) in autochatsdb[message.get_sender_contact().addr].items():
                    del autochatsdb[message.get_sender_contact().addr][str(key)]
                    replies.add(text='Solo se permiten automatizar hasta 5 chats, se ha automatizado este chat ('+str(len(autochatsdb[message.get_sender_contact().addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer y se ha desactivado la automatizacion del chat '+str(bot.get_chat(int(key)).get_name()))
                    break
             else:
                autochatsdb[message.get_sender_contact().addr][str(message.chat.id)]=target
                replies.add(text='Se ha automatizado este chat ('+str(len(autochatsdb[message.get_sender_contact().addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer!')
       else:
          replies.add(text='Solo se permite automatizar chats privados, canales y algunos grupos permitidos por ahora')
    else:
       replies.add(text='Este no es un chat de Telegram!')


def async_add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    loop.run_until_complete(add_auto_chats(bot, replies, message))
    saveautochats()
    #if DBXTOKEN:
    #   backup_db(bot)

async def save_delta_chats(replies, message):
    """This is for save the chats deltachat/telegram in Telegram Saved message user"""
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       tf = open(message.get_sender_contact().addr+'.json', 'w')
       json.dump(chatdb[message.get_sender_contact().addr], tf)
       tf.close()
       await client.connect()
       my_id = await client(functions.users.GetFullUserRequest('me'))
       if my_id.full_user.pinned_msg_id:
          my_pin = await client.get_messages('me', ids=my_id.full_user.pinned_msg_id)
          await client.edit_message('me',my_pin,'!!!Atención, este mensaje es parte del puente con deltachat, NO lo borre ni lo quite de los anclados o perdera el vinculo con telegram\n'+str(datetime.now()), file = message.get_sender_contact().addr+'.json')
       else:
          my_new_pin = await client.send_file('me', message.get_sender_contact().addr+'.json')
          await client.pin_message('me', my_new_pin)
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_save_delta_chats(replies, message):
    loop.run_until_complete(save_delta_chats(replies, message))

async def load_delta_chats(contacto, replies = None):
    """This is for load the chats deltachat/telegram from Telegram saved message user"""
    if contacto not in logindb:
       if replies:
          replies.add(text = 'Debe iniciar sesión para cargar sus chats!')
       return
    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       my_id = await client(functions.users.GetFullUserRequest('me'))
       if hasattr(my_id.full_user,'pinned_msg_id') and my_id.full_user.pinned_msg_id:
          my_pin = await client.get_messages('me', ids=my_id.full_user.pinned_msg_id)
          await client.download_media(my_pin)
          if os.path.isfile(contacto+'.json'):
             tf = open(contacto+'.json','r')
             chatdb[contacto]=json.load(tf)
             tf.close()
             os.remove(contacto+'.json')
       else:
          print('No pinned message!')
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print('Error loading delta chats of '+contacto+'\n'+code)


def async_load_delta_chats(message, replies):
    loop.run_until_complete(load_delta_chats(contacto=message.get_sender_contact().addr, replies=replies))

def remove_chat(bot, payload, replies, message):
    """Remove current chat from telegram bridge. Example: /remove
       you can pass the all parametre to remove all chats like: /remove all or a telegram chat id
    like: /remove -10023456789"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para eliminar chats!')
       return
    if message.get_sender_contact().addr not in chatdb:
       replies.add(text = 'No tiene ningun chat vinculado!')
       return
    if not payload or payload =='':
       target = get_tg_id(message.chat, bot)
       if not target:
          replies.add(text = 'Este no es un chat de Telegram!')
          return
    else:
       target = payload.replace(' ','_')
    if target == 'all':
       chatdb[message.get_sender_contact().addr].clear()
       if message.get_sender_contact().addr in autochatsdb:
          autochatsdb[message.get_sender_contact().addr].clear()
       replies.add(text = 'Se desvincularon todos sus chats de telegram.')
    else:
       if target in chatdb[message.get_sender_contact().addr]:
          c_title = chatdb[message.get_sender_contact().addr][target]
          del chatdb[message.get_sender_contact().addr][target]
          replies.add(text = 'Se desvinculó el chat delta '+str(c_title)+' con el chat telegram '+str(target))
       else:
          replies.add(text = 'Este chat no está vinculado a telegram')
       try:
          if message.get_sender_contact().addr in autochatsdb:
             for (key, value) in autochatsdb[message.get_sender_contact().addr].items():
                 if str(value) == target:
                    del autochatsdb[message.get_sender_contact().addr][str(key)]
                    replies.add(text = 'Se desactivaron las actualizaciones para el chat '+str(key))
       except:
          print('Dictionary change size...')
    async_save_delta_chats(replies, message)


def logout_tg(payload, replies, message):
    """Logout from Telegram and delete the token session for the bot"""
    if message.get_sender_contact().addr in logindb:
       del logindb[message.get_sender_contact().addr]
       if message.get_sender_contact().addr in autochatsdb:
          autochatsdb[message.get_sender_contact().addr].clear()
       savelogin()
       replies.add(text = 'Se ha cerrado la sesión en telegram, puede usar su token para iniciar en cualquier momento pero a nosotros se nos ha olvidado')
    else:
       replies.add(text = 'Actualmente no está logueado en el puente')

async def login_num(payload, replies, message):
    try:
       if message.chat.is_group():
          return
       forzar_sms = False
       parametros = payload.split()
       if len(parametros)<1:
          replies.add(text='Debe escribir el codigo del pais mas el numero (sin espacios), ejemplo /login +5355555555')
          return
       if len(parametros) == 2:
          if parametros[1].lower()!='sms':
             replies.add(text='El numero no debe contener espacios!.')
             return
          else:
             forzar_sms = True
       clientdb[message.get_sender_contact().addr] = TC(StringSession(), api_id, api_hash)
       await clientdb[message.get_sender_contact().addr].connect()
       try:
          me = await clientdb[message.get_sender_contact().addr].send_code_request(parametros[0], force_sms = forzar_sms)
       except errors.FloodWaitError as e:
          print(e)
          replies.add(text = 'Atencion!\nHa solicitado demasiadas veces el codigo y Telegram le ha penalizado con '+str(e.seconds)+' segundos de espera para poder solicitar nuevamente el codigo!')
          return
       hashdb[message.get_sender_contact().addr] = me.phone_code_hash
       phonedb[message.get_sender_contact().addr] = parametros[0]
       replies.add(text = 'Se ha enviado un codigo de confirmacion al numero '+parametros[0]+', puede que le llegue a su cliente de Telegram o reciba una llamada, por favor introdusca /sms CODIGO para iniciar')
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text='Debe escribir el codigo del pais mas el numero (sin espacios), ejemplo /login +5355555555')

def async_login_num(payload, replies, message):
    """Start session in Telegram. Example: /login +5312345678"""
    loop.run_until_complete(login_num(payload, replies, message))

async def login_code(payload, replies, message):
    try:
       if message.chat.is_group():
          return
       if message.get_sender_contact().addr in phonedb and message.get_sender_contact().addr in hashdb and message.get_sender_contact().addr in clientdb:
          try:
              me = await clientdb[message.get_sender_contact().addr].sign_in(phone=phonedb[message.get_sender_contact().addr], phone_code_hash=hashdb[message.get_sender_contact().addr], code=payload)
              logindb[message.get_sender_contact().addr]=clientdb[message.get_sender_contact().addr].session.save()
              savelogin()
              replies.add(text = 'Se ha iniciado sesiòn correctamente, copie y pegue el mensaje del token en privado para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats.')
              replies.add(text = '/token '+logindb[message.get_sender_contact().addr])
              await clientdb[message.get_sender_contact().addr].disconnect()
              del clientdb[message.get_sender_contact().addr]
          except SessionPasswordNeededError:
              smsdb[message.get_sender_contact().addr]=payload
              replies.add(text = 'Tiene habilitada la autentificacion de doble factor, por favor introdusca /pass PASSWORD para completar el loguin.')
       else:
          replies.add(text = 'Debe introducir primero si numero de movil con /login NUMERO')
    except Exception as e:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_login_code(payload, replies, message):
    """Confirm session in Telegram. Example: /sms 12345"""
    loop.run_until_complete(login_code(payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)

async def login_2fa(payload, replies, message):
    try:
       if message.chat.is_group():
          return
       if message.get_sender_contact().addr in phonedb and message.get_sender_contact().addr in hashdb and message.get_sender_contact().addr in clientdb and message.get_sender_contact().addr in smsdb:
          me = await clientdb[message.get_sender_contact().addr].sign_in(phone=phonedb[message.get_sender_contact().addr], password=payload)
          logindb[message.get_sender_contact().addr]=clientdb[message.get_sender_contact().addr].session.save()
          savelogin()
          replies.add(text = 'Se ha iniciado sesiòn correctamente, copie y pegue el mensaje del token en privado para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats.')
          replies.add(text = '/token '+logindb[message.get_sender_contact().addr])
          await clientdb[message.get_sender_contact().addr].disconnect()
          del clientdb[message.get_sender_contact().addr]
          del smsdb[message.get_sender_contact().addr]
       else:
          if message.get_sender_contact().addr not in clientdb:
             replies.add(text = 'Debe introducir primero si numero de movil con /login NUMERO')
          else:
             if message.get_sender_contact().addr not in smsdb:
                replies.add(text = 'Debe introducir primero el sms que le ha sido enviado con /sms CODIGO')
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_login_2fa(payload, replies, message):
    """Confirm session in Telegram with 2FA. Example: /pass PASSWORD"""
    loop.run_until_complete(login_2fa(payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)

async def login_session(payload, replies, message):
    if message.chat.is_group():
       return
    if message.get_sender_contact().addr not in logindb:
       try:
           hash = payload.replace(' ','_')
           client = TC(StringSession(hash), api_id, api_hash)
           await client.connect()
           my = await client.get_me()
           if my.first_name:
              first_name= my.first_name
           else:
              first_name= ""
           if my.last_name:
              last_name= my.last_name
           else:
              last_name= ""
           nombre= (first_name + ' ' + last_name).strip()
           await client.disconnect()
           logindb[message.get_sender_contact().addr] = hash
           if DBXTOKEN:
              savelogin()
           replies.add(text='Se ha iniciado sesión correctamente '+str(nombre))
       except:
          code = str(sys.exc_info())
          print(code)
          replies.add(text='Error al iniciar sessión:\n'+code)
    else:
       replies.add(text='Su token es:\n\n'+logindb[message.get_sender_contact().addr])

def async_login_session(payload, replies, message):
    """Start session using your token or show it if already login. Example: /token abigtexthashloginusingintelethonlibrary..."""
    loop.run_until_complete(login_session(payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)

async def updater(bot, payload, replies, message):
    global DBXTOKEN
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para cargar sus chats!')
       return
    if message.get_sender_contact().addr not in chatdb:
       chatdb[message.get_sender_contact().addr] = {}
    try:
       if not os.path.exists(message.get_sender_contact().addr):
          os.mkdir(message.get_sender_contact().addr)
       contacto = message.get_sender_contact()
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       me = await client.get_me()
       my_id = me.id
       all_chats = await client.get_dialogs(ignore_migrated = True)
       chats_limit = 5
       filtro = payload.replace(' ','_')
       filtro = filtro.replace('@','')
       ya_agregados = ''
       #replies.add(text = 'Obteniendo chats...'+filtro)
       for d in all_chats:
           if hasattr(d.entity,'username') and d.entity.username:
              uname = str(d.entity.username)
           else:
              uname = 'None'
           ttitle = "Unknown"
           if hasattr(d,'title'):
              ttitle = d.title
           tid = str(d.id)
           find_only = False
           if payload.lower()=='#privates':
              private_only = hasattr(d.entity,'participants_count')
           else:
              private_only = False
           if payload!='' and payload.lower()!='#privates':
              if ttitle.lower().find(payload.lower())>=0 or tid == payload or uname.lower() == filtro.lower():
                 find_only = False
              else:
                 find_only = True
           if str(d.id) not in chatdb[message.get_sender_contact().addr] and not private_only and not find_only:
              if DBXTOKEN:
                 titulo = str(ttitle)
                 if my_id == d.id:
                    titulo = 'Mensajes guardados'
              else:
                 titulo = str(ttitle)+' ['+str(d.id)+']'
                 if my_id == d.id:
                    titulo = 'Mensajes guardados ['+str(d.id)+']'
              chat_id = bot.create_group(titulo, [contacto])
              img = await client.download_profile_photo(d.entity, message.get_sender_contact().addr)
              try:
                 if img and os.path.exists(img):
                    chat_id.set_profile_image(img)
              except:
                 print('Error al poner foto del perfil al chat:\n'+str(img))
              chats_limit-=1
              chatdb[message.get_sender_contact().addr][str(d.id)] = str(chat_id.get_name())
              if d.unread_count == 0:
                 replies.add(text = "Estas al día con "+ttitle+" id:[`"+str(d.id)+"`]\n/more", chat = chat_id)
              else:
                 replies.add(text = "Tienes "+str(d.unread_count)+" mensajes sin leer de "+ttitle+" id:[`"+str(d.id)+"`]\n/more", chat = chat_id)
              bot.set(str(chat_id.id),str(d.id))
              if chats_limit<=0:
                 break
           else:
              if str(d.id) in chatdb[message.get_sender_contact().addr]:
                 ya_agregados += '\n'+str(ttitle)+' /remove_'+str(d.id)
       await client.disconnect()
       if ya_agregados!='':
          replies.add(text='Ya tienes agregados:\n'+ya_agregados+'\n\nUse /list para mostrar sus chats vinculados')
       replies.add(text='Se agregaron '+str(5-chats_limit)+' chats a la lista!')
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_updater(bot, payload, replies, message):
    """Load chats from telegram. Example: /load
    you can pass #privates for load private only chats like: /load #privates
    or only chats with some words in title like: /load delta chat
    if you use the chat id only load this chat"""
    loop.run_until_complete(updater(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_save_delta_chats(replies = replies, message = message)

async def click_button(bot, message, replies, payload):
    parametros = payload.split()
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión usar los botones!')
       return
    if len(parametros)<2:
       replies.add(text = 'Faltan parametros, debe proporcionar el id de mensaje y al menos el numero de columna')
       return
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       all_messages = await client.get_messages(target, ids = [int(parametros[0])])
       n_column = int(parametros[1])
       if len(parametros)<3:
          n_row = 0
       else:
          n_row = int(parametros[2])
       for m in all_messages:
           await m.click(n_column, n_row)
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_click_button(bot, message, replies, payload):
    """Make click on a message bot button"""
    loop.run_until_complete(click_button(bot = bot, message = message, replies = replies, payload = payload))
    parametros = payload.split()
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=parametros[0], dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))

async def react_button(bot, message, replies, payload):
    parametros = payload.split()
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para reaccionar!')
       return
    if message.quote:
       t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
       if not t_reply:
          replies.add(text = 'No se encontro la referencia de este mensaje!')
          return
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if len(parametros)<1:
          pchat = await client.get_input_entity(target)
          av_reactions = None
          if isinstance(pchat, types.InputPeerChannel):
             full_pchat = await client(functions.channels.GetFullChannelRequest(channel = pchat))
             if hasattr(full_pchat.full_chat,'available_reactions') and full_pchat.full_chat.available_reactions:
                av_reactions = full_pchat.full_chat.available_reactions
          elif isinstance(pchat, types.InputPeerUser) or isinstance(pchat, types.InputPeerSelf):
               full_pchat = await client(functions.users.GetFullUserRequest(id = pchat))
               if hasattr(full_pchat.full_user,"available_reactions") and full_pchat.full_user.available_reactions:
                  av_reactions = full_pchat.full_user.available_reactions
          elif isinstance(pchat, types.InputPeerChat):
               print('Hemos encontrado un InputPeerChat: '+str(f_id))
               full_pchat = await client(functions.messages.GetFullChatRequest(chat_id=pchat.id))
               if hasattr(full_pchat,'available_reactions') and full_pchat.available_reactions:
                  av_reactions = full_pchat.available_reactions
          if av_reactions:
             if len(av_reactions)>0:
                replies.add(text = "Reacciones disponibles en este chat:\n\n"+''.join([r for r in av_reactions]))
             else:
                replies.add(text = "No se permiten las reacciones en este chat!")
          else:
             full_reactions = await client(functions.messages.GetAvailableReactionsRequest(0))
             text_reactions = ''
             for r in full_reactions.reactions:
                 text_reactions+=r.reaction
             replies.add(text = "Reacciones disponibles en este chat:\n\n"+text_reactions)
       else:
          await client.send_reaction(target,t_reply,parametros[0])
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_react_button(bot, message, replies, payload):
    """Send reaction to message repling it like: /react ❤"""
    loop.run_until_complete(react_button(bot = bot, message = message, replies = replies, payload = payload))
    t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=str(t_reply), dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))


async def load_chat_messages(bot: DeltaBot, message = Message, replies = Replies, payload = None, dc_contact = None, dc_id = None, is_auto = False):
    global DBXTOKEN
    contacto = dc_contact
    chat_id = bot.get_chat(int(dc_id))
    dchat = chat_id.get_name()
    if is_auto:
       max_limit = MAX_MSG_LOAD_AUTO
       is_down = False
       is_comment = False
    else:
       max_limit = MAX_MSG_LOAD
       is_down = message.text.lower().startswith('/down')
       is_comment = message.text.lower().startswith('/comment')
    myreplies = Replies(bot, logger=bot.logger)
    target = get_tg_id(chat_id, bot)
    if not target:
       myreplies.add(text = 'Este no es un chat de telegram!', chat = chat_id)
       myreplies.send_reply_messages()
       return

    if contacto not in logindb:
       myreplies.add(text = 'Debe iniciar sesión para cargar los mensajes!', chat = chat_id)
       myreplies.send_reply_messages()
       return

    if not os.path.exists(contacto):
       os.mkdir(contacto)

    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash, auto_reconnect=not is_auto, retry_delay = 16)
       await client.connect()
       await client.get_dialogs()
       tchat = await client(functions.messages.GetPeerDialogsRequest(peers=[target] ))
       ttitle = 'Unknown'
       #extract chat title
       if hasattr(tchat,'chats') and tchat.chats:
          ttitle = tchat.chats[0].title
       else:
          if hasattr(tchat,'users') and tchat.users[0]:
             if tchat.users[0].first_name:
                first_name= tchat.users[0].first_name
             else:
                first_name= ""
             if tchat.users[0].last_name:
                last_name= tchat.users[0].last_name
             else:
                last_name= ""
             ttitle = (first_name + ' ' + last_name).strip()
       sin_leer = tchat.dialogs[0].unread_count
       limite = 0
       load_history = False
       show_id = False
       if payload and payload.lstrip('-').isnumeric():
          if payload.isnumeric():
             all_messages = await client.get_messages(target, limit = 10, ids = [int(payload)])
          else:
             all_messages = await client.get_messages(target, min_id = int(payload.lstrip('-')), limit = int(payload.lstrip('-'))+10)
             load_history = True
       else:
          if payload.lower()=='last':
             show_id = True
             all_messages = await client.get_messages(target, limit = 1)
          else:
             all_messages = await client.get_messages(target, limit = sin_leer)
             if payload and payload.startswith('+') and payload.lstrip('+').isnumeric() and bot.is_admin(contacto):
                max_limit = int(payload.lstrip('+'))
       #print(str(contacto)+' '+str(dchat)+': '+str(len(all_messages)))
       if sin_leer>0 or load_history or show_id:
          all_messages.reverse()
       m_id = -1
       dc_msg = -1
       for m in all_messages:
           if m and limite<max_limit:
              mquote = ''
              quote = None
              mservice = ''
              file_attach = ''
              file_title = '[ARCHIVO]'
              no_media = True
              html_buttons = ''
              msg_id = ''
              tipo = None
              text_message = ''
              poll_message = ''
              fwd_text = ''
              html_spoiler = None
              reactions_text = ''
              comment_text = ''
              sender_name = None
              if show_id:
                 msg_id = '\n'+str(m.id)

              #TODO try to determine if deltalab or deltachat to use m.message (not markdown) or m.text (raw text) instead
              if hasattr(m,'text') and m.text:
                 text_message = str(m.text)
              else:
                 text_message = ''

              #check if message has spoiler text
              if hasattr(m, 'entities') and m.entities:
                 for ent in m.entities:
                     ent_type_str = str(ent)
                     if ent_type_str.find('MessageEntitySpoiler')>=0:
                        html_spoiler = text_message
                        text_message = hide_spoiler(m.message, ent.offset, ent.length)
                        break
              #check if message has comments
              #if hasattr(m,'replies') and m.replies and hasattr(m.replies,'comments') and m.replies.comments:
              if hasattr(m,'post') and m.post:
                 try:
                    #comentarios = await client(functions.messages.GetRepliesRequest(peer=target, msg_id=m.id, offset_id=m.id, offset_date=datetime(2018, 6, 25), add_offset=0, limit=100, max_id=0, min_id=0, hash=0 ))
                    comentarios = await client.get_messages(target, reply_to=m.id, limit = 200)
                 except:
                    comentarios = None
                 if comentarios and not is_comment:
                    comment_text = '\n\n---\n'+str(len(comentarios))+' comentarios > /comment_'+str(m.id)
                 if is_comment and comentarios and len(comentarios)>0:
                    comentarios.reverse()
                    if html_spoiler:
                       html_spoiler +=str(len(comentarios)) + " comentarios<hr>"
                    else:
                       html_spoiler = str(len(comentarios)) + " comentarios<hr>"
                    for coment in comentarios:
                        if isinstance(coment.from_id, types.PeerUser):
                           full = await client(GetFullUserRequest(coment.from_id))
                           from_coment = str(full.users[0].first_name)
                        else:
                           from_coment = "Unknown"
                        if coment.photo:
                           file_comment = '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await coment.download_media(bytes)).decode(),coment.raw_text)
                        elif coment.media and hasattr(coment.media,'document') and coment.media.document and hasattr(coment.media.document,'thumbs') and coment.media.document.thumbs:
                           file_comment = '<center><img src="data:image/png;base64,{}" alt="{}"/></center>'.format(base64.b64encode(await coment.download_media(bytes, thumb=0)).decode(),coment.raw_text)
                        else:
                           file_comment = (coment.message or '[ARCHIVO/VIDEO]').replace('\n', '<br>')
                        html_spoiler += "<br><div style='border-radius:10px;color:white;background:#7777ff;padding-left:5px;padding-top:5px;padding-right:5px;padding-bottom:5px'><b>"+from_coment+"</b><br>"+file_comment+"</div>"

              #check if message is a forward
              if m.fwd_from:
                 fwd_text = 'Mensaje reenviado\n'
                 if m.fwd_from.from_id:
                    if isinstance(m.fwd_from.from_id, types.PeerUser):
                       full = await client(GetFullUserRequest(m.fwd_from.from_id))
                       if full.users[0].first_name:
                          fwd_first = str(full.users[0].first_name)
                       else:
                          fwd_first = ""
                       if full.users[0].last_name:
                          fwd_last = str(full.users[0].last_name)
                       else:
                          fwd_last = ""
                       fwd_text += "De: "+str(fwd_first+' '+fwd_last).strip()+"\n\n"
                    elif isinstance(m.fwd_from.from_id, types.PeerChannel):
                       full = await client(functions.channels.GetFullChannelRequest(channel = m.fwd_from.from_id))
                       if hasattr(full,'chats') and full.chats and hasattr(full.chats[0],'title'):
                          fwd_text += "De: "+str(full.chats[0].title)+"\n\n"
                    elif isinstance(m.fwd_from.from_id, types.PeerChat):
                       full = await client(functions.messages.GetFullChatRequest(chat_id = m.fwd_from.from_id))
                       if hasattr(full,'chats') and full.chats and hasattr(full.chats[0],'title'):
                          fwd_text += "De chat:"+full.chats[0].title+"\n"

              #check if message is a reply
              if hasattr(m,'reply_to') and m.reply_to:
                 if hasattr(m.reply_to,'reply_to_msg_id') and m.reply_to.reply_to_msg_id:
                    dc_mid = find_register_msg(contacto, int(dc_id), m.reply_to.reply_to_msg_id)
                    if dc_mid:
                       try:
                          quote = bot.account.get_message_by_id(dc_mid)
                       except:
                          print('Unregister dc_msg '+str(dc_mid))
                    if not quote:
                       mensaje = await client.get_messages(target, ids = [m.reply_to.reply_to_msg_id])
                       if mensaje and mensaje[0]:
                          reply_text = ''
                          if hasattr(mensaje[0],'sender') and mensaje[0].sender and hasattr(mensaje[0].sender,'first_name') and mensaje[0].sender.first_name:
                             if mensaje[0].sender.first_name:
                                first_name= mensaje[0].sender.first_name
                             else:
                                first_name= ""
                             if mensaje[0].sender.last_name:
                                last_name= mensaje[0].sender.last_name
                             else:
                                last_name= ""
                             reply_send_by = str((first_name + ' ' + last_name).strip())+": "
                          else:
                             reply_send_by = ""
                          if mensaje[0].poll:
                             if hasattr(mensaje[0].poll.poll, 'question') and mensaje[0].poll.poll.question:
                                reply_text+='📊 '+mensaje[0].poll.poll.question
                          if hasattr(mensaje[0],'media') and mensaje[0].media:
                             if hasattr(mensaje[0].media,'photo'):
                                reply_text += '[FOTO]'
                          if hasattr(mensaje[0],'document') and mensaje[0].document:
                             reply_text += '[ARCHIVO]'
                          reply_msg = mensaje[0].message
                          if hasattr(mensaje[0], 'entities') and mensaje[0].entities:
                             for ent in mensaje[0].entities:
                                 ent_type_str = str(ent)
                                 if ent_type_str.find('MessageEntitySpoiler')>=0:
                                    reply_msg = hide_spoiler(reply_msg, ent.offset, ent.length)
                                    break
                          reply_text += reply_msg
                          if len(reply_text)>60:
                             reply_text = reply_text[0:60]+'...'
                          mquote = '>'+reply_send_by+reply_text.replace('\n','\n>')+'\n\n'

              #check if message is a system message
              if hasattr(m,'action') and m.action:
                 mservice = '⚙\n'
                 if isinstance(m.action, types.MessageActionPinMessage):
                    mservice += '_📌Fijó el mensaje_\n'
                 elif isinstance(m.action, types.MessageActionChatAddUser):
                    mservice += '_Se unió al grupo_\n'
                 elif isinstance(m.action, types.MessageActionChatJoinedByLink):
                    mservice += '_Se unió al grupo usando un enlace de invitación_\n'
                 elif isinstance(m.action, types.MessageActionChatDeleteUser):
                    mservice += '_Salió del grupo_\n'
                 elif isinstance(m.action, types.MessageActionChannelCreate):
                    mservice += '_Se creo el grupo/canal_\n'
                 elif isinstance(m.action, types.MessageActionPhoneCall):
                    mservice += '_📞Llamada_\n'

              #extract sender name
              if hasattr(m,'sender') and m.sender and hasattr(m.sender,'first_name') and m.sender.first_name:
                 first_name= m.sender.first_name
                 if m.sender.last_name:
                    last_name= m.sender.last_name
                 else:
                    last_name= ""
                 if CAN_IMP:
                    send_by = ""
                    sender_name = str((first_name + " " + last_name).strip())
                 else:
                    send_by = str((first_name + " " + last_name).strip())+":\n"
              else:
                 send_by = ""

              #check if message have buttons
              if hasattr(m,'reply_markup') and m.reply_markup and hasattr(m.reply_markup,'rows'):
                 nrow = 0
                 html_buttons = '\n\n---\n'
                 for row in m.reply_markup.rows:
                     html_buttons += '\n'
                     ncolumn = 0
                     for b in row.buttons:
                         if hasattr(b,'url') and b.url:
                            html_buttons += '[['+str(b.text)+']('+str(b.url)+')] '
                         else:
                            html_buttons += '['+str(b.text)+' /c_'+str(m.id)+'_'+str(nrow)+'_'+str(ncolumn)+'] '
                         ncolumn += 1
                     html_buttons += '\n'
                     nrow += 1
              down_button = "\n⬇ /down_"+str(m.id)+"\n⏩ /forward_"+str(m.id)+"_tg_file_link_bot\n⏩ /forward_"+str(m.id)+"_DirectLinkGeneratorbot\n⏩ /forward_"+str(m.id)+"_aiouploaderbot"

              #check if message is a poll
              if m.poll:
                 if hasattr(m.poll.poll, 'question') and m.poll.poll.question:
                    poll_message+='\n📊 '+m.poll.poll.question+'\n\n'
                    total_results = m.poll.results.total_voters
                    if m.poll.results.results and total_results>0:
                       n_results = 0
                       for res in m.poll.results.results:
                           if res.chosen:
                              if res.correct:
                                 mark_text = "✅ "
                              else:
                                 mark_text = "☑ "
                           else:
                              mark_text = "🔳 "
                           poll_message+='\n\n'+mark_text+str(round((res.voters/total_results)*100))+'% ('+str(res.voters)+') '+m.poll.poll.answers[n_results].text
                           n_results+=1
                    else:
                       if hasattr(m.poll.poll,'answers') and m.poll.poll.answers:
                          n_option = 0
                          for ans in m.poll.poll.answers:
                              poll_message+='\n\n🔳 '+ans.text+' /c_'+str(m.id)+'_'+str(n_option)
                              n_option+=1
                    poll_message+='\n\n'+str(total_results)+' votos'

              #check if message have reactions
              if hasattr(m,'reactions') and m.reactions:
                 if hasattr(m.reactions,'results') and m.reactions.results:
                    reactions_text += "\n\n"
                    for react in m.reactions.results:
                        reactions_text += "("+('•' if react.chosen else '')+react.reaction+str(react.count)+") "
                    reactions_text += "\n\n"

              #check if message have document
              if hasattr(m,'document') and m.document:
                 if m.document.size<MIN_SIZE_DOWN or (is_down and m.document.size<MAX_SIZE_DOWN):
                    #print('Descargando archivo...')
                    file_attach = await client.download_media(m.document, contacto)
                    #Try to convert all tgs sticker to png
                    try:
                       if file_attach.lower().endswith('.webp') or file_attach.lower().endswith('.tgs'):
                          tipo = "sticker"
                          if CAN_IMP:
                             send_by = sender_name+":"
                       #if file_attach.lower().endswith('.tgs'):
                          #filename, file_extension = os.path.splitext(file_attach)
                          #attach_converted = filename+'.webp'
                          #await convertsticker(file_attach,attach_converted)
                          #file_attach = attach_converted
                          #tipo = "sticker"
                    except:
                       print('Error converting tgs file '+str(file_attach))
                    myreplies.add(text = fwd_text+mquote+send_by+"\n"+str(text_message)+reactions_text+comment_text+html_buttons+msg_id, filename = file_attach, viewtype = tipo, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                 else:
                    #print('Archivo muy grande!')
                    if hasattr(m.document,'attributes') and m.document.attributes:
                       for attr in m.document.attributes:
                           if hasattr(attr,'file_name') and attr.file_name:
                              file_title = attr.file_name
                           elif hasattr(attr,'title') and attr.title:
                              file_title = attr.title
                    myreplies.add(text = fwd_text+mquote+send_by+str(text_message)+"\n"+str(file_title)+" "+str(sizeof_fmt(m.document.size))+down_button+reactions_text+comment_text+html_buttons+msg_id, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                 no_media = False

              #check if message have media
              if hasattr(m,'media') and m.media:
                 #check if message have photo
                 f_size = 0
                 if hasattr(m.media,'photo') and m.media.photo:
                    if hasattr(m.media.photo,'sizes') and m.media.photo.sizes and len(m.media.photo.sizes)>0:
                       for sz in m.media.photo.sizes:
                           if hasattr(sz,'size') and sz.size:
                              f_size = sz.size
                              break
                    if f_size<MIN_SIZE_DOWN or (is_down and f_size<MAX_SIZE_DOWN):
                       #print('Descargando foto...')
                       file_attach = await client.download_media(m.media, contacto)
                       myreplies.add(text = fwd_text+mquote+send_by+"\n"+str(text_message)+reactions_text+comment_text+html_buttons+msg_id, filename = file_attach, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                    else:
                       #print('Foto muy grande!')
                       myreplies.add(text = fwd_text+mquote+send_by+str(text_message)+"\nFoto de "+str(sizeof_fmt(f_size))+down_button+reactions_text+comment_text+html_buttons+msg_id, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                    no_media = False

                 #check if message have media webpage
                 if hasattr(m.media,'webpage') and m.media.webpage:
                    if True:
                       no_media = False
                       f_size = 0
                       if hasattr(m.media.webpage,'photo') and m.media.webpage.photo:
                          if hasattr(m.media.webpage.photo,'sizes') and m.media.webpage.photo.sizes and len(m.media.webpage.photo.sizes)>1:
                             for sz in m.media.webpage.photo.sizes:
                                 if hasattr(sz,'size') and sz.size:
                                    f_size = sz.size
                                    break
                             if f_size<MIN_SIZE_DOWN or (is_down and f_size<MAX_SIZE_DOWN):
                                #print('Descargando foto web...')
                                file_attach = await client.download_media(m.media, contacto)
                             else:
                                #print('Foto web muy grande!')
                                down_button = '\n[FOTO WEB] '+sizeof_fmt(f_size)+down_button
                                file_attach = ''

                       if hasattr(m.media.webpage,'document') and m.media.webpage.document:
                          if hasattr(m.media.webpage.document,'size') and m.media.webpage.document.size:
                             f_size = m.media.webpage.document.size
                             if f_size<MIN_SIZE_DOWN or (is_down and f_size<MAX_SIZE_DOWN):
                                #print('Descargando archivo web...')
                                file_attach = await client.download_media(m.media, contacto)
                             else:
                                #print('Archivo web muy grande!')
                                down_button = '\n[ARCHIVO WEB] '+sizeof_fmt(f_size)+down_button
                                file_attach = ''

                       if hasattr(m.media.webpage,'title') and m.media.webpage.title:
                          wtitle = m.media.webpage.title
                       else:
                          wtitle = ''
                       if text_message!='':
                          wmessage=str(text_message)+'\n'
                       else:
                          wmessage=''
                       if hasattr(m.media.webpage,'url') and m.media.webpage.url:
                          wurl = m.media.webpage.url
                       else:
                          wurl = ''

                       if file_attach!= '':
                          myreplies.add(text = fwd_text+mquote+send_by+str(wtitle)+"\n"+wmessage+str(wurl)+reactions_text+comment_text+html_buttons+msg_id, filename = file_attach, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                       else:
                          myreplies.add(text = fwd_text+mquote+send_by+str(wtitle)+"\n"+wmessage+str(wurl)+(down_button if f_size>0 else "")+reactions_text+comment_text+html_buttons+msg_id, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                    else:
                       no_media = True

              #send only text message
              if no_media:
                 myreplies.add(text = fwd_text+mservice+mquote+send_by+str(text_message)+poll_message+reactions_text+comment_text+html_buttons+msg_id, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)

              #mark message as read
              m_id = m.id
              #print('Leyendo mensaje '+str(m_id))
              dc_msg = myreplies.send_reply_messages()[0].id
              if file_attach!='' and os.path.exists(file_attach):
                 os.remove(file_attach)
                 head, tail = os.path.split(file_attach)
                 bot_attach = bot_home+'/.simplebot/accounts/'+encode_bot_addr+'/account.db-blobs/'+str(tail)
                 if os.path.exists(bot_attach):
                    os.remove(bot_attach)
              limite+=1
              register_msg(contacto, int(dc_id), int(dc_msg), int(m_id))
              if SYNC_ENABLED==0 or not is_auto:
                 await m.mark_read()
           else:
              if not load_history and not is_auto:
                 myreplies.add(text = "Tienes "+str(sin_leer-limite)+" mensajes sin leer de "+str(ttitle)+"\n➕ /more", chat = chat_id)
              break
       if SYNC_ENABLED and is_auto:
          #{'dc_id:dc_msg':[contact,tg_id,tg_msg]}
          if m_id>-1 and dc_msg>-1:
             unreaddb[str(dc_id)+':'+str(dc_msg)]=[contacto,target,m_id]
             bot.set('UNREADDB',json.dumps(unreaddb))
       if sin_leer-limite<=0 and not load_history and not is_auto:
          myreplies.add(text = "Estas al día con "+str(ttitle)+"\n➕ /more", chat = chat_id)

       if load_history:
          myreplies.add(text = "Cargar más mensajes:\n➕ /more_-"+str(m_id), chat = chat_id)
       myreplies.send_reply_messages()
       if DBXTOKEN:
          if dchat!=str(ttitle) and len(chat_id.get_contacts())<3:
             print('Actualizando nombre de chat...')
             chat_id.set_name(str(ttitle))
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       if not is_auto:
          myreplies.add(text=code, chat = chat_id)
          myreplies.send_reply_messages()


def async_load_chat_messages(bot, message, replies, payload):
    """Load more messages from telegram in a chat,
    you can add specific message id to load one message
    or with - sign before load messages from this id number. Examples:
    Load message #5: /more 5
    Load message from #10: /more -10
    Load last message in the chat: /more last"""
    loop.run_until_complete(load_chat_messages(bot=bot, message=message, replies=Replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))

def async_down_chat_messages(bot, message, replies, payload):
    """Download messages files from telegram in a chat,
    you can add specific message id to download one message
    or with - sign download messages from this id number. Examples:
    Download message #5: /down 5
    Download message from #10: /down -10
    Download last message in the chat: /down last"""
    loop.run_until_complete(load_chat_messages(bot=bot, message=message, replies=Replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))

def async_comment_chat_messages(bot, message, replies, payload):
    """Show comments messages from telegram in a channel post,
    you can add specific message id to show comment one message
    or with - sign show comment messages from this id number. Examples:
    show comments message #5: /comment 5
    show comments messages from #10: /comment -10
    show last comments message in the chat: /comment last"""
    loop.run_until_complete(load_chat_messages(bot=bot, message=message, replies=Replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))


async def echo_filter(bot, message, replies):
    """Write direct in chat to write a telegram chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login +CODIGOPAISNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    dchat = message.chat.get_name()

    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       mquote = ''
       t_reply = None
       t_comment = None
       if message.quote:
          t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
          if t_reply:
             t_message = await client.get_messages(target,ids=[t_reply])
             if t_message and hasattr(t_message[0],'post') and t_message[0].post:
                print('escribiendo en Canal...')
                t_comment = t_reply
                t_reply = None
          if not t_reply and not t_comment:
             if message.quote.is_gif():
                mquote += '[GIF]'
             elif message.quote.is_image():
                mquote += '[PHOTO]'
             elif message.quote.is_audio():
                 mquote += '[AUDIO]'
             elif message.quote.is_video():
                 mquote += '[VIDEO]'
             elif message.quote.is_file():
                 mquote += '[FILE]'
             mquote += ' '+message.quote.text
             if len(mquote)>65:
                mquote = mquote[0:65]+'...'
             mquote = '>'+mquote.replace('\n','\n>')+'\n\n'

       mtext = mquote+message.text
       if message.filename:
          if message.is_audio() or message.filename.lower().endswith('.aac'):
              m = await client.send_file(target, message.filename, voice_note=True, reply_to = t_reply, comment_to = t_comment)
              register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
          else:
             if len(mtext) > 1024:
                 m = await client.send_file(target, message.filename, caption = mtext[0:1024], reply_to = t_reply, comment_to = t_comment)
                 register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
                 for x in range(1024, len(mtext), 1024):
                     m = await client.send_message(target, mtext[x:x+1024])
                     register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
             else:
                m = await client.send_file(target, message.filename, caption = mtext, reply_to = t_reply, comment_to = t_comment)
                register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
       else:
          if len(mtext) > 4096:
             for x in range(0, len(mtext), 4096):
                 m = await client.send_message(target, mtext[x:x+4096], reply_to = t_reply, comment_to = t_comment)
                 register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
          else:
             m = await client.send_message(target,mtext, reply_to = t_reply, comment_to = t_comment)
             register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
       await client.disconnect()
    except:
       await client(SendMessageRequest(target, mtext))
       code = str(sys.exc_info())
       replies.add(text=code)

@simplebot.filter
def async_echo_filter(bot, message, replies):
    """Write direct in chat bridge to write to telegram chat"""
    global authorize_url
    if authorize_url and not message.chat.is_group():
       try:
          oauth_result = auth_flow.finish(message.text)
          replies.add(text='Se ha generado un nuevo codigo de acceso valido, copielo y sustituya DBXTOKEN por el mismo:\n\n'+oauth_result.refresh_token)
       except Exception as e:
          replies.add(text=str(e))
       authorize_url = None
       return
    loop.run_until_complete(echo_filter(bot, message, replies))

async def send_cmd(bot, message, replies, payload):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return

    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       t_reply = None
       if message.quote:
          t_reply = is_register_msg(message.get_sender_contact().addr, message.chat.id, message.quote.id)
       if message.filename:
          if message.filename.find('.aac')>0:
             m = await client.send_file(target, message.filename, caption = payload, voice_note=True, reply_to=t_reply)
          else:
             m = await client.send_file(target, message.filename, caption = payload, reply_to=t_reply)
       else:
          m = await client.send_message(target,payload, reply_to=t_reply)
       register_msg(message.get_sender_contact().addr, message.chat.id, message.id, m.id)
       await client.disconnect()
    except:
       await client(SendMessageRequest(target, payload))
       code = str(sys.exc_info())
       replies.add(text=code)

def async_send_cmd(bot, message, replies, payload):
    """Send command to telegram chats. Example /b /help"""
    loop.run_until_complete(send_cmd(bot, message, replies, payload))
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload='', dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))


async def inline_cmd(bot, message, replies, payload):
    example_inline = """
    /inline_gif para buscar gif animados
    /inline_vid para buscar videos en youtube
    /inline_youtube para buscar videos en youtube
    /inline_bing para buscar imagenes en bing
    /inline_pic para buscar imagenes en Yandex
    /inline_wiki para buscar informacion en Wikipedia
    /inline_sticker para buscar sticker con emojis
    /inline_ribot para buscar en Google
    """
    contacto = message.get_sender_contact().addr
    if not os.path.exists(contacto):
       os.mkdir(contacto)
    if contacto not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    if len(payload.split())>1:
       parametros = payload.split()
       inline_bot = parametros[0]
       inline_search = payload.replace(parametros[0],'',1)
    else:
       replies.add(text = 'Debe proporcionar el nombre del bot y el termino de búsqueda, ejemplo: /inline gif gaticos\nAqui hay otros ejemplos probados:\n'+example_inline)
       return
    target = get_tg_id(message.chat, bot)
    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if target:
          results = await client.inline_query(bot = inline_bot, query = inline_search, entity = target)
       else:
          results = await client.inline_query(bot = inline_bot, query = inline_search)

       limite = 0
       if len(results)<1:
          replies.add('La busqueda no arrojó ningun resultado.')
          await client.disconnect()
          return
       for r in results:
           attach = ''
           resultado = ''
           tipo = None
           if limite<10:
              if hasattr(r,'title') and r.title:
                 resultado+=str(r.title)+'\n'
              if hasattr(r,'description') and r.description:
                 resultado+=str(r.description)+'\n'
              if hasattr(r,'url') and r.url:
                 resultado+=str(r.url)+'\n'
              if hasattr(r,'message') and r.message:
                 if r.message.message:
                    resultado+=str(r.message.message)+'\n'
                 if hasattr(r.message,'entities') and r.message.entities:
                    for e in r.message.entities:
                        if hasattr(e,'url') and e.url:
                           resultado+=str(e.url)+'\n'

              if attach == '':
                 try:
                    if hasattr(r,'document') and r.document:
                       attach = await client.download_media(r.document, contacto)
                       try:
                          if attach.lower().endswith('.webp') or attach.lower().endswith('.tgs'):
                             tipo = 'sticker'
                          #if attach.lower().endswith('.tgs'):
                             #filename, file_extension = os.path.splitext(attach)
                             #attach_converted = filename+'.webp'
                             #await convertsticker(attach,attach_converted)
                             #attach = attach_converted
                             #tipo = 'sticker'
                       except:
                          print('error convirtiendo sticker')
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                       tipo = None
                 except:
                    print('Error descargando inline document result')
                 try:
                    if hasattr(r,'photo') and r.photo:
                       attach = await client.download_media(r.photo, contacto)
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                 except:
                    print('Error descargando inline photo result')
                 try:
                    if hasattr(r,'gif') and r.gif:
                       attach = await client.download_media(r.gif, contacto)
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                 except:
                    print('Error descargando inline gif result')
                 try:
                    if hasattr(r,'video') and r.video:
                       attach = await client.download_media(r.video, contacto)
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                 except:
                    print('Error descargando inline video result')
                 try:
                    if hasattr(r,'mpeg4_gif') and r.mpeg4_gif:
                       attach = await client.download_media(r.mpeg4_gif, contacto)
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                 except:
                    print('Error descargando inline mpeg4_gif result')
                 try:
                    if hasattr(r,'audio') and r.audio:
                       attach = await client.download_media(r.audio, contacto)
                       replies.add(text = resultado, filename=attach, viewtype=tipo)
                 except:
                    print('Error descargando inline audio result')
              limite +=1
           else:
              break
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       if bot.is_admin(contacto):
         replies.add(text=code)
       await client.disconnect()

def async_inline_cmd(bot, message, replies, payload):
    """Search command for inline telegram bots. Example /inline gif dogs"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))


async def search_chats(bot, message, replies, payload):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para buscar chats, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    try:
        if not os.path.exists(message.get_sender_contact().addr):
           os.mkdir(message.get_sender_contact().addr)
        client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
        await client.connect()
        all_chats = await client.get_dialogs()
        id_chats = {}
        for d in all_chats:
            id_chats[d.entity.id] = ''
        resultados = await client(functions.contacts.SearchRequest(q=payload, limit=5))
        if len(resultados.chats)<1 and len(resultados.users)<1:
           replies.add('La busqueda no arrojó ningun resultado.')
           await client.disconnect()
           return
        for rchat in resultados.chats:
            if hasattr(rchat, 'photo'):
               profile_img = await client.download_profile_photo(rchat, message.get_sender_contact().addr)
            else:
               profile_img = ''
            if rchat.id in id_chats:
               replies.add(text = 'Grupo/Canal\n\n'+str(rchat.title)+'\nCargar: /load_'+str(rchat.username), filename = profile_img)
            else:
               replies.add(text = 'Grupo/Canal\n\n'+str(rchat.title)+'\nUnirse: /join_'+str(rchat.username)+'\nVista previa: /preview_'+str(rchat.username), filename = profile_img)
        for ruser in resultados.users:
            if hasattr(ruser, 'photo'):
               profile_img = await client.download_profile_photo(ruser, message.get_sender_contact().addr)
            else:
               profile_img =''
            if ruser.id in id_chats:
               replies.add(text = 'Usuario\n\n'+str(ruser.first_name)+'\nCargar: /load_'+str(ruser.username), filename = profile_img)
            else:
               replies.add(text = 'Usuario\n\n'+str(ruser.first_name)+'\nVista previa: /preview_'+str(ruser.username), filename = profile_img)
        await client.disconnect()
    except:
        code = str(sys.exc_info())
        replies.add(text=code)

def async_search_chats(bot, message, replies, payload):
    """Make search for public telegram chats. Example: /search delta chat"""
    loop.run_until_complete(search_chats(bot, message, replies, payload))

async def join_chats(bot, message, replies, payload):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para buscar chats, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    try:
        client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
        await client.connect()
        await client.get_dialogs()
        if payload.find('/joinchat/')>0:
           invite_hash = payload.rsplit('/', 1)[-1]
           await client(ImportChatInviteRequest(invite_hash))
        else:
           uname = payload.replace('@','')
           uname = uname.replace(' ','_')
           await client(JoinChannelRequest(uname))
        await client.disconnect()
        replies.add(text='Se ha unido al chat '+payload)
    except:
        code = str(sys.exc_info())
        replies.add(text=code)

def async_join_chats(bot, message, replies, payload):
    """Join to telegram chats by username or private link. Example: /join usernamegroup
    or /join https://t.me/joinchat/invitehashtoprivatechat"""
    loop.run_until_complete(join_chats(bot = bot, message = message, replies = replies, payload = payload))
    loop.run_until_complete(updater(bot=bot, payload=payload, replies=replies, message=message))
    if message.get_sender_contact().addr in logindb:
       async_save_delta_chats(replies = replies, message = message)

async def preview_chats(bot, payload, replies, message):
    global DBXTOKEN
    try:
        if message.get_sender_contact().addr not in logindb:
           replies.add(text = 'Debe iniciar sesión para visualizar chats!')
           return
        if not os.path.exists(message.get_sender_contact().addr):
           os.mkdir(message.get_sender_contact().addr)
        contacto = message.get_sender_contact()
        uid = ''
        client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
        await client.connect()
        await client.get_dialogs()
        if message.get_sender_contact().addr not in chatdb:
           chatdb[message.get_sender_contact().addr] = {}
        if payload.find('/joinchat/')>0:
           invite_hash = payload.rsplit('/', 1)[-1]
           private = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
           if not private:
              private = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
           private_photo = ''
           private_text = ''
           if hasattr(private,'photo') and private.photo:
              private_photo = await client.download_media(private.photo,message.get_sender_contact().addr)
           if hasattr(private,'broadcast') and private.broadcast:
              private_text+='\nCanal'
           if hasattr(private,'public') and private.public:
              private_text+='\nPúblico'
           else:
              private_text+='\nPrivado'
           if hasattr(private,'title') and private.title:
              private_text+='\nTítulo: '+str(private.title)
           if hasattr(private,'participants_count') and private.participants_count:
              private_text+='\nParticipantes: ' + str(private.participants_count)
           if hasattr(private,'chat') and private.chat:
              #if hasattr(private.chat,'id') and private.chat.id:
                 #uid = private.chat.id
              if hasattr(private.chat,'username') and private.chat.username:
                 uid = private.chat.username
           if uid == '':
              replies.add(text = private_text, filename = private_photo)
              return
        else:
           uid = payload.replace('https://t.me/','')
           uid = uid.replace('@','')
           uid = uid.replace(' ','_')
        if str(uid) not in chatdb[message.get_sender_contact().addr]:
           ttitle = 'Preview of'
           replies.add(text = 'Creando chat...')
           #try input from cache first
           try:
              pchat = await client.get_input_entity(uid)
              if isinstance(pchat, types.InputPeerChannel):
                 full_pchat = await client(functions.channels.GetFullChannelRequest(channel = pchat))
                 if hasattr(full_pchat,'chats') and full_pchat.chats and len(full_pchat.chats)>0:
                    ttitle = full_pchat.chats[0].title
              elif isinstance(pchat, types.InputPeerUser):
                 full_pchat = await client(functions.users.GetFullUserRequest(id = pchat))
                 if hasattr(full_pchat,'users') and full_pchat.users:
                    ttitle = full_pchat.users[0].first_name
              elif isinstance(pchat, types.InputPeerChat):
                 print('Hemos encontrado un InputPeerChat: '+str(uid))
                 full_pchat = await client(functions.messages.GetFullChatRequest(chat_id=pchat.id))
                 if hasattr(full_pchat,'chats') and full_pchat.chats and len(full_pchat.chats)>0:
                    ttitle = full_pchat.chats[0].title
                 if hasattr(full_pchat,'user') and full_pchat.user:
                    ttitle = full_pchat.user.first_name
           except:
              print('Error obteniendo entidad '+str(uid))
              pchat = await client.get_entity(uid)
              if hasattr(pchat, 'title') and pchat.title:
                 ttitle =  str(pchat.title)
              else:
                 if hasattr(pchat, 'first_name') and pchat.first_name:
                    ttitle = str(pchat.first_name)
           if DBXTOKEN:
              titulo = str(ttitle)
           else:
              titulo = str(ttitle)+' ['+str(uid)+']'
           chat_id = bot.create_group(titulo, [contacto])
           try:
               img = await client.download_profile_photo(uid, message.get_sender_contact().addr)
               if img and os.path.exists(img):
                  chat_id.set_profile_image(img)
           except:
               print('Error al poner foto del perfil al chat:\n'+str(img))
           chatdb[message.get_sender_contact().addr][str(uid)] = str(chat_id.get_name())
           replies.add(text = 'Se ha creado una vista previa del chat '+str(ttitle))
           replies.add(text = "Cargar más mensajes\n/more_-0", chat = chat_id)
           bot.set(str(chat_id.id),str(uid))
        await client.disconnect()
    except:
        code = str(sys.exc_info())
        print(code)
        replies.add(text=code)

def async_preview_chats(bot, payload, replies, message):
    """Preview chat with out join it, using the username like: /preview username"""
    loop.run_until_complete(preview_chats(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_save_delta_chats(replies = replies, message = message)

def eval_func(bot: DeltaBot, payload, replies, message: Message):
    """eval and back result. Example: /eval 2+2"""
    try:
       code = str(eval(payload))
    except:
       code = str(sys.exc_info())
    replies.add(text=code or "echo")

def confirm_unread(bot: DeltaBot, chat_id):
    chat_messages = bot.get_chat(chat_id).get_messages()
    if len(chat_messages)<1:
       return True
    elif chat_messages[-1].get_message_info().find('\nState: Read')>0 or chat_messages[-1].get_message_info().find('\nState: Seen')>0 or chat_messages[-1].get_message_info().find('\nRead: ')>0:
       par_key = str(chat_id)+':'+str(chat_messages[-1].id)
       if par_key in unreaddb:
          print('Confirmando lectura de mensaje '+par_key)
          async_read_unread(unreaddb[par_key][0],unreaddb[par_key][1],unreaddb[par_key][2])
          del unreaddb[par_key]
          bot.set('UNREADDB',json.dumps(unreaddb))
       return True
    else:
       return False
    return False

async def auto_load(bot, message, replies):
    global autochatsdb
    global UPDATE_DELAY
    while True:
        #{contact_addr:{chat_id:chat_type}}
        try:
           for (key, value) in autochatsdb.items():
               for (inkey, invalue) in value.items():
                   #print('Autodescarga de '+str(key)+' chat '+str(inkey))
                   try:
                      if SYNC_ENABLED == 0 or len([i for i in unreaddb.keys() if i.startswith(str(inkey)+':')])<1 or confirm_unread(bot, int(inkey)):
                         await load_chat_messages(bot = bot, replies = Replies, message = message, payload='', dc_contact = key, dc_id = inkey, is_auto=True)
                      else:
                         print('\nChat con mensajes por leer: '+str(inkey))
                   except:
                      code = str(sys.exc_info())
                      print(code)
                   time.sleep(0.100)
        except:
           print('Error in autochatsdb dict')
        time.sleep(UPDATE_DELAY)

def start_updater(bot, message, replies):
    """Start scheduler updater to get telegram messages. /start"""
    is_done = True
    global auto_load_task
    global tloop
    if auto_load_task:
       if auto_load_task.done():
          is_done = True
       else:
          is_done = False
          replies.add(text='Las autodescargas ya se estan ejecutando!')
    if is_done:
       auto_load_task = asyncio.run_coroutine_threadsafe(auto_load(bot=bot, message = message, replies = replies),tloop)
       replies.add(text='Las autodescargas se han iniciado!')

def stop_updater(bot: DeltaBot, payload, replies, message: Message):
    """Stop scheduler updater to get telegram messages. /stop"""
    global auto_load_task
    if auto_load_task:
       if not auto_load_task.cancelled():
          auto_load_task.cancel()
          replies.add(text='Auto descargas cancelada!')
       else:
          replies.add(text='Las autodescargas no se estan ejecutando!')
    else:
       replies.add(text='Las autodescargas no fueron iniciadas!')

async def c_run(payload, replies, message):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ejecutar comandos!')
       return
    try:
       replies.add(text='Ejecutando...')
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       code = str(await eval(payload))
       if replies:
          replies.add(text = code)
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code or "echo")

def async_run(payload, replies, message):
    """Run command inside a async TelegramClient def. Note that all code run with await prefix, results are maybe a coorutine. Example: /exec client.get_me()"""
    loop.run_until_complete(c_run(payload, replies, message))

def bot_settings(bot: DeltaBot, payload, replies, message: Message):
    """Set or show bot settings like:
    /setting CAN_IMP 1"""
    available_settings = """<pre>
    SETTING             VALUES  HINT
    CAN_IMP             0/1     Enable/disabled impersonating (names in titles)
    SYNC_ENABLED        0/1     Enable/disabled synchronize mode (mark telegram message as read when read in deltachat)
    MAX_MSG_LOAD        1..200  Max number of message receiving when you send /more
    MAX_MSG_LOAD_AUTO   1..200  Max number of message receiving in auto at the time
    MAX_AUTO_CHATS      0...    Max number of auto chats that user can set
    MAX_SIZE_DOWN       0...    Max file size of you can down with /down (bytes)
    MIN_SIZE_DOWN       0...    Minimum file size that bot download automatically (bytes)
    WHITE_LIST          mails   mails addr separate by space like user1@example.com user2@example.com
    BLACK_LIST          mails   mails addr separate by space like user1@example.com user2@example.com
    UPDATE_DELAY        0...    Seconds to delay when get automatic chats messages (Default 16) less can cause FloodWaitError
    </pre>"""
    global CAN_IMP
    global SYNC_ENABLED
    global MAX_MSG_LOAD
    global MAX_MSG_LOAD_AUTO
    global MAX_AUTO_CHATS
    global MAX_SIZE_DOWN
    global MIN_SIZE_DOWN
    global white_list
    global black_list
    global UPDATE_DELAY
    parametros = payload.split()
    if len(parametros)<1:
       replies.add(text = 'See available settings below:', html=available_settings)
    if len(parametros)==1:
       replies.add(text=bot.get(parametros[0].upper()))
    if len(parametros)>1:
       paramtext = ""
       for w in parametros[1:]:
           paramtext = paramtext+" "+w
       paramtext = paramtext.strip()
       if paramtext.isnumeric():
          paramtext = int(paramtext)
       if parametros[0].upper()=='CAN_IMP':
          CAN_IMP = paramtext
       elif parametros[0].upper()=='SYNC_ENABLED':
          SYNC_ENABLED = paramtext
          if paramtext==1:
             bot.account.set_config("mdns_enabled","1")
       elif parametros[0].upper()=='MAX_AUTO_CHATS':
          MAX_AUTO_CHATS = paramtext
       elif parametros[0].upper()=='MAX_MSG_LOAD':
          MAX_MSG_LOAD = paramtext
       elif parametros[0].upper()=='MAX_MSG_LOAD_AUTO':
          MAX_MSG_LOAD_AUTO = paramtext
       elif parametros[0].upper()=='MAX_SIZE_DOWN':
          MAX_SIZE_DOWN = paramtext
       elif parametros[0].upper()=='MIN_SIZE_DOWN':
          MIN_SIZE_DOWN = paramtext
       elif parametros[0].upper()=='WHITE_LIST':
          white_list = paramtext.split()
       elif parametros[0].upper()=='BLACK_LIST':
          black_list = paramtext.split()
       elif parametros[0].upper()=='UPDATE_DELAY':
          UPDATE_DELAY = paramtext
       else:
          replies.add(text = 'Unknown setting!, available settings below', html = available_settings)
          return
       bot.set(parametros[0].upper(), paramtext)
       if DBXTOKEN:
          backup_db()
       replies.add(text = 'Setting '+parametros[0]+' set to '+str(paramtext)+' successfully!')

@simplebot.command(admin=True)
def stats(replies) -> None:
    """Get bot and computer state."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(os.path.expanduser("~/.simplebot/"))
    proc = psutil.Process()
    botmem = proc.memory_full_info()
    size = 0
    bot_path = os.path.expanduser("~/.simplebot/accounts/"+encode_bot_addr)
    for path, dirs, files in os.walk(bot_path):
        for f in files:
            fp = os.path.join(path, f)
            size += os.path.getsize(fp)
    replies.add(
        text="**🖥️ Computer Stats:**\n"
        f"CPU: {psutil.cpu_percent(interval=0.1)}%\n"
        f"Memory: {sizeof_fmt(mem.used)}/{sizeof_fmt(mem.total)}\n"
        f"Swap: {sizeof_fmt(swap.used)}/{sizeof_fmt(swap.total)}\n"
        f"Disk: {sizeof_fmt(disk.used)}/{sizeof_fmt(disk.total)}\n\n"
        "**🤖 Bot Stats:**\n"
        f"CPU: {proc.cpu_percent(interval=0.1)}%\n"
        f"Memory: {sizeof_fmt(botmem.rss)}\n"
        f"Swap: {sizeof_fmt(botmem.swap if 'swap' in botmem._fields else 0)}\n"
        f"Path: {sizeof_fmt(size)}\n"
        f"SimpleBot: {simplebot.__version__}\n"
        f"DeltaChat: {deltachat.__version__}\n"
        f"simplebot_tg: {version}\n"
    )

def sizeof_fmt(num: float) -> str:
    """Format size in human redable form."""
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


def start_background_loop(bridge_initialized: Event) -> None:
    global tloop
    tloop = asyncio.new_event_loop()
    bridge_initialized.set()
    tloop.run_forever()


class TestEcho:
    def test_echo(self, mocker):
        msg = mocker.get_one_reply("/echo")
        assert msg.text == "echo"

        msg = mocker.get_one_reply("/echo hello world")
        assert msg.text == "hello world"

    def test_echo_filter(self, mocker):
        text = "testing echo filter"
        msg = mocker.get_one_reply(text, filters=__name__)
        assert msg.text == text

        text = "testing echo filter in group"
        msg = mocker.get_one_reply(text, group="mockgroup", filters=__name__)
        assert msg.text == text
