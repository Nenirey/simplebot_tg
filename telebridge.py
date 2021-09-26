import simplebot
from simplebot.bot import DeltaBot, Replies
from deltachat import Chat, Contact, Message
import sys
import os
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
#from telethon.events import StopPropagation
from telethon.sync import functions
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.types import InputPeerEmpty
from telethon.tl.types import PeerUser
from telethon import utils, errors
import asyncio
import re
import schedule, threading, time
import json
from datetime import datetime


version = "0.1.2"
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
login_hash = os.getenv('LOGIN_HASH')

global phonedb
phonedb = {}

global logindb
logindb = {}

global chatdb
chatdb = {}



@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.commands.register(name = "/eval" ,func = eval_func, admin = True)
    bot.commands.register(name = "/start" ,func = start_updater, admin = True)
    bot.commands.register(name = "/more" ,func = load_chat_messages, admin = True)
    bot.commands.register(name = "/news" ,func = updater, admin = True)
    bot.commands.register(name = "/c" ,func = c_run, admin = True)
    bot.commands.register(name = "/login" ,func = login_num, admin = True)
    bot.commands.register(name = "/sms" ,func = login_code, admin = True)
    bot.commands.register(name = "/remove" ,func = remove_chat, admin = True)
    
def remove_chat(payload, replies, message):
    """Remove current chat from telegram bridge. Example: /remove
       you can pass the all parametre to remove all chats like: /remove all"""
    if payload == 'all':
       chatdb.clear()
       replies.add(text = 'Se desvincularon todos sus chats de telegram.')
    if str(message.chat.id) in chatdb.values():   
       for (key, value) in chatdb.items():
           if value == str(message.chat.id):
              del chatdb[key]
              replies.add(text = 'Se desvinculó el chat delta '+value+' con el chat telegram '+key)
    else:
       replies.add(text = 'Este chat no está vinculado a telegram')
    try:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       with TelegramClient(StringSession(login_hash), api_id, api_hash) as client:
            tf = open('chatdb.json', 'w')
            json.dump(chatdb, tf)
            tf.close()
            client.edit_message('me',client.get_messages('me', ids=client(functions.users.GetFullUserRequest('me')).pinned_msg_id),'!!!Atención, este mensaje es parte del puente con deltachat, NO lo borre ni lo quite de los anclados o perdera el vinculo con telegram\n'+str(datetime.now()), file = 'chatdb.json')
            client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)

             
def login_num(payload, replies, message):
    """Start session in Telegram. Example: /login +5312345678"""
    try:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       with TelegramClient(StringSession(), api_id, api_hash) as client:
            client.connect()
            if not client.is_user_authorized():
               phonedb[message.get_sender_contact().addr] = payload 
               client.send_code_request(payload) 
               replies.add(text = 'Se ha enviado un codigo de confirmacion al numero '+payload+', por favor introdusca /sms CODIGO para iniciar')
            client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)
            
def login_code(payload, replies, message):
    """Confirm session in Telegram. Example: /sms 12345"""
    try:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       with TelegramClient(StringSession(), api_id, api_hash) as client:
            client.connect()
            if not client.is_user_authorized():
               if message.get_sender_contact().addr in phonedb:
                  client.sign_in(phonedb[message.get_sender_contact().addr], input('Enter code: '))
                  client.connect()
                  logindb[message.get_sender_contact().addr]=client.session.save()
               else:
                  replies.add(text = 'Debe introducir primero si numero de movil con /login NUMERO')
            else:
               replies.add(text = 'Ya se ha iniciado sesion correctamente') 
            client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code)            

def updater(bot, payload, replies, message):
    """Load chats from telegram"""
    try:
       replies.add(text = 'Actualizando...')
       contacto = message.get_sender_contact()
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       with TelegramClient(StringSession(login_hash), api_id, api_hash) as client:
            all_chats = client.get_dialogs()
            chats_limit = 5
            for d in all_chats:
                #es_privado = getattr(d.entity, 'is_private', False)
                #if not es_privado and d.unread_count != 0:
                ttitle = "Unknown"
                if hasattr(d,'title'):
                   ttitle = d.title
                if str(d.id) not in chatdb:
                   chat_id = bot.create_group('🇹 '+ttitle, [contacto])
                   chats_limit-=1
                   #if str(chat_id.id) not in chatdb.values():
                   chatdb[str(d.id)] = str(chat_id.id)
                #else:
                   #chat_id = bot.get_chat(int(chatdb[str(d.id)]))
                   """
                   all_messages = client.get_messages(d.id, limit = d.unread_count)
                   limite = 2
                   for message in all_messages:
                       if limite>=0:
                          if hasattr(message.sender,'first_name'):
                             replies.add(text = str(message.sender.first_name)+":\n"+str(message.message), chat = chat_id)                    
                          else: 
                             replies.add(text = str(message.message), chat = chat_id)
                          #message.mark_read()
                          limite-=1
                       else:
                          replies.add(text = str(d.unread_count-2-limite)+" sin leer de "+ttitle+"\n/more", chat = chat_id)
                          break
                   """
                   if d.unread_count == 0:
                      replies.add(text = "Estas al día con "+ttitle+".\n/more", chat = chat_id)
                   else:
                      replies.add(text = "Tienes "+str(d.unread_count)+" mensajes sin leer de "+ttitle+"\n/more", chat = chat_id)
                if chats_limit<=0:
                   break
            tf = open('chatdb.json', 'w')
            json.dump(chatdb, tf)
            tf.close()
            client.edit_message('me',client.get_messages('me', ids=client(functions.users.GetFullUserRequest('me')).pinned_msg_id),'!!!Atención, este mensaje es parte del puente con deltachat, NO lo borre ni lo quite de los anclados o perdera el vinculo con telegram\n'+str(datetime.now()), file = 'chatdb.json')
            client.disconnect()
            replies.add(text='Chats actualizados!')
    except:
       code = str(sys.exc_info())
       replies.add(text=code)

