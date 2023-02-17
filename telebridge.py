import simplebot
import deltachat
from simplebot.bot import DeltaBot, Replies
from deltachat import Chat, Contact, Message
from deltachat import account_hookimpl
from typing import Optional
import sys
import os
import io
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
from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError
from telethon import helpers
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
import zipfile
import base64
import html
import markdown
import random
import string

version = "0.2.23"
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
login_hash = os.getenv('LOGIN_HASH')
admin_addr = os.getenv('ADMIN')
TGTOKEN = os.getenv('TGTOKEN')
ADDR = os.getenv('ADDR')
bot_home = expanduser("~")
MAX_BUBBLE_SIZE = 1000
MAX_BUBBLE_LINES = 38

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

global last_messagedb
#{contac_addr:{dc_id:{dc_msg:tg_msg}}}
last_messagedb = {}


global unreaddb
#{'dc_id:dc_msg':[contact,tg_id,tg_msg]}
unreaddb = {}

global autochatsdb
#{contact_addr:{dc_id:tg_id}}
autochatsdb = {}

global chatdb
chatdb = {}

global resultsdb
#{contact_addr:results}
resultsdb = {}

global prealiasdb
prealiasdb = {}

global aliasdb
aliasdb = {}

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

dark_html = """<!DOCTYPE html>
       <html>
       <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <style>
                       body {
                       font-size: 18px;
                       color: white;
                       background-color: black;}
                       a:link {
                       color: #aaaaff;}
       </style>
       </head>
       <body>"""

loop = asyncio.new_event_loop()

#start secure storage save
def save_bot_db():
    if TGTOKEN:
       async_cloud_db()
       
async def cloud_db(tfile):
    try:
       client = TC(StringSession(TGTOKEN), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       storage_msg = await client.get_messages('me', search='simplebot_tg_db\n'+ADDR)
       if storage_msg.total>0:
          await client.edit_message('me', storage_msg[-1].id, 'simplebot_tg_db\n'+ADDR+'\n'+str(datetime.now()), file=tfile)
       else:
          await client.send_message('me', 'simplebot_tg_db\n'+ADDR+'\n'+str(datetime.now()), file=tfile)
       await client.disconnect()
       os.remove('./'+tfile)
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       print(estr)
       
def async_cloud_db():
    zipfile = zipdir(bot_home+'/.simplebot/', encode_bot_addr+'.zip')
    loop.run_until_complete(cloud_db(zipfile))
    
def zipdir(dir_path,file_path):
    zf = zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_LZMA)
    for dirname, subdirs, files in os.walk(dir_path):
        if dirname.endswith('account.db-blobs'):
           continue
        zf.write(dirname)
        print(dirname)
        for filename in files:
            #if filename=='bot.db-journal':
               #continue
            print(filename)
            zf.write(os.path.join(dirname, filename))
    zf.close()
    return file_path

def savelogin(bot):
    bot.set('LOGINDB',json.dumps(logindb))
    save_bot_db()

def saveautochats(bot):
    bot.set('AUTOCHATSDB',json.dumps(autochatsdb))
    save_bot_db()
    
def savealias(bot):
    bot.set('ALIASDB',json.dumps(aliasdb))
    save_bot_db()

def fixautochats(bot):
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

def extract_text_block(block):
    text_block = ""
    if hasattr(block,'text') and block.text:
       if isinstance(block.text,types.TextBold):
          if hasattr(block,'url') and block.url:
             text_block += "<b><a href='"+block.url+"'>"+extract_text_block(block.text.text)+"</a></b>"
          else:
             text_block += "<b>"+extract_text_block(block.text.text)+"</b>"
       elif isinstance(block.text,types.TextItalic):
          if hasattr(block,'url') and block.url:
             text_block += "<i><a href='"+block.url+"'>"+extract_text_block(block.text.text)+"</a></i>"
          else:
             text_block += "<i>"+extract_text_block(block.text.text)+"</i>"
       elif isinstance(block.text,types.TextPlain):
          if hasattr(block,'url') and block.url:
             text_block += "<a href='"+block.url+"'>"+extract_text_block(block.text)+"</a>"
          else:
             text_block += extract_text_block(block.text)
       elif isinstance(block.text,types.TextUrl):
          text_block += extract_text_block(block.text)
       elif isinstance(block.text,types.TextFixed):
          text_block += "<i>"+extract_text_block(block.text)+"</i>"
       elif isinstance(block.text,types.TextAnchor):
          if hasattr(block.text, 'name'):
             text_block += "<anchor name='"+block.text.name+"'>"+extract_text_block(block.text)+"</anchor>"
          else:
             text_block += "<anchor>"+extract_text_block(block.text)+"</anchor>"
       elif isinstance(block.text,types.TextConcat):
          for tc in block.text.texts:
              text_block += extract_text_block(tc)
       elif isinstance(block.text,types.TextEmpty):
          text_block += ""
       else:
          text_block += str(block.text)
    return text_block
    
def remove_attach(filename):
    head, tail = os.path.split(filename)
    bot_attach = bot_home+'/.simplebot/accounts/'+encode_bot_addr+'/account.db-blobs/'+str(tail)
    if os.path.exists(bot_attach):
       print("Eliminando adjunto "+filename)
       os.remove(bot_attach)

class AccountPlugin:
      @account_hookimpl
      def ac_chat_modified(self, chat):
          print('Chat modificado/creado: '+chat.get_name())
          if chat.is_multiuser():
             save_bot_db()
             
      @account_hookimpl
      def ac_process_ffi_event(self, ffi_event):
          if ffi_event.name=="DC_EVENT_WEBXDC_STATUS_UPDATE":
             print(ffi_event)
          if ffi_event.name == "DC_EVENT_WARNING":
             #print('Evento warning detectado!', ffi_event)
             if ffi_event.data2 and ffi_event.data2.find("Daily user sending quota exceeded")>=0:
                print('Limite diario de mensajes alcanzado!')

          if ffi_event.name == "DC_EVENT_MSG_READ":
             msg = str(ffi_event.data1)+':'+str(ffi_event.data2)
             print(msg)
             if msg in unreaddb:
                #async_read_unread(unreaddb[msg][0], unreaddb[msg][1], unreaddb[msg][2])
                del unreaddb[msg]

@simplebot.hookimpl(tryfirst=True)
def deltabot_incoming_message(message, replies) -> Optional[bool]:
    """Check that the sender is not in the black or white list."""
    sender_addr = message.get_sender_contact().addr
    if white_list and sender_addr!=admin_addr and sender_addr not in white_list:
       if message.text.lower().startswith('/pdown') or message.text.lower().startswith('/alias'):
          return None
       print('Usuario '+str(sender_addr)+' no esta en la lista blanca')
       return True
    if black_list and sender_addr!=admin_addr and sender_addr in black_list:
       print('Usuario '+str(sender_addr)+' esta en la lista negra')
       return True
    #print(message)
    """
    if message.chat.is_multiuser():
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

"""
@simplebot.hookimpl
def deltabot_member_added(chat, contact, actor, message, replies, bot) -> None:
    if actor:
       print('Miembro '+str(contact.addr)+' agregado por '+str(actor.addr)+' chat: '+str(chat.get_name()))
    else:
       print('My self!')
