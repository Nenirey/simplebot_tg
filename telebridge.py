import simplebot
from simplebot.bot import DeltaBot, Replies
from deltachat import Chat, Contact, Message
import sys
import os
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
from datetime import datetime
from threading import Event, Thread
#For telegram sticker stuff
import lottie
from lottie.importers import importers
from lottie.exporters import exporters
from lottie.utils.stripper import float_strip, heavy_strip

version = "0.1.5"
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
login_hash = os.getenv('LOGIN_HASH')


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
messagedb = {}

global chatdb
chatdb = {}

global auto_load_task
auto_load_task = None

loop = asyncio.new_event_loop()

def start_background_loop(bridge_initialized: Event) -> None:
    global tloop
    tloop = asyncio.new_event_loop()
    bridge_initialized.set()
    tloop.run_forever()

@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.account.set_config("displayname","Telegram Bridge")
    bot.account.set_avatar('telegram.jpeg')
    bot.account.set_config("mdns_enabled","0")
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
    bot.commands.register(name = "/down" ,func = async_load_chat_messages)
    bot.commands.register(name = "/c" ,func = async_click_button)
    bot.commands.register(name = "/b" ,func = async_send_cmd)
    bot.commands.register(name = "/search" ,func = async_search_chats)
    bot.commands.register(name = "/join" ,func = async_join_chats)
    bot.commands.register(name = "/preview" ,func = async_preview_chats)
    bot.commands.register(name = "/auto" ,func = async_add_auto_chats)
    bot.commands.register(name = "/inline" ,func = async_inline_cmd)
    bot.commands.register(name = "/list" ,func = list_chats)

@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    global auto_load_task
    bridge_init = Event()
    Thread(
        target=start_background_loop,
        args=(bridge_init,),
        daemon=True,
    ).start()
    bridge_init.wait()
    global auto_load_task
    auto_load_task = asyncio.run_coroutine_threadsafe(auto_load(bot=bot, message = Message, replies = Replies),tloop)

    
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
    exporter.process(an, outfilepath, quality=5, skip_frames=30, dpi=5)     
    

def list_chats(replies, message, payload):
    """Show your linked deltachat/telegram chats. Example /list"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para listar sus chats!')
       return
    if message.get_sender_contact().addr not in chatdb:
       chatdb[message.get_sender_contact().addr] = {}
    chat_list = ''
    for (key, value) in chatdb[message.get_sender_contact().addr].items():
        chat_list+='\n\n'+value+'\nDesvincular: /remove_'+key
    replies.add(text = chat_list)

async def add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    global auto_load_task
    global tloop
    alloweddb ={'deltachat2':''}
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para automatizar chats')
       return
    dchat = message.chat.get_name()

    tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
    if len(tg_ids)>0:
       id_chat=tg_ids[-1]
    else:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if id_chat.lstrip('-').isnumeric():
          target = int(id_chat)
       else:
          target = id_chat
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
            
       await client.disconnect()
    except Exception as e:
       code = str(sys.exc_info())
       print(code)
    if message.get_sender_contact().addr in chatdb:
       if is_channel or is_user or is_allowed or bot.is_admin(message.get_sender_contact()):
          messagedb[message.get_sender_contact().addr] = message.chat.id
          replies.add(text='Se ha automatizado este chat!')
       else:
          replies.add(text='Solo se permite automatizar chats privados, canales y algunos grupos permitidos por ahora')           
    else:
       replies.add('Este no es un chat de Telegram!')

    
def async_add_auto_chats(bot, replies, message):
    """Enable auto load messages in the current chat. Example: /auto"""
    loop.run_until_complete(add_auto_chats(bot, replies, message))

async def save_delta_chats(replies, message):
    """This is for save the chats deltachat/telegram in Telegram Saved message user"""
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       tf = open(message.get_sender_contact().addr+'.json', 'w')
       json.dump(chatdb[message.get_sender_contact().addr], tf)
       tf.close()
       await client.connect()
       my_id = await client(functions.users.GetFullUserRequest('me'))
       if my_id.pinned_msg_id:
          my_pin = await client.get_messages('me', ids=my_id.pinned_msg_id)
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

async def load_delta_chats(message, replies):
    """This is for load the chats deltachat/telegram from Telegram saved message user"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para cargar sus chats!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       my_id = await client(functions.users.GetFullUserRequest('me'))
       my_pin = await client.get_messages('me', ids=my_id.pinned_msg_id)
       await client.download_media(my_pin)
       if os.path.isfile(message.get_sender_contact().addr+'.json'):
          tf = open(message.get_sender_contact().addr+'.json','r')
          chatdb[message.get_sender_contact().addr]=json.load(tf)
          tf.close()
       await client.disconnect()
    except:
       print('Error loading delta chats')