def load_chat_messages(message, replies):
    """Load more messages from telegram in a chat"""
    if str(message.chat.id) in chatdb.values():
       for (key, value) in chatdb.items():
           if value == str(message.chat.id):
               try:
                  loop = asyncio.new_event_loop()
                  asyncio.set_event_loop(loop)
                  with TelegramClient(StringSession(login_hash), api_id, api_hash) as client:  
                       #change limit to unread then send only 10 messages
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
                              if hasattr(m.sender,'first_name'):
                                 send_by = str(m.sender.first_name)+":\n\n"
                              else:
                                 send_by = ""
                              no_media = True
                              if hasattr(m,'document') and m.document:
                                 no_media = False
                                 if m.document.size<204800:
                                    file_attach = client.download_media(m.document)
                                    replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                 else:
                                    replies.add(text = send_by+str(m.message)+"\nadjunto de "+str(m.document.size)+" bytes")
                              if hasattr(m,'media') and m.media:
                                 no_media = False 
                                 if m.media.photo.sizes[1].size<204800:
                                    file_attach = client.download_media(m.media)
                                    replies.add(text = send_by+file_attach+"\n"+str(m.message), filename = file_attach)
                                 else:
                                    replies.add(text = send_by+str(m.message)+"\nadjunto de "+str(m.media.photo.sizes[1].size)+" bytes")
                              if no_media:
                                 replies.add(text = send_by+str(m.message))                    
                              m.mark_read()
                              print('Leyendo mensaje '+str(m.id))
                              #client.send_read_acknowledge(entity=int(key), message=m)
                           else:
                              replies.add(text = "Tienes "+str(sin_leer-2-5-limite)+" mensajes sin leer de "+ttitle+"\n/more")
                              break
                           limite-=1 
                       if sin_leer==0 or limite>=1:
                          replies.add(text = "Estas al día con "+ttitle+"\n/more")
                       client.disconnect()
               except:
                  code = str(sys.exc_info())
                  replies.add(text=code)
               break
    else:
       replies.add(text='Este no es un chat de telegram')

def forever():
    while True:
          schedule.run_pending()
          time.sleep(1)


@simplebot.command
def echo(payload, replies):
    """Echoes back text. Example: /echo hello world"""
    replies.add(text = payload or "echo")


@simplebot.filter
def echo_filter(message, replies):
    """Write direct in chat with T upper title to write a telegram chat"""
    if str(message.chat.id) in chatdb.values():
       for (key, value) in chatdb.items():
           if value == str(message.chat.id):
               try:
                  loop = asyncio.new_event_loop()
                  asyncio.set_event_loop(loop)
                  #client(functions.messages.GetPeerDialogsRequest(peers=[int(key)]))
                  with TelegramClient(StringSession(login_hash), api_id, api_hash) as client:
                       if message.filename:
                          client.send_file(int(key),message.filename)
                       else:
                          client.send_message(int(key),message.text)
                       client.disconnect()
               except:
                  code = str(sys.exc_info())
                  replies.add(text=code)
    else:
       replies.add(text='Este chat no está vinculado a telegram')
    #replies.add(text = 'Escribes desde un chat de telegram')


#@simplebot.command(admin=True)
def eval_func(bot: DeltaBot, payload, replies, message: Message):
    """eval and back result. Example: /eval 2+2"""
    try:
       code = str(eval(payload))
    except:
       code = str(sys.exc_info())
    replies.add(text=code or "echo")

#@simplebot.command(admin=True)
def start_updater(bot: DeltaBot, payload, replies, message: Message):
    """run schedule updater to get telegram messages. /start"""
    schedule.every(10).seconds.do(updater, bot=bot, payload=payload, replies=replies, message=message)    
    t1 = threading.Thread(target = forever)
    t1.start()

#@simplebot.command(admin=True)
def c_run(payload, replies):
    """Run command inside a TelegramClient. Example: /c client.get_me()"""
    try:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       with TelegramClient(StringSession(login_hash), api_id, api_hash) as client:
            client.get_dialogs()
            code = str(eval(payload))
            if replies: 
               replies.add(text = code)
            client.disconnect()
    except:
       code = str(sys.exc_info())
       print(code)
       if replies:
          replies.add(text=code or "echo")
try:
    c_run(payload = "client.download_media(client.get_messages('me', ids=client(functions.users.GetFullUserRequest('me')).pinned_msg_id))", replies=None)
    if os.path.isfile('chatdb.json'):
       tf = open('chatdb.json','r')
       chatdb=json.load(tf)
       tf.close()
    else:
       tf = open('chatdb.json', 'w')
       json.dump(chatdb, tf)
       tf.close()
       c_run(payload = "client.pin_message('me',client.send_file('me', 'chatdb.json'))", replies=None) 
except:
    tf = open('chatdb.json', 'w')
    json.dump(chatdb, tf)
    tf.close()
    c_run(payload = "client.pin_message('me',client.send_file('me', 'chatdb.json'))", replies=None) 


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