"""

@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.account.add_account_plugin(AccountPlugin())
    bot.account.set_config("displayname","Telegram Bridge")
    bot.account.set_avatar("telegram.jpeg")
    #bot.account.set_config("delete_device_after","21600")
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
    bot.commands.register(name = "/pdown" ,func = async_private_down_chat_messages)
    bot.commands.register(name = "/comment" ,func = async_comment_chat_messages)
    bot.commands.register(name = "/c" ,func = async_click_button)
    bot.commands.register(name = "/b" ,func = async_send_cmd)
    bot.commands.register(name = "/search" ,func = async_search_chats)
    bot.commands.register(name = "/join" ,func = async_join_chats)
    bot.commands.register(name = "/preview" ,func = async_preview_chats)
    bot.commands.register(name = "/auto" ,func = async_add_auto_chats)
    bot.commands.register(name = "/inline" ,func = async_inline_cmd)
    bot.commands.register(name = "/inmore" ,func = async_inmore_cmd)
    bot.commands.register(name = "/inclick" ,func = async_inclick_cmd)
    bot.commands.register(name = "/indown" ,func = async_indown_cmd)
    bot.commands.register(name = "/list" ,func = list_chats)
    bot.commands.register(name = "/forward" ,func = async_forward_message)
    bot.commands.register(name = "/pin" ,func = async_pin_messages)
    bot.commands.register(name = "/news" ,func = async_chat_news)
    bot.commands.register(name = "/info" ,func = async_chat_info)
    bot.commands.register(name = "/setting" ,func = bot_settings, admin = True)
    bot.commands.register(name = "/react" ,func = async_react_button)
    bot.commands.register(name = "/link2" ,func = link_to)
    bot.commands.register(name = "/chat" ,func = create_comment_chat)
    bot.commands.register(name = "/alias" ,func = create_alias)

@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    global bot_addr
    bot_addr = bot.account.get_config('addr')
    global encode_bot_addr
    encode_bot_addr = urllib.parse.quote(bot_addr, safe='')
    global logindb
    logindb = json.loads(bot.get('LOGINDB') or '{}')
    global autochatsdb
    autochatsdb = json.loads(bot.get('AUTOCHATSDB') or '{}')
    global aliasdb
    aliasdb = json.loads(bot.get('ALIASDB') or '{}')
    #fixautochats(bot)
    for (key,_) in logindb.items():
        loop.run_until_complete(load_delta_chats(contacto=key))
        time.sleep(5)
    bridge_init = Event()
    Thread(
        target=start_background_loop,
        args=(bridge_init,),
        daemon=True,
    ).start()
    bridge_init.wait()
    global auto_load_task
    auto_load_task = asyncio.run_coroutine_threadsafe(auto_load(bot=bot, message = Message, replies = Replies),tloop)
    if admin_addr:
       bot.get_chat(admin_addr).send_text('El bot '+bot_addr+' se ha iniciado correctamente')

def create_alias(bot, replies, message, payload):
    """Configure your alias for anonimous Super Groups, 
    send /alias first in private"""
    global prealiasdb
    global aliasdb
    parametros = payload.split()
    addr = message.get_sender_contact().addr
    if len(parametros)==0 and not message.chat.is_multiuser():
       calias = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
       prealiasdb[calias] = addr
       replies.add('Envie /alias_'+calias+' en el super grupo anónimo donde esté el bot (mantenga presionado /alias... para copiarlo)')
    if len(parametros)==1:
       if parametros[0] in prealiasdb:
          aliasdb[addr]=prealiasdb[parametros[0]]
          savealias(bot)
          bot.get_chat(prealiasdb[parametros[0]]).send_text('Alias '+addr+' confirmado para '+prealiasdb[parametros[0]])
          del prealiasdb[parametros[0]]
       
def parse_entiti(r_text, s_text,offset,tlen):
    if r_text == '▚':
       h_text = helpers.add_surrogate(r_text*tlen)
    else:
       spaces = " "*tlen
       h_text = helpers.add_surrogate(r_text+spaces)
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
   
def register_last_msg(contacto, dc_id, dc_msg, tg_msg):
   global last_messagedb
   #{contac_addr:{dc_id:{dc_msg:tg_msg}}}
   if contacto not in last_messagedb:
      last_messagedb[contacto] = {}
   if dc_id not in last_messagedb[contacto]:
      last_messagedb[contacto][dc_id] = {}
   else:
      last_messagedb[contacto][dc_id].clear()
   last_messagedb[contacto][dc_id][dc_msg] = tg_msg

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
def last_register_msg(contacto, dc_id):
   if contacto in last_messagedb:
      if dc_id in last_messagedb[contacto]:
         for (_, value) in last_messagedb[contacto][dc_id].items():
             last_id = value
         return last_id
      else:
         return
   else:
      return

def get_tg_id(chat, bot):
    f_id = bot.get(str(chat.id))
    tg_ids = []
    if f_id:
       tg_ids = [f_id]
    elif not TGTOKEN:
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

def get_tg_reply(chat, bot):
    f_id = bot.get("rp2_"+str(chat.id))
    tg_ids = []
    if f_id and TGTOKEN:
       tg_ids = [f_id]
    elif not TGTOKEN:
       dchat = chat.get_name()
       tg_ids = re.findall(r"\(([0-9]+)\)", dchat)
       if len(tg_ids)>0:
          bot.set("rp2_"+str(chat.id),tg_ids[-1])
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
       if len(mensajes)>0 and mensajes[0]:
          await mensajes[0].mark_read()
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print('Error marcando mensaje como leido\n'+code)

def async_read_unread(contacto, target, tg_id):
    loop.run_until_complete(read_unread(contacto, target, tg_id))

def safe_html(hcode):
    scode = html.escape(hcode)
    return scode
    
async def chat_news(bot, payload, replies, message):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ver sus chats!')
       return
    if addr not in chatdb:
       chatdb[addr] = {}
    try:
       if not os.path.exists(addr):
          os.mkdir(addr)
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       me = await client.get_me()
       my_id = me.id
       all_chats = await client.get_dialogs(ignore_migrated = True)
       chat_list = ""
       chat_count = 0
       is_full = (payload.lower().find('full')>=0)
       is_img = (payload.lower().find('img')>=0)
       is_private = (payload.lower().find('private')>=0)
       global bot_addr
       for d in all_chats:
           if d.unread_count>0:
              no_leidos = str(d.unread_count)
              no_leidos = '<a style="color:white;background:red;border-radius:15px;padding-left:3px;padding-top:3px;padding-right:3px;padding-bottom:3px">'+no_leidos+'</a>'
           else:
              no_leidos = ''
              if not is_full:
                 continue
           if hasattr(d.entity,'username') and d.entity.username:
              uname = safe_html(str(d.entity.username))
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
              titulo = safe_html(str(ttitle))
              if my_id == d.id:
                 titulo = 'Mensajes guardados'
              if len(titulo)<1:
                 titulo = '?'
              profile_letter = '<div style="font-size:50px;color:white;background:#7777ff;border-radius:25px;width:50px;height:50px"><center>'+str(titulo[0])+'</center></div>'
              if str(d.id) in chatdb[addr]:
                 comando = '<br><a href="mailto:'+bot_addr+'?body=/remove_'+str(d.id)+'">❌ Desvilcular</a>&nbsp; &nbsp; &nbsp;<a href="mailto:?body=/link2_'+str(d.id)+'">↔️ Vincular con...</a>'
              else:
                 comando = '<br><a href="mailto:'+bot_addr+'?body=/load_'+str(d.id)+'">✅ Cargar</a>&nbsp; &nbsp; &nbsp;<a href="mailto:?body=/link2_'+str(d.id)+'">↔️ Vincular con...</a>'
              try:
                  if is_img:
                     profile_photo = '<img src="data:image/jpeg;base64,{}" alt="{}" style="width:50px;height:50px;border-radius:25px"/>'.format(base64.b64encode(await client.download_profile_photo(d.id,bytes,download_big=False)).decode(), str(titulo[0]))
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
                             send_by = '<br><b>'+safe_html(str(full_pchat.users[0].first_name))+'</b>'
                       except:
                          print('Error obteniendo entidad '+str(d.message.from_id.user_id))
                          try:
                             pchat = await client.get_entity(d.message.from_id.user_id)
                             if hasattr(pchat, 'first_name') and pchat.first_name:
                                send_by = '<br><b>'+safe_html(str(pchat.first_name))+'</b>'
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
              chat_list += '<table><tr><td>'+str(profile_photo)+'</td><td><b>'+str(titulo)+'</b>&nbsp;&nbsp;'+str(no_leidos)+str(send_by)+'<br>'+str(safe_html(last_message))+str(comando)+'</td></tr></table><hr>'
              #bubbles
              #chat_list += '<br><div style="border-radius:3px;color:white;background:#7777ff">'+profile_photo+'<b>'+titulo+'</b> <a style="color:white;background:red;border-radius:15px">'+no_leidos+'</a>'+send_by+'<br>'+last_message+comando+'</div>'
              #img = await client.download_profile_photo(d.entity, message.get_sender_contact().addr)
       chat_list += "</body></html>"
       await client.disconnect()
       replies.add(text=str(chat_count)+' chats',html=chat_list)
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       print(estr)
       replies.add(text=estr)

def async_chat_news(bot, payload, replies, message):
    """See a list of all your chats status/unread from telegram. Example: /news
    you can pass the parameter private to see only the private chat like: /news private
    you can pass the parameter full to see a full chat list like: /news full
    pass the img parameter to see the chats profile photos like: /news img"""
    loop.run_until_complete(chat_news(bot, payload, replies, message))


def link_to(bot, payload, replies, message):
    """Link chat with a Telegram chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para vincular chats!')
       return
    if not bot.is_admin(message.get_sender_contact()) and (len(message.chat.get_contacts())>2 or message.chat.is_mailinglist()):
       replies.add(text = 'Debe ser administrador para vincular un chat de mas de 2 miembros o un super grupo!')
       return
    if payload:
       tchat = payload.replace('@','')
       tchat = tchat.replace(' ','_')
       bot.set(str(message.chat.id), tchat)
       replies.add(text='Se ha asociado el chat de Telegram '+payload+' con este chat')
    else:
       bot.set(str(message.chat.id),None)
       bot.set("rp2_"+str(message.chat.id),None)
       replies.add(text='Este chat se desvinculó de Telegram!')
    save_bot_db()

async def chat_info(bot, payload, replies, message):
    f_id = get_tg_id(message.chat, bot)
    c_id = get_tg_reply(message.chat, bot)
    addr = message.get_sender_contact().addr
    if not f_id:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ver información del chat!')
       return
    if addr not in chatdb:
       chatdb[addr] = {}
    try:
       if not os.path.exists(addr):
          os.mkdir(addr)

       if f_id:
          #TODO show more chat information
          myreplies = Replies(bot, logger=bot.logger)
          client = TC(StringSession(logindb[addr]), api_id, api_hash)
          await client.connect()
          await client.get_dialogs()
          tinfo =""
          img = None
          if message.quote:
             t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
             if not t_reply:
                replies.add(text='No se encontró la referencia de este mensaje con el de Telegram', quote=message)
             else:
                if c_id:
                   mensaje = []
                   async for m in client.iter_messages(f_id, reply_to = c_id):
                         if m.id == t_reply:
                            mensaje.append(m)
                            break
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
                   myreplies.add(text=tinfo, html=mensaje[0].stringify(), filename=img, quote=message, chat=message.chat)
                   myreplies.send_reply_messages()
                   if img and img!='' and os.path.exists(img):
                      os.remove(img)
                      remove_attach(img)
                else:
                   replies.add(text="El mensaje fue eliminado?")
             await client.disconnect()
             return
          pchat = await client.get_input_entity(f_id)

          if isinstance(pchat, types.InputPeerChannel):
             full_pchat = await client(functions.channels.GetFullChannelRequest(channel = pchat))
             if hasattr(full_pchat,'chats') and full_pchat.chats and len(full_pchat.chats)>0:
                tinfo += "\nTitulo: "+full_pchat.chats[0].title
                if hasattr(full_pchat.full_chat,'participants_count') and full_pchat.full_chat.participants_count:
                   tinfo += "\nParticipantes: "+str(full_pchat.full_chat.participants_count)
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
             img = await client.download_profile_photo(f_id, addr)
          except:
             img = None
             print("Error descargando foto de perfil de "+str(f_id))
          await client.disconnect()
          myreplies.add(text=tinfo, html = "<code>"+str(full_pchat)+"</code>", filename = img, quote=message, chat=message.chat)
          myreplies.send_reply_messages()
          if img and img!='' and os.path.exists(img):
             os.remove(img)
             remove_attach(img)
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       print(estr)
       replies.add(text=estr)

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
    addr = message.get_sender_contact().addr
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
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
    addr = message.get_sender_contact().addr
    if addr not in logindb:
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
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para listar sus chats!')
       return
    if addr not in chatdb:
       chatdb[addr] = {}
    chat_list = ''
    for (key, value) in chatdb[addr].items():
        chat_list+='\n\n'+value+'\n❌ Desvincular: /remove_'+key
    replies.add(text = chat_list)

