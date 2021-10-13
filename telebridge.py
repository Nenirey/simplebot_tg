import simplebot
from simplebot.bot import DeltaBot, Replies
from deltachat import Chat, Contact, Message
import sys
import os
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon import TelegramClient as TC
#from telethon.events import StopPropagation
from telethon.sync import functions
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.types import InputPeerEmpty
from telethon.tl.types import PeerUser
from telethon import utils, errors
from telethon.errors import SessionPasswordNeededError
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import re
import time
import json
from datetime import datetime

version = "0.1.3"
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

global chatdb
chatdb = {}

loop = asyncio.new_event_loop()

@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.commands.register(name = "/eval" ,func = eval_func, admin = True)
    bot.commands.register(name = "/start" ,func = start_updater, admin = True)
    bot.commands.register(name = "/more" ,func = load_chat_messages)
    bot.commands.register(name = "/load" ,func = async_updater)
    bot.commands.register(name = "/exec" ,func = async_run, admin = True)
    bot.commands.register(name = "/login" ,func = async_login_num)
    bot.commands.register(name = "/sms" ,func = async_login_code)
    bot.commands.register(name = "/pass" ,func = async_login_2fa)
    bot.commands.register(name = "/token" ,func = async_login_session)
    bot.commands.register(name = "/logout" ,func = logout_tg)
    bot.commands.register(name = "/remove" ,func = remove_chat)
    bot.commands.register(name = "/down" ,func = down_media)

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
    