def async_load_delta_chats(message, replies):
    loop.run_until_complete(load_delta_chats(message, replies))

def remove_chat(payload, replies, message):
    """Remove current chat from telegram bridge. Example: /remove
       you can pass the all parametre to remove all chats like: /remove all or a telegram chat id
    like: /remove -10023456789"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para eliminar chats!')
       return
    target = payload.replace(' ','_')
    if target == 'all':
       chatdb[message.get_sender_contact().addr].clear()
       replies.add(text = 'Se desvincularon todos sus chats de telegram.')
    if target in chatdb[message.get_sender_contact().addr]:
       c_title = chatdb[message.get_sender_contact().addr][target]
       del chatdb[message.get_sender_contact().addr][target]
       replies.add(text = 'Se desvinculó el chat delta '+c_title+' con el chat telegram '+target)
    if not payload or payload =='':
       if str(message.chat.get_name()) in chatdb[message.get_sender_contact().addr].values():
          for (key, value) in chatdb[message.get_sender_contact().addr].items():
              if value == str(message.chat.get_name()):
                 del chatdb[message.get_sender_contact().addr][key]
                 if message.get_sender_contact().addr in messagedb:
                    del messagedb[message.get_sender_contact().addr]
                 replies.add(text = 'Se desvinculó el chat delta '+str(message.chat.id)+' con el chat telegram '+key)
                 break
       else:
          replies.add(text = 'Este chat no está vinculado a telegram')
          return
    async_save_delta_chats(replies, message)


def logout_tg(payload, replies, message):
    """Logout from Telegram and delete the token session for the bot"""
    if message.get_sender_contact().addr in logindb:
       del logindb[message.get_sender_contact().addr]
       if message.get_sender_contact().addr in messagedb:
          del messagedb[message.get_sender_contact().addr]
       replies.add(text = 'Se ha cerrado la sesión en telegram, puede usar su token para iniciar en cualquier momento pero a nosotros se nos ha olvidado')
    else:
       replies.add(text = 'Actualmente no está logueado en el puente')

async def login_num(payload, replies, message):
    try:
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
       me = await clientdb[message.get_sender_contact().addr].send_code_request(parametros[0], force_sms = forzar_sms)
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
       if message.get_sender_contact().addr in phonedb and message.get_sender_contact().addr in hashdb and message.get_sender_contact().addr in clientdb:
          try:
              me = await clientdb[message.get_sender_contact().addr].sign_in(phone=phonedb[message.get_sender_contact().addr], phone_code_hash=hashdb[message.get_sender_contact().addr], code=payload)
              logindb[message.get_sender_contact().addr]=clientdb[message.get_sender_contact().addr].session.save()
              replies.add(text = 'Se ha iniciado sesiòn correctamente, su token es:\n\n'+logindb[message.get_sender_contact().addr]+'\n\nUse /token mas este token para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats.')
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
       if message.get_sender_contact().addr in phonedb and message.get_sender_contact().addr in hashdb and message.get_sender_contact().addr in clientdb and message.get_sender_contact().addr in smsdb:
          me = await clientdb[message.get_sender_contact().addr].sign_in(phone=phonedb[message.get_sender_contact().addr], password=payload)
          logindb[message.get_sender_contact().addr]=clientdb[message.get_sender_contact().addr].session.save()
          replies.add(text = 'Se ha iniciado sesiòn correctamente, su token es:\n\n'+logindb[message.get_sender_contact().addr]+'\n\nUse /token mas este token para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este.\n\nAhora puede escribir /load para cargar sus chats')
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
           replies.add(text='Se ha iniciado sesión correctamente '+str(nombre))
           logindb[message.get_sender_contact().addr] = hash
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
       ya_agregados = '' 
       replies.add(text = 'Obteniendo chats...'+filtro)
       for d in all_chats:
           if hasattr(d.entity,'username'):
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
              if ttitle.lower().find(payload.lower())>=0 or tid is payload or uname is filtro:
                 find_only = False
              else:
                 find_only = True
           if str(d.id) not in chatdb[message.get_sender_contact().addr] and not private_only and not find_only:
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
              if chats_limit<=0:
                 break
           else:
              ya_agregados += '\nYa tiene agregado: '+str(ttitle)+' /remove_'+str(d.id)   
       await client.disconnect()
       if ya_agregados!='':
          replies.add(text=ya_agregados)  
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

async def click_button(message, replies, payload):
    parametros = payload.split()
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para descargar medios!')
       return
    dchat = message.chat.get_name()

    tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
    if len(tg_ids)>0:
       id_chat=tg_ids[-1]
    else:
       replies.add(text = 'Este no es un chat de telegram!')
       return

    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if id_chat.lstrip('-').isnumeric():
          target = int(id_chat)
       else:
          target = id_chat
       tchat = await client(functions.messages.GetPeerDialogsRequest(peers=[target] ))
       all_messages = await client.get_messages(target, ids = [int(parametros[0])])
       for m in all_messages:
           await m.click(int(parametros[1]),int(parametros[2]))
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_click_button(bot, message, replies, payload):
    """Make click on a message bot button"""
    loop.run_until_complete(click_button(message = message, replies = replies, payload = payload))
    parametros = payload.split()
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=parametros[0]))

async def load_chat_messages(bot: DeltaBot, message = Message, replies = Replies, payload = None, dc_contact = None, dc_id = None):
    is_auto = False   
    if dc_contact and dc_id :
       contacto = dc_contact
       chat_id = bot.get_chat(dc_id)
       dchat = chat_id.get_name()
       is_auto = True
       myreplies = Replies(bot, logger=bot.logger)
       max_limit = 1
       is_down = False
       print(dchat)       
    else:
       contacto = message.get_sender_contact().addr
       dchat = message.chat.get_name()
       chat_id = bot.get_chat(message.chat)
       myreplies = replies
       max_limit = 5
       is_down = message.text.lower().startswith('/down')
       print(dchat)
    tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
    if len(tg_ids)>0:
       id_chat=tg_ids[-1]
    else:
       replies.add(text = 'Este no es un chat de telegram!', chat = chat_id)
       return

    if contacto not in logindb:
       replies.add(text = 'Debe iniciar sesión para cargar los mensajes!', chat = chat_id)
       return

    if not os.path.exists(contacto):
       os.mkdir(contacto)

    try:      
       client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if id_chat.lstrip('-').isnumeric():
          target = int(id_chat)
       else:
          target = id_chat
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
       if sin_leer>0 or load_history or show_id:
          all_messages.reverse()
       m_id = -0
       for m in all_messages:
           if limite<max_limit:
              mquote = ''
              mservice = ''
              file_attach = 'archivo'
              no_media = True
              html_buttons = ''
              msg_id = ''
              tipo = None
              text_message = ''  
              if m and show_id:
                 msg_id = '\n'+str(m.id)
              if m:
                 #TODO try to determine if deltalab or deltachat to use m.message (not markdown) or m.message instead
                 text_message = m.text                    
                              
              #check if message is a reply
              if m and hasattr(m,'reply_to'):
                 if hasattr(m.reply_to,'reply_to_msg_id'):
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
                       if hasattr(mensaje[0],'media') and mensaje[0].media:
                          if hasattr(mensaje[0].media,'photo'):
                             reply_text += '[FOTO]'
                       if hasattr(mensaje[0],'document') and mensaje[0].document:
                          reply_text += '[ARCHIVO]'
                       reply_text += str(mensaje[0].text)
                       if len(reply_text)>60:
                          reply_text = reply_text[0:60]+'...'
                       mquote = '>'+reply_send_by+reply_text+'\n\n'
                    
              #check if message is a system message
              if m and hasattr(m,'action') and m.action:
                 mservice = '_system message_\n'
                 #mservice += str(m.action)
                    
              #extract sender name
              if m and hasattr(m,'sender') and m.sender and hasattr(m.sender,'first_name') and m.sender.first_name:
                 first_name= m.sender.first_name
                 if m.sender.last_name:
                    last_name= m.sender.last_name
                 else:
                    last_name= ""
                 send_by = str((first_name + ' ' + last_name).strip())+":\n"
              else:
                 send_by = ""
                    
              #check if message have buttons
              if m and hasattr(m,'reply_markup') and m.reply_markup and hasattr(m.reply_markup,'rows'):
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
                        
              #check if message have document
              if m and hasattr(m,'document') and m.document:
                 if m.document.size<512000 or (is_down and m.document.size<20971520):
                    file_attach = await client.download_media(m.document, contacto)
                    #Try to convert all tgs sticker to png
                    try:
                       if file_attach.lower().endswith('.webp'):
                          tipo = "sticker" 
                       if file_attach.lower().endswith('.tgs'):
                          filename, file_extension = os.path.splitext(file_attach)
                          attach_converted = filename+'.webp'
                          await convertsticker(file_attach,attach_converted)
                          file_attach = attach_converted
                          tipo = "sticker"                            
                    except:
                       print('Error converting tgs file '+str(file_attach)) 
                    myreplies.add(text = send_by+"\n"+str(text_message)+html_buttons+msg_id, filename = file_attach, viewtype = tipo, chat = chat_id)
                 else:
                    if hasattr(m.document,'attributes') and m.document.attributes:
                       if hasattr(m.document.attributes[0],'file_name'):
                          file_attach = m.document.attributes[0].file_name
                       if hasattr(m.document.attributes[0],'title'):
                          file_attach = m.document.attributes[0].title
                    myreplies.add(text = send_by+str(text_message)+"\n"+str(file_attach)+" "+str(sizeof_fmt(m.document.size))+"\n/down_"+str(m.id)+html_buttons+msg_id, chat = chat_id)
                 no_media = False
                
              #check if message have media
              if m and hasattr(m,'media') and m.media:
                 #check if message have photo  
                 if hasattr(m.media,'photo'):
                    if m.media.photo.sizes[1].size<512000 or (is_down and m.media.photo.sizes[1].size<20971520):
                       file_attach = await client.download_media(m.media, contacto)
                       myreplies.add(text = send_by+"\n"+str(text_message)+html_buttons+msg_id, filename = file_attach, chat = chat_id)
                    else:
                       myreplies.add(text = send_by+str(text_message)+"\nFoto de "+str(sizeof_fmt(m.media.photo.sizes[1].size))+"/down_"+str(m.id)+html_buttons+msg_id, chat = chat_id)
                    no_media = False
                    
                 #check if message have media webpage  
                 if hasattr(m.media,'webpage'):
                    if m.media.webpage:
                       no_media = False
                       file_attach = await client.download_media(m.media, contacto)
                       if hasattr(m.media.webpage,'title') and m.media.webpage.title:
                          wtitle = m.media.webpage.title
                       else:
                          wtitle = ''
                       if m.message:
                          wmessage=str(text_message)+'\n'
                       else:
                          wmessage=''
                       if hasattr(m.media.webpage,'url') and m.media.webpage.url:
                          wurl = m.media.webpage.url
                       else:
                          wurl = ''
                       myreplies.add(text = send_by+str(wtitle)+"\n"+wmessage+str(wurl)+html_buttons+msg_id, filename = file_attach, chat = chat_id)
                    else:
                       no_media = True
                    
              #send only text message
              if m and no_media:
                 myreplies.add(text = mservice+mquote+send_by+str(text_message)+html_buttons+msg_id, chat = chat_id)
              if m:
                 await m.mark_read()
              if m:
                 m_id = m.id
                 print('Leyendo mensaje '+str(m_id))
              if is_auto:
                 myreplies.send_reply_messages()
                 if os.path.exists(file_attach):
                    os.remove(file_attach) 
              limite+=1
           else:
              if not load_history and not is_auto:
                 myreplies.add(text = "Tienes "+str(sin_leer-limite)+" mensajes sin leer de "+str(ttitle)+"\n/more", chat = chat_id)
              break
       if sin_leer-limite<=0 and not load_history and not is_auto:
          myreplies.add(text = "Estas al día con "+str(ttitle)+"\n/more", chat = chat_id)
       if load_history:
          myreplies.add(text = "Cargar más mensajes:\n/more_-"+str(m_id), chat = chat_id)
       await client.disconnect()
    except:
       code = str(sys.exc_info())
       myreplies.add(text=code, chat = chat_id)


def async_load_chat_messages(bot, message, replies, payload, args = None):
    """Load more messages from telegram in a chat"""
    if len(args)>1:
       dc_contact = args[0]
       dc_id = args[1]
    loop.run_until_complete(load_chat_messages(bot, message, replies, payload, dc_contact = None, dc_id = None))


@simplebot.command
def echo(payload, replies):
    """Echoes back text. Example: /echo hello world"""
    replies.add(text = payload or "echo")


async def echo_filter(message, replies):
    """Write direct in chat with T upper title to write a telegram chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login +CODIGOPAISNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    dchat = message.chat.get_name()

    tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
    if len(tg_ids)>0:
       id_chat=tg_ids[-1]
    else:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if id_chat.lstrip('-').isnumeric():
          target = int(id_chat)
       else:
          target = id_chat
       if message.filename:
          if message.is_audio() or message.filename.lower().endswith('.aac'):
             await client.send_file(target, message.filename, voice_note=True)
          else:
             if len(message.text) > 1024:
                await client.send_file(target, message.filename, caption = message.text[0:1024])    
                for x in range(1024, len(message.text), 1024):
                    await client.send_message(target, message.text[x:x+1024])
             else:       
                await client.send_file(target, message.filename, caption = message.text)
       else:
          if len(message.text) > 4096:
             for x in range(0, len(message.text), 4096): 
                 await client.send_message(target, message.text[x:x+4096])
          else:
             await client.send_message(target,message.text)
       await client.disconnect()
    except:
       await client(SendMessageRequest(target, message.text))
       code = str(sys.exc_info())
       replies.add(text=code)

