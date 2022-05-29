#!/bin/bash
BOTPATH="${ADDR/@/"%40"}"
BOTZIPDB="${ADDR/@/"%40"}.zip"
BOTDB="$HOME/.simplebot/accounts/$BOTPATH/bot.db"
echo "BOTPATH = $BOTPATH"
echo "BOTZIPDB = $BOTZIPDB"
echo "BOTDB = $BOTDB"
if [ -f "$BOTDB" ]; then
   echo "Bot ya inicializado!"
else
   echo "Restaurando..."
   python3 ./restore.py
   if [ -f "$BOTZIPDB" ]; then
      echo "Bot restaurado!"
      rm "$BOTZIPDB"
   else
      echo "No existen restauras, configurando..."
      python3 -m simplebot init "$ADDR" "$PASSWORD"
      python3 -m simplebot --account "$ADDR" plugin --add ./telebridge.py
   fi
fi
if [ -n "$ADMIN" ]; then
   python3 -m simplebot --account "$ADDR" admin --add "$ADMIN"
fi
python3 -m simplebot --account "$ADDR" serve