def remove_chat(payload, replies, message):
    """Remove current chat from telegram bridge. Example: /remove
       you can pass the all parametre to remove all chats like: /remove all"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para eliminar chats!')
       return
    if payload == 'all':
       chatdb[message.get_sender_contact().addr].clear()
       replies.add(text = 'Se desvincularon todos sus chats de telegram.')
    if str(message.chat.get_color()) in chatdb[message.get_sender_contact().addr].values():   
       for (key, value) in chatdb[message.get_sender_contact().addr].items():
           if value == str(message.chat.get_color()):
              del chatdb[message.get_sender_contact().addr][key]
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
       replies.add(text = 'Se ha cerrado la sesión en telegram, puede usar su token para iniciar en cualquier momento pero a nosotros se nos ha olvidado')
    else:
       replies.add(text = 'Actualmente no está logueado en el puente')
                                   
async def login_num(payload, replies, message):
    try:
       clientdb[message.get_sender_contact().addr] = TC(StringSession(), api_id, api_hash)
       await clientdb[message.get_sender_contact().addr].connect()
       me = await clientdb[message.get_sender_contact().addr].send_code_request(payload)
       hashdb[message.get_sender_contact().addr] = me.phone_code_hash
       phonedb[message.get_sender_contact().addr] = payload
       replies.add(text = 'Se ha enviado un codigo de confirmacion al numero '+payload+', por favor introdusca /sms CODIGO para iniciar')
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

def async_login_num(payload, replies, message):
    """Start session in Telegram. Example: /login +5312345678"""
    loop.run_until_complete(login_num(payload, replies, message))
            
async def login_code(payload, replies, message):   
    try:
       if message.get_sender_contact().addr in phonedb and message.get_sender_contact().addr in hashdb and message.get_sender_contact().addr in clientdb:
          try:
              me = await clientdb[message.get_sender_contact().addr].sign_in(phone=phonedb[message.get_sender_contact().addr], phone_code_hash=hashdb[message.get_sender_contact().addr], code=payload)               
              logindb[message.get_sender_contact().addr]=clientdb[message.get_sender_contact().addr].session.save()
              replies.add(text = 'Se ha iniciado sesiòn correctamente, su token es:\n\n'+logindb[message.get_sender_contact().addr]+'\n\nUse /token mas este token para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este')         
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
          replies.add(text = 'Se ha iniciado sesiòn correctamente, su token es:\n\n'+logindb[message.get_sender_contact().addr]+'\n\nUse /token mas este token para iniciar rápidamente.\n⚠No debe compartir su token con nadie porque pueden usar su cuenta con este')         
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
           client = TC(StringSession(payload), api_id, api_hash)
           await client.connect()
           my = await client.get_me()
           nombre = my.first_name
           await client.disconnect()
           replies.add(text='Ah iniciado sesión correctamente '+str(nombre))
           logindb[message.get_sender_contact().addr] = payload                      
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
       replies.add(text = 'Obteniedo chats...')
       contacto = message.get_sender_contact()
       client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)
       await client.connect()
       all_chats = await client.get_dialogs()
       chats_limit = 5
       for d in all_chats:
           if payload.lower()=='privates':
              private_only = hasattr(d.entity,'participants_count')
           else:
              private_only = False 
           ttitle = "Unknown"
           if hasattr(d,'title'):
              ttitle = d.title
           if str(d.id) not in chatdb[message.get_sender_contact().addr] and not private_only:
              chat_id = bot.create_group(ttitle, [contacto])
              img = await client.download_profile_photo(d.entity)
              if img and os.path.exists(img): 
                 chat_id.set_profile_image(img)
              chats_limit-=1
              chatdb[message.get_sender_contact().addr][str(d.id)] = str(chat_id.get_color())
              if d.unread_count == 0:
                 replies.add(text = "Estas al día con "+ttitle+".\n/more", chat = chat_id)
              else:
                 replies.add(text = "Tienes "+str(d.unread_count)+" mensajes sin leer de "+ttitle+"\n/more", chat = chat_id)
              if chats_limit<=0:
                 break
       await client.disconnect()          
       replies.add(text='Se agregaron '+str(5-chats_limit)+' chats a la lista!')
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def async_updater(bot, payload, replies, message):
    """Load chats from telegram. Example: /load
    you can pass privates for load private only chats like: /load privates"""
    loop.run_until_complete(updater(bot, payload, replies, message))
    if message.get_sender_contact().addr in logindb:
       async_save_delta_chats(replies = replies, message = message)
        
def down_media(message, replies, payload):
    """Download media message from telegram in a chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para descargar medios!')
       return
    if message.get_sender_contact().addr in chatdb and str(message.chat.get_color()) in chatdb[message.get_sender_contact().addr].values():
       for (key, value) in chatdb[message.get_sender_contact().addr].items():
           if value == str(message.chat.get_color()):
               try:
                  loop = asyncio.new_event_loop()
                  asyncio.set_event_loop(loop)
                  with TelegramClient(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash) as client:  
                       client.get_dialogs()
                       tchat = client(functions.messages.GetPeerDialogsRequest(peers=[int(key)] ))
                       ttitle = 'Unknown'
                       if hasattr(tchat,'chats') and tchat.chats:
                          ttitle = tchat.chats[0].title
                       all_messages = client.get_messages(int(key), ids = [int(payload)])
                       for m in all_messages:
                           if True:                       
                              mquote = ''
                              file_attach = 'archivo'
                              if hasattr(m,'reply_to'):
                                 if hasattr(m.reply_to,'reply_to_msg_id'):
                                    if client.get_messages(int(key), ids = [m.reply_to.reply_to_msg_id])[0]:
                                       mquote = '"'+client.get_messages(int(key), ids = [m.reply_to.reply_to_msg_id])[0].text+'"\n'
                              if hasattr(m.sender,'first_name'):
                                 send_by = str(m.sender.first_name)+":\n"
                              else:
                                 send_by = ""
                              if hasattr(m,'document') and m.document:
                                 if m.document.size<20971520:
                                    file_attach = client.download_media(m.document)
                                    replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                 else:
                                    if hasattr(m.document,'attributes') and m.document.attributes:
                                       if hasattr(m.document.attributes[0],'file_name'):
                                          file_attach = m.document.attributes[0].file_name
                                       if hasattr(m.document.attributes[0],'title'):
                                          file_attach = m.document.attributes[0].title
                                    replies.add(text = send_by+str(m.message)+"\n"+file_attach+" "+str(sizeof_fmt(m.document.size))+"\n/down_"+str(m.id))
                              if hasattr(m,'media') and m.media:
                                 if hasattr(m.media,'photo'):
                                    if m.media.photo.sizes[1].size<20971520:
                                       file_attach = client.download_media(m.media)
                                       replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                    else:
                                       replies.add(text = send_by+str(m.message)+"\nFoto de "+str(sizeof_fmt(m.media.photo.sizes[1].size))+"/down_"+str(m.id))                      
                              print('Descargando mensaje '+str(m.id))
                           else:
                              break
                       client.disconnect()
               except:
                  code = str(sys.exc_info())
                  replies.add(text=code)
               break
    else:
       replies.add(text='Este no es un chat de telegram')    