@simplebot.filter
def async_echo_filter(message, replies):
    """Write direct in chat bridge to write to telegram chat"""
    loop.run_until_complete(echo_filter(message, replies))

async def send_cmd(message, replies, payload):
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes, use los comandos:\n/login SUNUMERO\no\n/token SUTOKEN para iniciar, use /help para ver la lista de comandos.')
       return
    dchat = message.chat.get_name()

    tg_ids = re.findall(r"\[([\-A-Za-z0-9_]+)\]", dchat)
    if len(tg_ids)>0:
       id_chat=tg_ids[-1]
    else:
       replies.add(text = 'Este no es un chat de telegram!')
       return
    try:
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if id_chat.lstrip('-').isnumeric():
          target = int(id_chat)
       else:
          target = id_chat
       if message.filename:
          if message.filename.find('.aac')>0:
             await client.send_file(target, message.filename, caption = payload, voice_note=True)
          else:
             await client.send_file(target, message.filename, caption = payload)
       else:
          await client.send_message(target,payload)
       await client.disconnect()
    except:
       await client(SendMessageRequest(target, payload))
       code = str(sys.exc_info())
       replies.add(text=code)

def async_send_cmd(bot, message, replies, payload):
    """Send command to telegram chats. Example /b /help"""
    loop.run_until_complete(send_cmd(message, replies, payload))
    loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=''))


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
    if contacto in chatdb and str(message.chat.get_name()) in chatdb[contacto].values():
       for (key, value) in chatdb[contacto].items():
           if value == str(message.chat.get_name()):
              if key.lstrip('-').isnumeric():
                 target = int(key)
              else:
                 target = key
              break
    else:
       target = None
    try:
       client = TC(StringSession(logindb[contacto]), api_id, api_hash)
       await client.connect()
       await client.get_dialogs()
       if target:
          results = await client.inline_query(bot = inline_bot, query = inline_search, entity = target)
       else:
          results = await client.inline_query(bot = inline_bot, query = inline_search)
       resultado = ''
       
       limite = 0
       if len(results)<1:
          replies.add('La busqueda no arrojó ningun resultado.')  
          await client.disconnect()
          return  
       for r in results:
           attach = ''
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
              try:
                 if hasattr(r,'document') and r.document:
                    attach = await client.download_media(r.document, contacto)
              except:
                 print('Error descargando inline document result')

              if attach == '':
                 try:
                    if hasattr(r,'photo') and r.photo:
                       attach = await client.download_media(r.photo, contacto)
                 except:
                    print('Error descargando inline photo result')
                 try:
                    if hasattr(r,'gif') and r.gif:
                       attach = await client.download_media(r.gif, contacto)
                 except:
                    print('Error descargando inline gif result')
                 try:
                    if hasattr(r,'video') and r.video:
                       attach = await client.download_media(r.video, contacto)
                 except:
                    print('Error descargando inline video result')
                 try:
                    if hasattr(r,'mpeg4_gif') and r.mpeg4_gif:
                       attach = await client.download_media(r.mpeg4_gif, contacto)
                 except:
                    print('Error descargando inline mpeg4_gif result')
                 try:
                    if hasattr(r,'audio') and r.audio:
                       attach = await client.download_media(r.audio, contacto)
                 except:
                    print('Error descargando inline audio result')
              try:
                 if attach.lower().endswith('.webp'):
                    tipo = 'sticker'    
                 if attach.lower().endswith('.tgs'):
                    filename, file_extension = os.path.splitext(attach)
                    attach_converted = filename+'.webp'
                    await convertsticker(attach,attach_converted)
                    attach = attach_converted
                    tipo = 'sticker'
              except:
                 print('error convirtiendo sticker')   
                           
              replies.add(text = resultado, filename=attach, viewtype=tipo)
              resultado+='\n\n'
              limite +=1
           else:
              break
       await client.disconnect()
    except:
       #await client(SendMessageRequest(target, payload))
       code = str(sys.exc_info())
       if bot.is_admin(contacto):
         replies.add(text=code)
       await client.disconnect()