async def add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    alloweddb ={'deltachat2':''}
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para automatizar chats')
       return
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
    if addr in chatdb:
       if is_channel or is_user or is_allowed or bot.is_admin(message.get_sender_contact()):
          #{contact_addr:{chat_id:chat_type}}
          if addr not in autochatsdb:
             autochatsdb[addr]={}
          if str(message.chat.id) in autochatsdb[addr]:
             del autochatsdb[addr][str(message.chat.id)]
             replies.add(text='Se ha desactivado la automatizacion en este chat ('+str(len(autochatsdb[addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer!')
          else:
             if len(autochatsdb[addr])>=MAX_AUTO_CHATS and not bot.is_admin(message.get_sender_contact()):
                autochatsdb[addr][str(message.chat.id)]=target
                for (key,_) in autochatsdb[addr].items():
                    del autochatsdb[addr][str(key)]
                    replies.add(text='Solo se permiten automatizar hasta 5 chats, se ha automatizado este chat ('+str(len(autochatsdb[addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer y se ha desactivado la automatizacion del chat '+str(bot.get_chat(int(key)).get_name()))
                    break
             else:
                autochatsdb[message.get_sender_contact().addr][str(message.chat.id)]=target
                replies.add(text='Se ha automatizado este chat ('+str(len(autochatsdb[addr]))+' de '+str(MAX_AUTO_CHATS)+'), tiene '+str(sin_leer)+' mensajes sin leer!')
       else:
          replies.add(text='Solo se permite automatizar chats privados, canales y algunos grupos permitidos por ahora')
    else:
       replies.add(text='Este no es un chat de Telegram!')


def async_add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    loop.run_until_complete(add_auto_chats(bot, replies, message))
    saveautochats(bot)

async def save_delta_chats(replies, message):
    """This is for save the chats deltachat/telegram in Telegram Saved message user"""
    try:
       addr = message.get_sender_contact().addr
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       tf = open(addr+'.json', 'w')
       json.dump(chatdb[addr], tf)
       tf.close()
       await client.connect()
       my_id = await client(functions.users.GetFullUserRequest('me'))
       if my_id.full_user.pinned_msg_id:
          my_pin = await client.get_messages('me', ids=my_id.full_user.pinned_msg_id)
          await client.edit_message('me',my_pin,'!!!Atención, este mensaje es parte del puente con deltachat, NO lo borre ni lo quite de los anclados o perdera el vinculo con telegram\n'+str(datetime.now()), file = addr+'.json')
       else:
          my_new_pin = await client.send_file('me', addr+'.json')
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
          json_file = await client.download_media(my_pin)
          if os.path.isfile(json_file):
             tf = open(json_file,'r')
             chatdb[contacto]=json.load(tf)
             tf.close()
             os.remove(json_file)
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
    target = None
    self_target = get_tg_id(message.chat, bot)
    rpto = get_tg_reply(message.chat, bot)
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para eliminar chats!')
       return
    if not payload or payload =='':
       if not self_target:
          replies.add(text = 'Este chat no está vinculado a Telegram!')
    else:
       target = payload.replace(' ','_')
    any_target = target or self_target
    if target == 'all':
       if addr in chatdb:
          chatdb[addr].clear()
       if addr in autochatsdb:
          autochatsdb[addr].clear()
       replies.add(text = 'Se desvincularon todos sus chats de telegram.')
    else:
       if self_target and not target:
          bot.set(str(message.chat.id),None)
          if rpto:
             bot.set("rp2_"+str(message.chat.id),None)
       if str(any_target) in chatdb[addr]:
          c_title = chatdb[addr][str(any_target)]
          del chatdb[addr][str(any_target)]
          replies.add(text = 'Se desvinculó el chat delta '+str(c_title)+' con el chat telegram '+str(any_target))
       else:
          replies.add(text = 'Este chat no está vinculado a telegram')
       try:
          if addr in autochatsdb:
             for (key, value) in autochatsdb[addr].items():
                 if str(value) == str(target) or (target is None and str(key) == str(message.chat.id)):
                    del autochatsdb[addr][str(key)]
                    replies.add(text = 'Se desactivaron las actualizaciones para el chat '+bot.get_chat(int(key)).get_name())
                    break
       except:
          print('Dictionary change size...')
    async_save_delta_chats(replies, message)


def logout_tg(bot, payload, replies, message):
    """Logout from Telegram and delete the token session for the bot"""
    addr = message.get_sender_contact().addr
    if addr in logindb:
       del logindb[addr]
       if addr in clientdb:
          del clientdb[addr]
       if addr in autochatsdb:
          autochatsdb[addr].clear()
       savelogin(bot)
       replies.add(text = 'Se ha cerrado la sesión en telegram, puede usar su token para iniciar en cualquier momento pero a nosotros se nos ha olvidado')
    else:
       replies.add(text = 'Actualmente no está logueado en el puente')

async def login_num(payload, replies, message):
    try:
       if message.chat.is_multiuser():
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
       addr = message.get_sender_contact().addr
       clientdb[addr] = TC(StringSession(), api_id, api_hash)
       await clientdb[addr].connect()
       try:
          me = await clientdb[addr].send_code_request(parametros[0], force_sms = forzar_sms)
       except errors.FloodWaitError as e:
          print(e)
          replies.add(text = 'Atencion!\nHa solicitado demasiadas veces el codigo y Telegram le ha penalizado con '+str(e.seconds)+' segundos de espera para poder solicitar nuevamente el codigo!')
          return
       hashdb[addr] = me.phone_code_hash
       phonedb[addr] = parametros[0]
       replies.add(text = 'Se ha enviado un codigo de confirmacion al numero '+parametros[0]+', puede que le llegue a su cliente de Telegram o reciba una llamada, por favor introdusca /sms CODIGO para iniciar')
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text='Debe escribir el codigo del pais mas el numero (sin espacios), ejemplo /login +5355555555')

def async_login_num(payload, replies, message):
    """Start session in Telegram. Example: /login +5312345678"""
    loop.run_until_complete(login_num(payload, replies, message))

async def login_code(bot, payload, replies, message):
    try:
       if message.chat.is_multiuser():
          return
       addr = message.get_sender_contact().addr
       if addr in phonedb and addr in hashdb and addr in clientdb:
          try:
              me = await clientdb[addr].sign_in(phone=phonedb[addr], phone_code_hash=hashdb[addr], code=payload)
              logindb[addr]=clientdb[addr].session.save()
              replies.add(text = 'Se ha iniciado sesiòn correctamente, copie y pegue el mensaje del token en privado para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats.')
              replies.add(text = '/token '+logindb[addr])
              await clientdb[addr].disconnect()
              del clientdb[addr]
          except SessionPasswordNeededError:
              smsdb[addr]=payload
              replies.add(text = 'Tiene habilitada la autentificacion de doble factor, por favor introdusca /pass PASSWORD para completar el login.')
       else:
          replies.add(text = 'Debe introducir primero si numero de movil con /login NUMERO')
    except Exception as e:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_login_code(bot, payload, replies, message):
    """Confirm session in Telegram. Example: /sms 12345"""
    loop.run_until_complete(login_code(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)
       savelogin(bot)

async def login_2fa(bot, payload, replies, message):
    try:
       if message.chat.is_multiuser():
          return
       addr = message.get_sender_contact().addr
       if addr in phonedb and addr in hashdb and addr in clientdb and addr in smsdb:
          me = await clientdb[addr].sign_in(phone=phonedb[addr], password=payload)
          logindb[addr]=clientdb[addr].session.save()
          replies.add(text = 'Se ha iniciado sesiòn correctamente, copie y pegue el mensaje del token en privado para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats.')
          replies.add(text = '/token '+logindb[addr])
          await clientdb[addr].disconnect()
          del clientdb[addr]
          del smsdb[addr]
       else:
          if addr not in clientdb:
             replies.add(text = 'Debe introducir primero si numero de movil con /login NUMERO')
          else:
             if addr not in smsdb:
                replies.add(text = 'Debe introducir primero el sms que le ha sido enviado con /sms CODIGO')
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_login_2fa(bot, payload, replies, message):
    """Confirm session in Telegram with 2FA. Example: /pass PASSWORD"""
    loop.run_until_complete(login_2fa(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)
       savelogin(bot)

async def login_session(bot, payload, replies, message):
    if message.chat.is_multiuser():
       return
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       try:
           hash = payload.replace(' ','_')
           if not hash:
              replies.add('Debe proporcionar el token!')
              return
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
           logindb[addr] = hash
           replies.add(text='Se ha iniciado sesión correctamente '+str(nombre))
       except:
          code = str(sys.exc_info())
          print(code)
          replies.add(text='Error al iniciar sessión:\n'+code)
    else:
       replies.add(text='Su token es:\n\n'+logindb[addr])

def async_login_session(bot, payload, replies, message):
    """Start session using your token or show it if already login. Example: /token abigtexthashloginusingintelethonlibrary..."""
    loop.run_until_complete(login_session(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_load_delta_chats(message = message, replies = replies)
       savelogin(bot)

async def updater(bot, payload, replies, message):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para cargar sus chats!')
       return
    if addr not in chatdb:
       chatdb[addr] = {}
    try:
       if not os.path.exists(addr):
          os.mkdir(addr)
       contacto = message.get_sender_contact()
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
           if str(d.id) not in chatdb[addr] and not private_only and not find_only:
              if TGTOKEN:
                 titulo = str(ttitle)
                 if my_id == d.id:
                    titulo = 'Mensajes guardados'
              else:
                 titulo = str(ttitle)+' ['+str(d.id)+']'
                 if my_id == d.id:
                    titulo = 'Mensajes guardados ['+str(d.id)+']'
              chat_id = bot.create_group(titulo, [contacto])
              img = await client.download_profile_photo(d.entity, addr)
              try:
                 if img and os.path.exists(img):
                    chat_id.set_profile_image(img)
                    os.remove(img)
              except:
                 print('Error al poner foto del perfil al chat:\n'+str(img))
              chats_limit-=1
              chatdb[addr][str(d.id)] = str(chat_id.get_name())
              if d.unread_count == 0:
                 replies.add(text = "Estas al día con "+ttitle+" id:[`"+str(d.id)+"`]\n/more", chat = chat_id)
              else:
                 replies.add(text = "Tienes "+str(d.unread_count)+" mensajes sin leer de "+ttitle+" id:[`"+str(d.id)+"`]\n/more", chat = chat_id)
              bot.set(str(chat_id.id),str(d.id))
              if chats_limit<=0:
                 break
           else:
              if str(d.id) in chatdb[addr]:
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
    addr = message.get_sender_contact().addr
    if addr not in logindb:
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
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para reaccionar!')
       return
    if message.quote:
       t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
    elif len(parametros)>1 and parametros[0].isnumeric():
       t_reply = int(parametros[0])
    else:
       t_reply = False
    if not t_reply and len(parametros)>0:
       replies.add(text = 'No se encontro la referencia de este mensaje!')
       return
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
          await client(functions.messages.SendReactionRequest(peer=target, msg_id=t_reply, reaction=[types.ReactionEmoji( emoticon=parametros[-1] )]))
       await client.disconnect()
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       replies.add(text=estr)

def async_react_button(bot, message, replies, payload):
    """Send reaction to message repling it like: /react ❤"""
    loop.run_until_complete(react_button(bot = bot, message = message, replies = replies, payload = payload))
    addr = message.get_sender_contact().addr
    t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=str(t_reply), dc_contact = addr, dc_id = message.chat.id, is_auto = False))


async def load_chat_messages(bot: DeltaBot, message = Message, replies = Replies, payload = None, dc_contact = None, dc_id = None, is_auto = False):
    global bot_addr
    contacto = dc_contact
    chat_id = bot.get_chat(int(dc_id))
    dchat = chat_id.get_name()
    is_in_auto = False
    if is_auto:
       max_limit = MAX_MSG_LOAD_AUTO
       is_down = False
       is_comment = False
       is_pdown = False
    else:
       max_limit = MAX_MSG_LOAD
       is_down = message.text.lower().startswith('/down') 
       is_comment = message.text.lower().startswith('/comment')
       is_pdown = message.text.lower().startswith('/pdown')
    
    myreplies = Replies(bot, logger=bot.logger)
    target = get_tg_id(chat_id, bot)
    rpto = get_tg_reply(chat_id, bot)
    if is_pdown:
       addr = message.get_sender_contact().addr
       is_down = True
       if addr in aliasdb:
          chat_id = bot.get_chat(aliasdb[addr])
       else:
          chat_id = bot.get_chat(addr)
       if admin_addr in logindb:
          contacto = admin_addr
       else:
          myreplies.add("El administrador del bot debe estar logueado para las descargas privadas", chat = chat_id)
          return
        
    if contacto in autochatsdb and str(dc_id) in autochatsdb[contacto]:
       is_in_auto = True
    if not target:
       myreplies.add(text = 'Este no es un chat de telegram!', chat = chat_id)
       myreplies.send_reply_messages()
       if is_auto and is_in_auto:
          del autochatsdb[dc_contact][str(dc_id)]
       return

    if contacto not in logindb:
       myreplies.add(text = 'Debe iniciar sesión para cargar los mensajes!', chat = chat_id)
       myreplies.send_reply_messages()
       return

    if not os.path.exists(dc_contact):
       os.mkdir(dc_contact)

    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash, auto_reconnect=not is_auto, retry_delay = 16)
       await client.connect()
       all_chats = await client.get_dialogs()
       tchat = None
       for ch in all_chats:
           if "-100"+str(ch.entity.id) == str(target) or "-"+str(ch.entity.id) == str(target) or ch.entity.id == target:
              tchat = ch
           elif hasattr(ch.entity,'username') and str(ch.entity.username) == str(target):
              tchat = ch
           if tchat is not None:
              break
       #if not tchat:
          #rchat = await client(functions.messages.GetPeerDialogsRequest(peers=[target] ))
          #tchat = rchat.dialogs[0]
       #if tchat.message:
          #previous_reactions = client(functions.messages.GetUnreadReactionsRequest(peer=target, offset_id=0, add_offset=0, limit=100,  min_id=0, max_id=tchat.message.id))
       ttitle = 'Unknown'
       me = await client.get_me()
       my_id = me.id
       #extract chat title
       ttitle = tchat.title
       if rpto:
          t = await client.get_messages(target, reply_to=rpto)
       sin_leer = tchat.unread_count
       limite = 0
       load_history = False
       show_id = False
       load_unreads = False
       if payload and payload.lstrip('-').isnumeric():
          if payload.isnumeric():
             if rpto:
                all_messages = []
                async for r in client.iter_messages(target, reply_to=rpto):
                      if r.id == int(payload):
                         all_messages.append(r)
                         break
             else:
                all_messages = await client.get_messages(target, limit = 10, ids = [int(payload)])
          else:
             if rpto:
                all_messages = []
                async for r in client.iter_messages(target, reverse=True, reply_to=rpto):
                      if r.id>int(payload.lstrip('-')):
                         all_messages.append(r)
                      if len(all_messages)>max_limit:
                         break
             else:
                all_messages = await client.get_messages(target, min_id = int(payload.lstrip('-')), limit = int(payload.lstrip('-'))+10)
             load_history = True
       else:
          if payload.lower()=='last':
             show_id = True
             all_messages = await client.get_messages(target, reply_to=rpto, limit = 1)
          else:
             if rpto:
                all_messages = []
                rp_message = await client.get_messages(target, ids=[rpto])
                last_unread = rp_message[0].replies.read_max_id
                sin_leer = rp_message[0].replies.replies
                async for r in client.iter_messages(target, reverse=True, reply_to = rpto):
                      if not last_unread or r.id>last_unread:
                         all_messages.append(r)
                      else:
                         sin_leer-=1
                      if len(all_messages)>max_limit:
                         break
             else:
                last_synchro = last_register_msg(contacto, int(dc_id))
                if last_synchro:
                   all_messages = await client.get_messages(target, min_id = last_synchro, limit = max(MAX_MSG_LOAD, MAX_MSG_LOAD_AUTO))
                else:
                   all_messages = await client.get_messages(target, limit = sin_leer)
                load_unreads = True
             if payload and payload.startswith('+') and payload.lstrip('+').isnumeric() and bot.is_admin(contacto):
                max_limit = int(payload.lstrip('+'))
       #print(str(contacto)+' '+str(dchat)+': '+str(len(all_messages)))
       if (sin_leer>0 or load_history or show_id) and not rpto:
          all_messages.reverse()
       m_id = -1
       dc_msg = -1
       for m in all_messages:
           #skip self unread message
           if hasattr(m,'sender') and m.sender:
              if my_id == m.sender.id:
                 if is_auto:
                    continue
           if hasattr(m,'peer_id') and m.peer_id:
              if hasattr(m.peer_id,'user_id') and m.peer_id.user_id:
                 if my_id == m.peer_id.user_id:
                    ttitle = "Mensajes guardados"
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
              down_button = "\n⬇ /down_"+str(m.id)+"\n🔽 /pdown_"+str(m.id)+"\n⏩ /forward_"+str(m.id)+"_tg_file_link_bot\n⏩ /forward_"+str(m.id)+"_DirectLinkGeneratorbot"
              if show_id:
                 msg_id = '\n'+str(m.id)

              #TODO try to determine if deltalab or deltachat to use m.message (not markdown) or m.text (raw text) instead
              if hasattr(m,'text') and m.text:
                 text_message = str(m.text)
              else:
                 text_message = ''

              #check if message has spoiler text or custom emojis
              if hasattr(m, 'entities') and m.entities:
                 text_tmp = helpers.add_surrogate(m.raw_text)
                 for ent in reversed(m.entities):
                     if isinstance(ent, types.MessageEntitySpoiler):
                        if not html_spoiler:
                           html_spoiler = helpers.add_surrogate(m.raw_text)
                        text_tmp = parse_entiti('▚',text_tmp, ent.offset, ent.length)
                        text_message = markdown.markdown(helpers.del_surrogate(text_tmp))
                     if isinstance(ent, types.MessageEntityCustomEmoji):
                        if not html_spoiler:
                           html_spoiler = helpers.add_surrogate(m.raw_text)
                        cemoji = await client(functions.messages.GetCustomEmojiDocumentsRequest( document_id=[ent.document_id] ))
                        html_spoiler = parse_entiti('<img src="data:'+str(cemoji[0].mime_type)+';base64,{}" alt="{}" style="width:12px;height:12px"/>'.format(base64.b64encode(await client.download_media(cemoji[0],bytes)).decode(),'i'),html_spoiler,ent.offset,ent.length)
                     if html_spoiler:
                        html_spoiler = markdown.markdown(helpers.del_surrogate(html_spoiler))

              #check if message have web preview
              if hasattr(m,'web_preview') and m.web_preview and hasattr(m.web_preview,'cached_page') and m.web_preview.cached_page:
                 if hasattr(m.web_preview.cached_page,'blocks') and m.web_preview.cached_page.blocks:
                    last_html = html_spoiler
                    if not html_spoiler:
                       html_spoiler = """<style>
                       body {
                       font-size: 18px;
                       color: white;
                       background-color: black;}
                       a:link {
                       color: #aaaaff;}</style>"""
                    for block in m.web_preview.cached_page.blocks:
                        if isinstance(block, types.PageBlockCover):
                           if hasattr(block,'cover') and block.cover:
                              if hasattr(block.cover,'photo_id') and block.cover.photo_id:
                                 if hasattr(m,'media') and m.media and hasattr(m.media,'webpage') and m.media.webpage and hasattr(m.media.webpage,'photo') and m.media.webpage.photo and m.media.webpage.photo.id == block.cover.photo_id:
                                    html_spoiler += '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await client.download_media(m.media.webpage.photo,bytes)).decode(),'COVER')
                                 for cached_photo in m.web_preview.cached_page.photos:
                                     if cached_photo.id == block.cover.photo_id:
                                        html_spoiler += '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await client.download_media(cached_photo,bytes)).decode(),'COVER')
                              if hasattr(block.cover,'caption') and block.cover.caption:
                                 html_spoiler += "<br>"+extract_text_block(block.cover.caption)+""
                        elif isinstance(block, types.PageBlockTitle):
                           if hasattr(block,'text') and block.text:
                              html_spoiler += "<br><br><h1>"+str(block.text.text)+"</h1>"
                        elif isinstance(block, types.PageBlockSubtitle):
                           if hasattr(block,'text') and block.text:
                              html_spoiler += "<br><br><h2>"+str(block.text.text)+"</h2>"
                        elif isinstance(block, types.PageBlockAuthorDate):
                           if hasattr(block,'published_date') and block.published_date:
                              html_spoiler += "<br><br>"+block.published_date.strftime("%d de %B de %Y")
                           if hasattr(block,'author') and block.author:
                              autor = extract_text_block(block.author)
                              if autor!="":
                                 html_spoiler += " por "+autor
                        elif isinstance(block, types.PageBlockPhoto):
                           if hasattr(block,'photo_id') and block.photo_id:
                              for cached_photo in m.web_preview.cached_page.photos:
                                  if cached_photo.id == block.photo_id:
                                     html_spoiler += '<br><br><center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await client.download_media(cached_photo,bytes)).decode(),'PHOTO')
                        elif isinstance(block, types.PageBlockSlideshow):
                           for slide_photo in block.items:
                               if hasattr(slide_photo,'photo_id') and slide_photo.photo_id:
                                  for cached_photo in m.web_preview.cached_page.photos:
                                      if cached_photo.id == slide_photo.photo_id:
                                         html_spoiler += '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await client.download_media(cached_photo,bytes)).decode(),'SLIDE PHOTO')
                        elif isinstance(block, types.PageBlockChannel):
                           if hasattr(block.channel,'photo') and block.channel.photo:
                              try:
                                 html_spoiler += '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await client.download_media(block.channel.photo,bytes)).decode(),'PHOTO')
                              except:
                                 print("err")
                           if hasattr(block.channel,'title') and block.channel.title:
                              html_spoiler += str(block.channel.title)
                        elif isinstance(block, types.PageBlockParagraph) or isinstance(block, types.PageBlockBlockquote):
                           html_spoiler += "<br><br>"+extract_text_block(block)
                        elif isinstance(block, types.PageBlockPullquote):
                           html_spoiler += "<br><br><center>"+extract_text_block(block)+"</center>"
                        elif isinstance(block, types.PageBlockHeader):
                           html_spoiler += "<br><br><h2>"+extract_text_block(block)+"</h2>"
                        elif isinstance(block, types.PageBlockSubheader):
                           html_spoiler += "<br><br><h3>"+extract_text_block(block)+"</h3>"
                        elif isinstance(block, types.PageBlockList) or isinstance(block, types.PageBlockOrderedList):
                           if isinstance(block, types.PageBlockOrderedList):
                              start_tag_list = "<ol>"
                              end_tag_list = "</ol>"
                           else:
                              start_tag_list = "<ul>"
                              end_tag_list = "</ul>"
                           html_spoiler += "<br><br>"+start_tag_list
                           for itemlist in block.items:
                               html_spoiler += "<li>"+extract_text_block(itemlist)+"</li>"
                           html_spoiler += end_tag_list
                        elif isinstance(block, types.PageBlockTable):
                           html_spoiler += "<table border='1'>"
                           for row in block.rows:
                               html_spoiler += "<tr>"
                               for cell in row.cells:
                                   if hasattr(cell,'text') and cell.text and hasattr(cell.text,'text') and cell.text.text and isinstance(cell.text.text, types.TextImage) and hasattr(cell.text.text,"document_id"):
                                      if hasattr(cell.text.text,'w') and cell.text.text.w:
                                         img_tw = str(cell.text.text.w)
                                      else:
                                         img_tw = "100%"
                                      for cached_photo in m.web_preview.cached_page.documents:
                                          if cached_photo.id == cell.text.text.document_id:
                                             html_spoiler += '<td><center><img src="data:image/png;base64,{}" alt="{}" style="width:'.format(base64.b64encode(await client.download_media(cached_photo, bytes, thumb=-1)).decode(),'Article photo')+img_tw+'"/></center></td>'
                                   else:
                                     html_spoiler += "<td>"+extract_text_block(cell)+"</td>"
                               html_spoiler += "</tr>"
                           html_spoiler += "</table>"
                        elif isinstance(block, types.PageBlockEmbedPost):
                           for post in block.blocks:
                               html_spoiler += "<br><br>"+extract_text_block(post)
                        elif isinstance(block, types.PageBlockDetails):
                           if hasattr(block, 'title') and block.title:
                              html_spoiler += "<br><br>"+extract_text_block(block.title)
                           for detail in block.blocks:
                               if isinstance(detail, types.PageBlockList):
                                  for item in detail.items:
                                      if isinstance(item, types.PageListItemBlocks):
                                         for iblock in item.blocks:
                                             if isinstance(iblock, types.PageListItemBlocks):
                                                for iiblock in iblock.blocks:
                                                    html_spoiler += "<br><br>"+extract_text_block(iiblock)
                                                    if isinstance(iiblock, types.PageBlockList):
                                                       for liiblock in iiblock.items:
                                                           html_spoiler += "<br><br>"+extract_text_block(liiblock)
                                                    else:
                                                       html_spoiler += str(iiblock)
                                             elif isinstance(iblock, types.PageBlockList):
                                                for blockl in iblock.items:
                                                    html_spoiler += "<br><br>"+extract_text_block(blockl)
                                             elif isinstance(iblock, types.PageBlockParagraph):
                                                html_spoiler += "<br><br>"+extract_text_block(iblock)
                                             else:
                                                html_spoiler += str(iblock)
                                      elif isinstance(item, types.PageListItemText):
                                         html_spoiler += "<br><br>"+extract_text_block(item)
                                      else:
                                         html_spoiler += str(item)
                               else:
                                 html_spoiler += str(detail)
                        elif isinstance(block, types.PageBlockPreformatted):
                           html_spoiler += "<br><br>"+extract_text_block(block)
                        elif isinstance(block, types.PageBlockKicker):
                           html_spoiler += "<br><br><h3>"+extract_text_block(block)+"</h3>"
                        elif isinstance(block, types.PageBlockRelatedArticles):
                           for article in block.articles:
                               if hasattr(article,'title') and article.title:
                                  html_spoiler += "<br><br>"+article.title
                               if hasattr(article,'description') and article.description:
                                  html_spoiler += "<br>"+article.description
                        elif isinstance(block, types.PageBlockEmbed):
                           if hasattr(block,'url') and block.url:
                              html_spoiler += "<video controls><source src='"+block.url+"'></video>"
                        elif isinstance(block, types.PageBlockVideo):
                           if hasattr(block,'video_id') and block.video_id:
                              for cached_video in m.web_preview.cached_page.documents:
                                  if cached_video.id == block.video_id:
                                     html_spoiler += '<center><video controls><source type="data:video/mp4;base64,{}" alt="{}"></video></center>'.format(base64.b64encode(await client.download_media(cached_video,bytes)).decode(),'VIDEO')
                        elif isinstance(block, types.PageBlockAnchor):
                           html_spoiler += ""
                        elif isinstance(block, types.PageBlockDivider):
                           html_spoiler += "<br><hr>"
                        else:
                           html_spoiler += "<br><br>"+str(block)
                    if len(html_spoiler)<MIN_SIZE_DOWN or (is_down and len(html_spoiler)<MAX_SIZE_DOWN):
                       last_html = None
                    else:
                       text_message += "\n\nVista previa de "+sizeof_fmt(len(html_spoiler))+"\n⬇️ /down_"+str(m.id)
                       html_spoiler = last_html

              #check if message has comments
              if hasattr(m,'post') and m.post:
                 try:
                    comentarios = []
                    async for r in client.iter_messages(target, reply_to=m.id):
                          comentarios.append(r)
                    #comentarios = await client.get_messages(target, reply_to=m.id, limit = 200)
                 except:
                    comentarios = None
                 if m.replies and not is_comment:
                    comment_text = '\n\n---\n💬 '+str(m.replies.replies)+' comentarios > /comment_'+str(m.id)+' /chat_'+str(m.id)
                 if is_comment and comentarios and len(comentarios)>0:
                    comentarios.reverse()
                    if html_spoiler:
                       html_spoiler +=str(len(comentarios)) + " comentarios<hr>"
                    else:
                       html_spoiler = str(len(comentarios)) + " comentarios<hr>"
                    for coment in comentarios:
                        if isinstance(coment.from_id, types.PeerUser):
                           full = await client(GetFullUserRequest(coment.from_id))
                           from_coment = markdown.markdown(str(full.users[0].first_name))
                        else:
                           from_coment = "Unknown"
                        if coment.photo:
                           file_comment = '<center><img src="data:image/png;base64,{}" alt="{}" style="width:100%"/></center>'.format(base64.b64encode(await coment.download_media(bytes)).decode(),safe_html(coment.raw_text))
                        elif coment.media and hasattr(coment.media,'document') and coment.media.document and hasattr(coment.media.document,'thumbs') and coment.media.document.thumbs:
                           file_comment = '<center><img src="data:image/png;base64,{}" alt="{}"/></center>'.format(base64.b64encode(await coment.download_media(bytes, thumb=0)).decode(),safe_html(coment.raw_text))
                        else:
                           file_comment = (safe_html(coment.message) or '[ARCHIVO/VIDEO]').replace('\n', '<br>')
                        html_spoiler += "<br><div style='border-radius:10px;color:white;background:#7777ff;padding-left:5px;padding-top:5px;padding-right:5px;padding-bottom:5px'><b>"+from_coment+"</b><br>"+file_comment+"</div>"


              #check if message is a forward
              if m.fwd_from:
                 fwd_text = 'Mensaje reenviado\n'
                 if m.fwd_from.from_id:
                    try:
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
                    except:
                       fwd_text += "De: ?????\n"

              #check if message is a reply
              if hasattr(m,'reply_to') and m.reply_to:
                 if hasattr(m.reply_to,'reply_to_msg_id') and m.reply_to.reply_to_msg_id:
                    if hasattr(m.reply_to,'forum_topic') and m.reply_to.forum_topic:
                       ftopic = await client(functions.channels.GetForumTopicsByIDRequest(m.input_chat, [m.reply_to.reply_to_msg_id]))
                       if hasattr(ftopic.topics[0],'title'):
                          mquote = '>'+ftopic.topics[0].title+' >\n'
                    dc_mid = find_register_msg(contacto, int(dc_id), m.reply_to.reply_to_msg_id)
                    if dc_mid:
                       try:
                          quote = bot.account.get_message_by_id(dc_mid)
                       except:
                          print('Unregister dc_msg '+str(dc_mid))
                    if not quote:
                       if rpto:
                          mensaje = []
                          async for r in client.iter_messages(target, reply_to = rpto):
                                if r.id == m.reply_to.reply_to_msg_id:
                                   mensaje.append(r)
                                   break
                       else:
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
                                    reply_msg = parse_entiti('▚',reply_msg, ent.offset, ent.length)
                                    break
                          if reply_msg:
                             reply_text += reply_msg
                          if len(reply_text)>60:
                             reply_text = reply_text[0:60]+'...'
                          if hasattr(mensaje[0].reply_to,'forum_topic') and mensaje[0].reply_to.forum_topic:
                             ftopic = await client(functions.channels.GetForumTopicsByIDRequest(mensaje[0].input_chat, [mensaje[0].reply_to.reply_to_msg_id]))
                             if hasattr(ftopic.topics[0],'title'):
                                mquote += '>'+ftopic.topics[0].title+' >\n'
                          mquote += '>'+reply_send_by+reply_text.replace('\n','\n>')+'\n\n'

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
                 elif isinstance(m.action, types.MessageActionGroupCall):
                    if m.action.duration:
                       mservice += '_📞Llamada de grupo finalizada_\n'
                    else:
                       mservice += '_📞Llamada de grupo iniciada_\n'
                 elif isinstance(m.action, types.MessageActionGroupCallScheduled):
                    mservice += '_📞Llamada de grupo programada para '+str(m.action.schedule_date)+'_\n'
                 elif isinstance(m.action, types.MessageActionChatEditPhoto):
                    mservice += '_Foto del grupo/canal cambiada_\n'
                    try:
                       if len(chat_id.get_contacts())<3 or (contacto in chatdb and str(target) in chatdb[contacto]):
                          profile_photo = await client.download_profile_photo(target, contacto)
                          chat_id.set_profile_image(profile_photo)
                          os.remove(profile_photo)
                    except:
                       print('Error actualizando photo de perfil')

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

              #check if send via bot
              if hasattr(m,'via_bot_id') and m.via_bot_id:
                 full_bot = await client(functions.users.GetFullUserRequest(id = m.via_bot_id))
                 if CAN_IMP:
                    if sender_name:
                       sender_name += " via @"+str(full_bot.users[0].username)
                    else:
                       sender_name = " via @"+str(full_bot.users[0].username)
                 else:
                    if sender_name:
                       sender_name = sender_name.replace(':\n',' ')
                       sender_name += "via @"+full_bot.users[0].username+":\n"
                    else:
                       sender_name = "via @"+full_bot.users[0].username+":\n"

              #check if message have buttons
              if hasattr(m,'reply_markup') and m.reply_markup and hasattr(m.reply_markup,'rows'):
                 nrow = 0
                 html_buttons = '\n---'
                 username_bot = None
                 uri_command = 'None'
                 for row in m.reply_markup.rows:
                     html_buttons += '\n'
                     ncolumn = 0
                     for b in row.buttons:
                         if hasattr(b,'query') and b.query:
                            if not username_bot:
                               user_bot = await client(functions.users.GetFullUserRequest(id = m.peer_id.user_id))
                               username_bot = str(user_bot.users[0].username)
                            html_buttons += '[['+str(b.text)+'](mailto:'+bot_addr+'?body=/inline_'+username_bot+'_'+b.query.replace(' ','%20')+')] '
                         elif hasattr(b,'url') and b.url:
                            if not username_bot:
                               if hasattr(m.peer_id,'user_id'):
                                  user_bot = await client(functions.users.GetFullUserRequest(id = m.peer_id.user_id))
                                  username_bot = str(user_bot.users[0].username)
                                  uri_command = 'https://t.me/'+username_bot.lower()+'?start='
                            
                            if str(b.url).lower().startswith(uri_command):
                               html_buttons += '['+str(b.text)+' /b_/start_'+str(b.url).lower().replace(uri_command,"")+'] '
                            else:
                               html_buttons += '[['+str(b.text)+']('+str(b.url)+')] '
                         else:
                            html_buttons += '['+str(b.text)+' /c_'+str(m.id)+'_'+str(nrow)+'_'+str(ncolumn)+'] '
                         ncolumn += 1
                     nrow += 1

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
                        if hasattr(react,'chosen'):
                           reactions_text += "("+('•' if react.chosen else '')+react.reaction+str(react.count)+") "
                        elif hasattr(react, 'chosen_order'):
                           reactions_text += "("+('•' if react.chosen_order is not None else '')+react.reaction.emoticon+str(react.count)+") "
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
                    full_text = fwd_text+mquote+send_by+"\n"+str(text_message)+reactions_text
                    bubble_command = comment_text+html_buttons+msg_id
                    if len(full_text+bubble_command)>1000:
                       bubble_text = full_text[0:1000-len(bubble_command)-6]+" [...]"
                       html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                    else:
                       bubble_text = full_text
                    myreplies.add(text = bubble_text+bubble_command, filename = file_attach, viewtype = tipo, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                 else:
                    #print('Archivo muy grande!')
                    if hasattr(m.document,'attributes') and m.document.attributes:
                       for attr in m.document.attributes:
                           if hasattr(attr,'file_name') and attr.file_name:
                              file_title = attr.file_name
                           elif hasattr(attr,'title') and attr.title:
                              file_title = attr.title
                    if hasattr(m.document,'thumbs') and m.document.thumbs:
                       file_attach = await client.download_media(m.document, contacto, thumb=-1)
                    full_text = fwd_text+mquote+send_by+str(text_message)+"\n"
                    bubble_command = str(file_title)+" "+str(sizeof_fmt(m.document.size))+down_button+reactions_text+comment_text+html_buttons+msg_id
                    if len(full_text+bubble_command)>1000:
                       bubble_text = full_text[0:1000-len(bubble_command)-6]+" [...]"
                       html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                    else:
                       bubble_text = full_text
                    myreplies.add(text = bubble_text+bubble_command, filename = file_attach, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
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
                       full_text = fwd_text+mquote+send_by+"\n"+str(text_message)
                       bubble_command = reactions_text+comment_text+html_buttons+msg_id
                       if len(full_text+bubble_command)>1000:
                          bubble_text = full_text[0:1000-len(bubble_command)-6]+" [...]"
                          html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                       else:
                          bubble_text = full_text
                       myreplies.add(text = bubble_text+bubble_command, filename = file_attach, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                    else:
                       #print('Foto muy grande!')
                       full_text = fwd_text+mquote+send_by+str(text_message)
                       bubble_command = "\nFoto de "+str(sizeof_fmt(f_size))+down_button+reactions_text+comment_text+html_buttons+msg_id
                       if len(full_text+bubble_command)>1000:
                          bubble_text = full_text[0:1000-len(bubble_command)-6]+" [...]"
                          html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                       else:
                          bubble_text = full_text
                       myreplies.add(text = bubble_text+bubble_command, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
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
                          full_text = fwd_text+mquote+send_by+str(wtitle)+"\n"+wmessage+str(wurl)
                          bubble_command = reactions_text+comment_text+html_buttons+msg_id
                          if len(full_text+bubble_command)>1000:
                             bubble_text = full_text[0:1000-len(bubble_command)-6]+" [...]"
                             html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                          else:
                             bubble_text = full_text
                          myreplies.add(text = bubble_text+bubble_command, filename = file_attach, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                       else:
                          full_text = fwd_text+mquote+send_by+str(wtitle)+"\n"+wmessage+str(wurl)
                          bubble_command = (down_button if f_size>0 else "")+reactions_text+comment_text+html_buttons+msg_id
                          if len(full_text+bubble_command)>MAX_BUBBLE_SIZE or str(full_text+bubble_command).count('\n')>MAX_BUBBLE_LINES:
                             if len(bubble_command)>MAX_BUBBLE_SIZE or bubble_command.count('\n')>MAX_BUBBLE_LINES:
                                bubble_text = full_text[0:MAX_BUBBLE_LINES-1]+" [...]"
                                if not html_spoiler:
                                   html_spoiler = markdown.markdown(full_text+bubble_command)+(html_spoiler or "")
                             else:
                                bubble_text = full_text[0:MAX_BUBBLE_SIZE-str(bubble_command).count('\n')-1]+" [...]"
                                if not html_spoiler:
                                   html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                          else:
                             bubble_text = full_text
                          myreplies.add(text = bubble_text+bubble_command, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)
                    else:
                       no_media = True

              #send only text message
              if no_media:
                 full_text = fwd_text+mservice+mquote+send_by+str(text_message)+poll_message
                 bubble_command = reactions_text+comment_text+html_buttons+msg_id
                 if len(full_text+bubble_command)>MAX_BUBBLE_SIZE or str(full_text+bubble_command).count('\n')>MAX_BUBBLE_LINES:
                    if len(bubble_command)>MAX_BUBBLE_SIZE or bubble_command.count('\n')>MAX_BUBBLE_LINES:
                       bubble_text = full_text[0:MAX_BUBBLE_LINES-1]+" [...]"
                       if not html_spoiler:
                          html_spoiler = markdown.markdown(full_text+bubble_command)+(html_spoiler or "")
                    else:
                       bubble_text = full_text[0:MAX_BUBBLE_LINES-str(bubble_command).count('\n')-1]+" [...]"
                       if not html_spoiler:
                          html_spoiler = markdown.markdown(full_text)+(html_spoiler or "")
                 else:
                    bubble_text = full_text
                 myreplies.add(text = bubble_text+bubble_command, chat = chat_id, quote = quote, html = html_spoiler, sender = sender_name)

              #mark message as read
              m_id = m.id
              #print('Leyendo mensaje '+str(m_id))
              dc_msg = myreplies.send_reply_messages()[0].id
              if rpto:
                await client(functions.messages.ReadDiscussionRequest(t[0].chat, m.id, m.id))
              else:
                await m.mark_read()
              limite+=1
              register_msg(contacto, int(dc_id), int(dc_msg), int(m_id))
              if load_unreads:
                 register_last_msg(contacto, int(dc_id), int(dc_msg), int(m_id))
              if file_attach!='' and os.path.exists(file_attach):
                 os.remove(file_attach)
                 remove_attach(file_attach)
           else:
              if not load_history and not is_auto and not is_in_auto and not is_pdown:
                 myreplies.add(text = "Tienes "+str(sin_leer-limite)+" mensajes sin leer de "+str(ttitle)+"\n➕ /more", chat = chat_id)
              break
       if SYNC_ENABLED and is_auto:
          #{'dc_id:dc_msg':[contact,tg_id,tg_msg]}
          if m_id>-1 and dc_msg>-1:
             unreaddb[str(dc_id)+':'+str(dc_msg)]=[contacto,target,m_id]
             #bot.set('UNREADDB',json.dumps(unreaddb))
       if sin_leer-limite<=0 and not load_history and not is_auto and not is_in_auto and not is_pdown:
          myreplies.add(text = "Estas al día con "+str(ttitle)+"\n➕ /more", chat = chat_id)

       if load_history and not is_pdown:
          myreplies.add(text = "Cargar más mensajes:\n➕ /more_-"+str(m_id), chat = chat_id)
       myreplies.send_reply_messages()
       if TGTOKEN:
          if dchat!=str(ttitle) and len(chat_id.get_contacts())<3 and not rpto:
             print('Actualizando nombre de chat...')
             chat_id.set_name(str(ttitle))
       await client.disconnect()
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       print(estr)
       if isinstance(e, AuthKeyDuplicatedError):
          print('Eliminando sesión inválida...')
          myreplies.add(text='⚠️ Su token ha sido invalidado, debe iniciar sesión nuevamente.', chat = chat_id)
          myreplies.send_reply_messages()
          del logindb[contacto]
       if not is_auto:
          myreplies.add(text=estr, chat = chat_id)
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
    
def async_private_down_chat_messages(bot, message, replies, payload):
    """Download messages files from telegram to private chat
    using an existing admin login account,
    you can add specific message id to download one message
    or with - sign download messages from this id number. Examples:
    Download message #5: /pdown 5
    Download message from #10: /pdown -10
    Download last message in the chat: /pdown last"""
    loop.run_until_complete(load_chat_messages(bot=bot, message=message, replies=Replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))

def async_comment_chat_messages(bot, message, replies, payload):
    """Show comments messages from telegram in a channel post or make a direct comment,
    you can add specific message id to show comment one message
    or with - sign show comment messages from this id number. Examples:
    show comments message #5: /comment 5
    show comments messages from #10: /comment -10
    show last comments message in the chat: /comment last
    make direct comment: /comment 5 nice bike"""
    if len(payload.split())<=1:
      loop.run_until_complete(load_chat_messages(bot=bot, message=message, replies=Replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = message.chat.id, is_auto = False))
    else:
      loop.run_until_complete(direct_comment(bot=bot, message=message, replies=Replies, payload=payload))
      

async def direct_comment(bot, message, replies, payload):
    """Write direct in chat to write a telegram chat"""
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar comentarios, use los comandos:\n/login +CODIGOPAISNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    c_id = get_tg_reply(message.chat, bot)
    target = get_tg_id(message.chat, bot)
    parametros = payload.split()
    comentario = payload.replace(parametros[0],'',1)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       await client.send_message(target, comentario, comment_to = int(parametros[0]))
       await client.disconnect()
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       replies.add(text=estr)

async def echo_filter(bot, message, replies):
    """Write direct in chat to write a telegram chat"""
    if message.is_system_message():
       return
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       if message.chat.is_mailinglist() or len(message.chat.get_contacts())>2:
          return
       else:
          replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login +CODIGOPAISNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
          return
    c_id = get_tg_reply(message.chat, bot)
    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       all_chats = await client.get_dialogs()
       tchat = None
       #prevent ghost mode
       if not c_id:
         for chat in all_chats:
           if "-100"+str(chat.entity.id) == str(target) or chat.entity.id==target:
              tchat = chat
           elif hasattr(chat.entity,'username') and chat.entity.username == target:
              tchat = chat
           if tchat is not None:
              break
           #else:
             #rchat = await client(functions.messages.GetPeerDialogsRequest(peers=[target] ))
             #tchat = rchat.dialogs[0]
         sin_leer = tchat.unread_count
         await client.send_read_acknowledge(target)
       else:
         sin_leer = 0
       mquote = ''
       t_reply = None
       t_comment = c_id
       if message.quote: 
          t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
          if t_reply:
             t_message = await client.get_messages(target,ids=[t_reply])
             if t_message and hasattr(t_message[0],'post') and t_message[0].post:
                print('escribiendo en Canal...')
                if not c_id:
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
             file = io.BytesIO(open(message.filename, 'rb').read())
             file.name = "dummy.ogg"
             waveform = utils.encode_waveform(file.getvalue())
             #duration = (utils._get_metadata(file).get('duration').seconds)
             m = await client.send_file(target, file, voice_note=True, attributes=[types.DocumentAttributeAudio(duration=-1, voice=True, waveform=waveform)], reply_to = t_reply, comment_to = t_comment)
             register_msg(addr, message.chat.id, message.id, m.id)
          else:
             if len(mtext) > 1024:
                 m = await client.send_file(target, message.filename, caption = mtext[0:1024], reply_to = t_reply, comment_to = t_comment)
                 register_msg(addr, message.chat.id, message.id, m.id)
                 for x in range(1024, len(mtext), 1024):
                     m = await client.send_message(target, mtext[x:x+1024])
                     register_msg(addr, message.chat.id, message.id, m.id)
             else:
                if c_id and t_reply:
                   entity, comment_to = await client._get_comment_data(target, c_id)
                   m = await client(functions.messages.SendMediaRequest(peer=entity, media=types.InputMediaUploadedDocument(file=client.upload_file(message.filename)), caption=mtext, reply_to_msg_id=t_reply))
                else:
                   m = await client.send_file(target, message.filename, caption = mtext, reply_to = t_reply, comment_to = t_comment)
                   register_msg(addr, message.chat.id, message.id, m.id)
             remove_attach(message.filename)
       else:
          if len(mtext) > 4096:
             for x in range(0, len(mtext), 4096):
                 m = await client.send_message(target, mtext[x:x+4096], reply_to = t_reply, comment_to = t_comment)
                 register_msg(addr, message.chat.id, message.id, m.id)
          else:
             if c_id and t_reply:
                entity, comment_to = await client._get_comment_data(target, c_id)
                m = await client(functions.messages.SendMessageRequest(entity, message=mtext, reply_to_msg_id=t_reply))
             else:
                m = await client.send_message(target, mtext, reply_to = t_reply, comment_to = t_comment)
                register_msg(addr, message.chat.id, message.id, m.id)
       await client.disconnect()
    except Exception as e:
       estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
       replies.add(text=estr)
       """
       try:
          await client(SendMessageRequest(target, mtext))
       except Exception as e:
          estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
          replies.add(text=estr)
          await client.disconnect()
      """

@simplebot.filter
def async_echo_filter(bot, message, replies):
    """Write direct in chat bridge to write to telegram chat"""
    loop.run_until_complete(echo_filter(bot, message, replies))

async def send_cmd(bot, message, replies, payload):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar comandos, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return

    target = get_tg_id(message.chat, bot)
    if not target:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       t_reply = None
       m = None
       tinfo = 'Comandos disponibles:'
       if message.quote:
          t_reply = is_register_msg(addr, message.chat.id, message.quote.id)
       if message.filename:
          if message.filename.find('.aac')>0:
             m = await client.send_file(target, message.filename, caption = payload, voice_note=True, reply_to=t_reply)
          else:
             m = await client.send_file(target, message.filename, caption = payload, reply_to=t_reply)
          remove_attach(message.filename)
       else:
          if payload:
             m = await client.send_message(target,payload, reply_to=t_reply)
          else:
             pchat = await client.get_input_entity(target)
             if isinstance(pchat, types.InputPeerChannel):
                full_pchat = await client(functions.channels.GetFullChannelRequest(channel = pchat))
                if hasattr(full_pchat.full_chat,'bot_info') and full_pchat.full_chat.bot_info:
                   print('Obteniando commandos de grupo/canal...')
                   for binfo in full_pchat.full_chat.bot_info:
                       tinfo += "\n"+str(binfo.description)+"\n\n"
                       if hasattr(binfo,'commands') and binfo.commands:
                          for cmd in binfo.commands:
                              tinfo += "\n/b_/"+str(cmd.command)+" "+str(cmd.description)
             elif isinstance(pchat, types.InputPeerUser) or isinstance(pchat, types.InputPeerSelf):
                  full_pchat = await client(functions.users.GetFullUserRequest(id = pchat))
                  if hasattr(full_pchat.full_user,'bot_info') and full_pchat.full_user.bot_info:
                     print('Obteniando commandos de usuario/bot...')
                     if hasattr(full_pchat.full_user.bot_info,'commands') and full_pchat.full_user.bot_info.commands:
                        for cmd in full_pchat.full_user.bot_info.commands:
                            tinfo += "\n/b_/"+str(cmd.command)+" "+str(cmd.description)
             elif isinstance(pchat, types.InputPeerChat):
                  print('Hemos encontrado un InputPeerChat: '+str(f_id))
                  full_pchat = await client(functions.messages.GetFullChatRequest(chat_id=pchat.id))
                  if hasattr(full_pchat.full_chat,'bot_info') and full_pchat.full_chat.bot_info and len(full_pchat.full_chat.bot_info)>0:
                     print('Obteniando commandos de chat...')
                     if hasattr(full_pchat.full_chat.bot_info[0],'commands') and full_pchat.full_chat.bot_info[0].commands:
                        for cmd in full_pchat.full_chat.bot_info[0].commands:
                            tinfo += "\n/b_/"+str(cmd.command)+" "+str(cmd.description)
             replies.add(text=tinfo)
       if m:
          register_msg(addr, message.chat.id, message.id, m.id)
       await client.disconnect()
    except Exception as e:
        estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
        replies.add(text=estr)
        #await client(SendMessageRequest(target, payload))

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
    is_down = message.text.lower().startswith('/indown')
    is_more = message.text.lower().startswith('/inmore')
    is_click = message.text.lower().startswith('/inclick')
    contacto = message.get_sender_contact().addr
    if not os.path.exists(contacto):
       os.mkdir(contacto)
    if contacto not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    if len(payload.split())>1 or is_more or is_click or is_down:
       parametros = payload.split()
       inline_bot = parametros[0].replace('@','')
       inline_search = payload.replace(inline_bot,'',1)
    else:
       replies.add(text = 'Debe proporcionar el nombre del bot y el termino de búsqueda, ejemplo: /inline gif gaticos\nAqui hay otros ejemplos probados:\n'+example_inline)
       return
    target = get_tg_id(message.chat, bot)
    try:
       if contacto not in clientdb:
          clientdb[contacto] = TC(StringSession(logindb[contacto]), api_id, api_hash)
       #client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await clientdb[contacto].connect()
       await clientdb[contacto].get_dialogs()
       offset = 0
       if is_click:
          if contacto in resultsdb:
             results = []
             mensa = await resultsdb[contacto][int(parametros[0])].click()
             await load_chat_messages(bot = bot, message=message, replies=replies, payload=str(mensa.id), dc_contact = contacto, dc_id = message.chat.id, is_auto = False)
             return
          else:
             replies.add('Debe realizar la consulta para poderla enviar')
             return
             #await client(functions.messages.SendInlineBotResultRequest(peer=target, query_id=resultsdb[contacto][int(parametros[0])].query_id, id=resultsdb[contacto][int(parametros[0])].result.id))
       elif is_more:
          offset = int(parametros[0])
          if contacto in resultsdb:
             results = resultsdb[contacto][offset::]
          else:
             replies.add('Debe realizar la consulta para poder cargar mas')
             return
       elif is_down:
          offset = int(parametros[0])
          if contacto in resultsdb:
             results = []
             results.append(resultsdb[contacto][offset])
          else:
             replies.add('Debe realizar la consulta para poder descargar')
             return
       else:
          if target:
             results = await clientdb[contacto].inline_query(bot = inline_bot, query = inline_search, entity = target)
          else:
             results = await clientdb[contacto].inline_query(bot = inline_bot, query = inline_search)
          resultsdb[contacto] = results

       limite = 0
       if len(results)<1 and not is_click and not is_more:
          replies.add('La busqueda no arrojó ningun resultado.')
          #await client.disconnect()
          return
       myreplies = Replies(bot, logger=bot.logger)
       for r in results:
           attach = ''
           resultado = ''
           html_buttons = ''
           tipo = None
           if limite<MAX_MSG_LOAD:
              if hasattr(r,'title') and r.title:
                 resultado+=str(r.title)+'\n'
              if hasattr(r,'description') and r.description:
                 resultado+=str(r.description)+'\n'
              if hasattr(r,'url') and r.url:
                 resultado+=str(r.url)+'\n'
              if hasattr(r.result,'send_message') and r.result.send_message:
                 if hasattr(r.result.send_message,'message') and r.result.send_message.message:
                    #resultado+=str(r.result.send_message.message)+'\n'
                    #check if message have buttons
                    if hasattr(r.result.send_message,'reply_markup') and r.result.send_message.reply_markup and hasattr(r.result.send_message.reply_markup,'rows'):
                       nrow = 0
                       html_buttons = '\n\n---\n'
                       for row in r.result.send_message.reply_markup.rows:
                           html_buttons += '\n'
                           ncolumn = 0
                           for b in row.buttons:
                               if hasattr(b,'url') and b.url:
                                  uri_command = 'https://t.me/'+inline_bot.lower()+'?start='
                                  if str(b.url).lower().startswith(uri_command):
                                     html_buttons += '['+str(b.text)+' /b_/start_'+str(b.url).lower().replace(uri_command,"")+'] '
                                  else:
                                     html_buttons += '[['+str(b.text)+']('+str(b.url)+')] '
                               else:
                                  html_buttons += '['+str(b.text)+'] '
                               ncolumn += 1
                           html_buttons += '\n'
                           nrow += 1
                    myreplies.add(text = resultado+html_buttons+'\n\n/inclick_'+str(limite+offset), chat=message.chat)
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
                       print('Descargando documento...')
                       if r.document.size<MIN_SIZE_DOWN or (is_down and r.document.size<MAX_SIZE_DOWN):
                          attach = await clientdb[contacto].download_media(r.document, contacto)
                       else:
                          if hasattr(r.document,'attributes') and r.document.attributes:
                             for attr in r.document.attributes:
                                 if hasattr(attr,'file_name') and attr.file_name:
                                    resultado += attr.file_name
                                 elif hasattr(attr,'title') and attr.title:
                                    resultado += attr.title
                          resultado += " "+str(sizeof_fmt(r.document.size))+"\n\n⬇ /indown_"+str(limite+offset)
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
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                       tipo = None
                 except:
                    print('Error descargando inline document result')
                 try:
                    if hasattr(r,'photo') and r.photo:
                       print('Descargando photo...')
                       f_size = 0
                       if hasattr(r.photo,'sizes') and r.photo.sizes and len(r.photo.sizes)>0:
                          for sz in r.photo.sizes:
                              if hasattr(sz,'size') and sz.size:
                                 f_size = sz.size
                                 break
                       if f_size<MIN_SIZE_DOWN or (is_down and f_size<MAX_SIZE_DOWN):
                          attach = await clientdb[contacto].download_media(r.photo, contacto)
                       else:
                          resultado += "Foto de "+str(sizeof_fmt(f_size))+"\n\n⬇ /indown_"+str(limite+offset)
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                 except:
                    print('Error descargando inline photo result')
                 try:
                    if hasattr(r,'gif') and r.gif:
                       print('Descargando gif...')
                       attach = await clientdb[contacto].download_media(r.gif, contacto)
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                 except:
                    print('Error descargando inline gif result')
                 try:
                    if hasattr(r,'video') and r.video:
                       print('Descargando video...')
                       attach = await clientdb[contacto].download_media(r.video, contacto)
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                 except:
                    print('Error descargando inline video result')
                 try:
                    if hasattr(r,'mpeg4_gif') and r.mpeg4_gif:
                       print('Descargando mpeg4_gif...')
                       attach = await clientdb[contacto].download_media(r.mpeg4_gif, contacto)
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                 except:
                    print('Error descargando inline mpeg4_gif result')
                 try:
                    if hasattr(r,'audio') and r.audio:
                       print('Descargando audio...')
                       attach = await clientdb[contacto].download_media(r.audio, contacto)
                       myreplies.add(text = resultado, filename=attach, viewtype=tipo, chat=message.chat)
                 except:
                    print('Error descargando inline audio result')
                 myreplies.send_reply_messages()
                 if attach!='' and os.path.exists(attach):
                    os.remove(attach)
                    remove_attach(attach)
              limite +=1
           else:
              break
       if not is_down:
          if limite+offset<len(resultsdb[contacto]):
             replies.add(text='Cargar mas resultados '+str(limite+offset)+' de '+str(len(resultsdb[contacto]))+':\n/inmore_'+str(limite+offset))
          else:
             replies.add(text='Fin de la consulta.')
       #await client.disconnect()
    except:
       code = str(sys.exc_info())
       if bot.is_admin(contacto):
         replies.add(text=code)
       #await client.disconnect()

def async_inline_cmd(bot, message, replies, payload):
    """Search command for inline telegram bots. Example /inline gif dogs"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))

def async_inmore_cmd(bot, message, replies, payload):
    """Load more results from last inline telegram bot request. Example /inmore 5"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))

def async_indown_cmd(bot, message, replies, payload):
    """Download result from inline telegram bot request. Example /indown 5"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))

def async_inclick_cmd(bot, message, replies, payload):
    """Execute action click result from inline telegram bot request, this normaly
    send the result to the current chat. Example /inclick 5"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))

async def search_chats(bot, message, replies, payload):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para buscar chats, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    try:
        if not os.path.exists(addr):
           os.mkdir(addr)
        client = TC(StringSession(logindb[addr]), api_id, api_hash)
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
        myreplies = Replies(bot, logger=bot.logger)
        for rchat in resultados.chats:
            if hasattr(rchat, 'photo'):
               profile_img = await client.download_profile_photo(rchat, addr)
            else:
               profile_img = ''
            if rchat.id in id_chats:
               myreplies.add(text = 'Grupo/Canal\n\n'+str(rchat.title)+'\nCargar: /load_'+str(rchat.username), filename = profile_img, chat=message.chat)
            else:
               myreplies.add(text = 'Grupo/Canal\n\n'+str(rchat.title)+'\nUnirse: /join_'+str(rchat.username)+'\nVista previa: /preview_'+str(rchat.username), filename = profile_img, chat=message.chat)
        for ruser in resultados.users:
            if hasattr(ruser, 'photo') and ruser.photo:
               profile_img = await client.download_profile_photo(ruser, addr)
            else:
               profile_img =''
            if ruser.id in id_chats:
               myreplies.add(text = 'Usuario\n\n'+str(ruser.first_name)+'\nCargar: /load_'+str(ruser.username), filename = profile_img, chat=message.chat)
            else:
               myreplies.add(text = 'Usuario\n\n'+str(ruser.first_name)+'\nVista previa: /preview_'+str(ruser.username), filename = profile_img, chat=message.chat)
        myreplies.send_reply_messages()
        if profile_img!='' and os.path.exists(profile_img):
           os.remove(profile_img)
           remove_attach(profile_img)
        await client.disconnect()
    except Exception as e:
        estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
        replies.add(text=estr)

def async_search_chats(bot, message, replies, payload):
    """Make search for public telegram chats. Example: /search delta chat"""
    loop.run_until_complete(search_chats(bot, message, replies, payload))

async def join_chats(bot, message, replies, payload):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para buscar chats, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    try:
        client = TC(StringSession(logindb[addr]), api_id, api_hash)
        await client.connect()
        await client.get_dialogs()
        if payload.lower().find('/joinchat/')>0 or payload.lower().find('https://t.me/+')>=0:
           invite_hash = payload.rsplit('/', 1)[-1]
           invite_hash = invite_hash.replace('+', '')
           invite_result = await client(ImportChatInviteRequest(invite_hash))
           replies.add(text=invite_result.stringify())
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
    addr = message.get_sender_contact().addr
    try:
        if addr not in logindb:
           replies.add(text = 'Debe iniciar sesión para visualizar chats!')
           return
        if not os.path.exists(addr):
           os.mkdir(addr)
        contacto = message.get_sender_contact()
        uid = ''
        client = TC(StringSession(logindb[addr]), api_id, api_hash)
        await client.connect()
        await client.get_dialogs()
        if addr not in chatdb:
           chatdb[addr] = {}
        if payload.lower().find('/joinchat/')>0 or payload.lower().find('https://t.me/+')>=0:
           invite_hash = payload.rsplit('/', 1)[-1]
           invite_hash = invite_hash.replace('+','')
           private = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
           if not private:
              private = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
           private_photo = ''
           private_text = ''
           if hasattr(private,'photo') and private.photo:
              private_photo = await client.download_media(private.photo, addr)
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
        if str(uid) not in chatdb[addr]:
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
           if TGTOKEN:
              titulo = str(ttitle)
           else:
              titulo = str(ttitle)+' ['+str(uid)+']'
           chat_id = bot.create_group(titulo, [contacto])
           try:
               img = await client.download_profile_photo(uid, addr)
               if img and os.path.exists(img):
                  chat_id.set_profile_image(img)
                  os.remove(img)
           except:
               print('Error al poner foto del perfil al chat:\n'+str(img))
           chatdb[addr][str(uid)] = str(chat_id.get_name())
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
    
def create_comment_chat(bot, message, replies, payload):
    """Create a comment chat for post messages like /chat 1234"""
    target = get_tg_id(message.chat, bot)
    if TGTOKEN:
       tmp_name = message.chat.get_name()
    else:
       tmp_name = message.chat.get_name()+' ['+str(target)+']'
    chat_id = bot.create_group(tmp_name, [message.get_sender_contact()])
    bot.set(str(chat_id.id),str(target))
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=payload, dc_contact = message.get_sender_contact().addr, dc_id = chat_id.id, is_auto = True))
    replies.add(text = "Cargar más comentarios\n/more", chat = chat_id)
    bot.set("rp2_"+str(chat_id.id), payload)
    if TGTOKEN:
       chat_name ='💬 '+message.chat.get_name()
    else:
       chat_name ='💬 '+message.chat.get_name()+' ['+str(target)+']('+payload+')'
    chat_id.set_name(chat_name)
    replies.add(text='Chat de comentarios creado!')

def confirm_unread(bot: DeltaBot, chat_id):
    dchat = bot.get_chat(chat_id)
    if dchat.is_mailinglist():
       return True
    chat_messages = dchat.get_messages()
    if len(chat_messages)<1:
       return True
    elif chat_messages[-1].get_message_info().find('\nState: Read')>0 or chat_messages[-1].get_message_info().find('\nState: Seen')>0 or chat_messages[-1].get_message_info().find('\nRead: ')>0:
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
           autochats = copy.deepcopy(autochatsdb)
           for (key, value) in autochats.items():
               for (inkey, invalue) in value.items():
                   print('Autodescarga de '+str(key)+' chat '+str(inkey))
                   try:
                      if SYNC_ENABLED == 0 or len([i for i in unreaddb.keys() if i.startswith(str(inkey)+':')])<1:
                         if key in logindb:
                            await load_chat_messages(bot = bot, replies = Replies, message = message, payload='', dc_contact = key, dc_id = inkey, is_auto=True)
                      elif confirm_unread(bot, int(inkey)):
                         for key, _ in unreaddb.items():
                             if key.startswith(str(inkey)+':'):
                                print('Confirmando lectura de mensaje '+key)
                                #await read_unread(unreaddb[key][0],unreaddb[key][1],unreaddb[key][2])
                                del unreaddb[key]
                                break
                      elif bot.get_chat(int(inkey)) and len(bot.get_chat(int(inkey)).get_contacts())<3 and bot.get_chat(int(inkey)).get_messages()[-1].get_message_info().find('rejected: Mailbox is full')>0:
                         print('Bandeja llena...')
                         del unreaddb[key]
                      else:
                         print('\nMensajes por leer en: '+bot.get_chat(int(inkey)).get_name()+' ['+str(inkey)+']')
                   except Exception as e:
                      estr = str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+'\n'+str(type(e).__name__)+'\n'+str(e))
                      print(estr)
                      print("Eliminando chat invalido "+str(autochatsdb[key][inkey]))
                      del autochatsdb[key][inkey]
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

async def c_run(bot, payload, replies, message):
    addr = message.get_sender_contact().addr
    if addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para ejecutar comandos!')
       return
    try:
       replies.add(text='Ejecutando...')
       client = TC(StringSession(logindb[addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       lines = payload.split('\n')
       result = await eval(lines[0])
       code = str(eval("result"+lines[1]))
       if replies:
          replies.add(text = code)
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code or "echo")

def async_run(bot, payload, replies, message):
    """Run command inside a async TelegramClient def. Note that all code run with await prefix, results are maybe a coorutine. Example: /exec client.get_me()"""
    loop.run_until_complete(c_run(bot, payload, replies, message))

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
       save_bot_db()
       replies.add(text = 'Setting '+parametros[0]+' set to '+str(paramtext)+' successfully!')

@simplebot.command(admin=True)
def stats(bot, replies) -> None:
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
        f"Telethon: {TC.__version__}\n"
        f"simplebot_tg: {version}\n",
        html=bot.account.get_connectivity_html()
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