def load_chat_messages(message, replies):
    """Load more messages from telegram in a chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para cargar los mensajes!')
       return
    if message.get_sender_contact().addr in chatdb and str(message.chat.get_color()) in chatdb[message.get_sender_contact().addr].values():
       for (key, value) in chatdb[message.get_sender_contact().addr].items():
           if value == str(message.chat.get_color()):
               try:
                  loop = asyncio.new_event_loop()
                  asyncio.set_event_loop(loop)
                  with TelegramClient(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash) as client:  
                       #change limit to unread then send only 10 messages
                       client.get_dialogs()
                       tchat = client(functions.messages.GetPeerDialogsRequest(peers=[int(key)] ))
                       ttitle = 'Unknown'
                       if hasattr(tchat,'chats') and tchat.chats:
                          ttitle = tchat.chats[0].title
                       #else:
                       #   if hasattr(tchat,'users'):
                       #      ttitle = tchat.users[0].first_name
                       sin_leer = tchat.dialogs[0].unread_count
                       limite = 5
                       all_messages = client.get_messages(int(key), limit = sin_leer)
                       if sin_leer>0:
                          all_messages.reverse()
                       for m in all_messages:
                           if limite>=0:                       
                              mquote = ''
                              mservice = ''
                              file_attach = 'archivo'
                              if hasattr(m,'reply_to'):
                                 if hasattr(m.reply_to,'reply_to_msg_id'):
                                    if client.get_messages(int(key), ids = [m.reply_to.reply_to_msg_id])[0]:
                                       mquote = '"'+client.get_messages(int(key), ids = [m.reply_to.reply_to_msg_id])[0].text+'"\n'
                              if hasattr(m,'action') and m.action:
                                    mservice = '_system message_'
                              if hasattr(m.sender,'first_name'):
                                 send_by = str(m.sender.first_name)+":\n"
                              else:
                                 send_by = ""
                              no_media = True
                              if hasattr(m,'document') and m.document:
                                 if m.document.size<512000:
                                    file_attach = client.download_media(m.document)
                                    replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                 else:
                                    if hasattr(m.document,'attributes') and m.document.attributes:
                                       if hasattr(m.document.attributes[0],'file_name'):
                                          file_attach = m.document.attributes[0].file_name
                                       if hasattr(m.document.attributes[0],'title'):
                                          file_attach = m.document.attributes[0].title
                                    replies.add(text = send_by+str(m.message)+"\n"+file_attach+" "+str(sizeof_fmt(m.document.size))+"\n/down_"+str(m.id))
                                 no_media = False
                              if hasattr(m,'media') and m.media:
                                 if hasattr(m.media,'photo'):
                                    if m.media.photo.sizes[1].size<512000:
                                       file_attach = client.download_media(m.media)
                                       replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                    else:
                                       replies.add(text = send_by+str(m.message)+"\nFoto de "+str(sizeof_fmt(m.media.photo.sizes[1].size))+"/down_"+str(m.id))
                                    no_media = False
                                 if hasattr(m.media,'webpage'):
                                    replies.add(text = send_by+str(m.media.webpage.title)+"\n"+str(m.media.webpage.url))
                                    no_media = False
                              if no_media:
                                 replies.add(text = mservice+mquote+send_by+str(m.message))                    
                              m.mark_read()
                              print('Leyendo mensaje '+str(m.id))
                              #client.send_read_acknowledge(entity=int(key), message=m)
                           else:
                              #time.sleep(1)
                              replies.add(text = "Tienes "+str(sin_leer-2-5-limite)+" mensajes sin leer de "+ttitle+"\n/more")
                              break
                           limite-=1 
                       if sin_leer-limite<=0:
                          #time.sleep(1)
                          replies.add(text = "Estas al día con "+ttitle+"\n/more")
                       client.disconnect()
               except:
                  code = str(sys.exc_info())
                  replies.add(text=code)
               break
    else:
       replies.add(text='Este no es un chat de telegram')

def job():
    print("do the job")


@simplebot.command
def echo(payload, replies):
    """Echoes back text. Example: /echo hello world"""
    replies.add(text = payload or "echo")


async def echo_filter(message, replies):
    """Write direct in chat with T upper title to write a telegram chat"""
    if message.get_sender_contact().addr not in logindb:
       replies.add(text = 'Debe iniciar sesión para enviar mensajes!')
       return
    if str(message.chat.get_color()) in chatdb[message.get_sender_contact().addr].values():
       for (key, value) in chatdb[message.get_sender_contact().addr].items():
           if value == str(message.chat.get_color()):
               try:                  
                  client = TC(StringSession(logindb[message.get_sender_contact().addr]), api_id, api_hash)                
                  await client.connect()
                  await client.get_dialogs()
                  if message.filename:
                     if message.filename.find('.aac')>0:
                        await client.send_file(int(key), message.filename, voice_note=True)
                     else:
                        await client.send_file(int(key), message.filename, caption = message.text)
                  else:
                     await client.send_message(int(key),message.text)
                  await client.disconnect()
               except:
                  code = str(sys.exc_info())
                  replies.add(text=code)
    else:
       replies.add(text='Este chat no está vinculado a telegram')

@simplebot.filter
def async_echo_filter(message, replies):
    """Write direct in chat bridge to write to telegram chat"""
    loop.run_until_complete(echo_filter(message, replies))  


def eval_func(bot: DeltaBot, payload, replies, message: Message):
    """eval and back result. Example: /eval 2+2"""
    try:
       code = str(eval(payload))
    except:
       code = str(sys.exc_info())
    replies.add(text=code or "echo")

def start_updater(bot: DeltaBot, payload, replies, message: Message):
    """run schedule updater to get telegram messages. /start"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", seconds=10)
    scheduler.start()

async def c_run(payload, replies, message):
    """Run command inside a TelegramClient. Example: /c client.get_me()"""
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
    """Run command inside a TelegramClient. Example: /c client.get_me()"""
    loop.run_until_complete(c_run(payload, replies, message))  
            
def sizeof_fmt(num: float) -> str:
    """Format size in human redable form."""
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)

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