def async_inline_cmd(bot, message, replies, payload):
    """Search command for inline telegram bots. Example /inline gif dogs"""
    loop.run_until_complete(inline_cmd(bot, message, replies, payload))
    #loop.run_until_complete(load_chat_messages(bot = bot, message=message, replies=replies, payload=''))


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
        if len(resultados)<1:
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
    """Join to telegram chats by username or private link. Example: /join @usernamegroup
    or /join https://t.me/joinchat/invitehashtoprivatechat"""
    loop.run_until_complete(join_chats(bot = bot, message = message, replies = replies, payload = payload))
    loop.run_until_complete(updater(bot=bot, payload=payload.replace('@',''), replies=replies, message=message))
    if message.get_sender_contact().addr in logindb:
       async_save_delta_chats(replies = replies, message = message)

async def preview_chats(bot, payload, replies, message):
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
           uid = payload.replace('@','')
           uid = uid.replace(' ','_')
        if str(uid) not in chatdb[message.get_sender_contact().addr]:
           replies.add(text = 'Creando chat...')      
           pchat = await client.get_entity(uid)
           if hasattr(pchat, 'title') and pchat.title:
              ttitle =  str(pchat.title)
           else:
              if hasattr(pchat, 'first_name') and pchat.first_name:
                 ttitle = str(pchat.first_name)
              else:
                 ttitle = 'Preview of'
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

async def auto_load(bot, message, replies):
    global messagedb
    while True:
        #print('Ejecutando auto descargas...')
        for (key, value) in messagedb.items():
            print('Autodescarga de '+str(key)+' chat '+str(value))
            try:              
               await load_chat_messages(bot = bot, replies = Replies, message = message, payload='', dc_contact = key, dc_id = value)              
            except:
               code = str(sys.exc_info())
               print(code)
        await asyncio.sleep(15)

def start_updater(bot, message, replies):
    """Start scheduler updater to get telegram messages. /start"""
    is_done = True
    global auto_load_task
    global tloop
    if auto_load_task:
       if auto_load_task.done():
          is_done = True
          replies.add(text='Las autodescargas ya se estan ejecutando!')
       else:
          is_done = False
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

def sizeof_fmt(num: float) -> str:
    """Format size in human redable form."""
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


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
