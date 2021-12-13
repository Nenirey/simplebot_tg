#!/bin/bash
BOTPATH="${ADDR/@/"%40"}"
BOTZIPDB="${ADDR/@/"%40"}.zip"
BOTDB="$HOME/.simplebot/accounts/$BOTPATH/bot.db"
echo "BOTPATH = $BOTPATH"
echo "BOTZIPDB = $BOTZIPDB"
echo "BOTDB = $BOTDB"
if [ -f "$BOTDB" ]; then
   echo "Bot ya inicializado!"
   python3 -m simplebot init "$ADDR" "$PASSWORD"
else
   echo "Restaurando..."
   python3 ./restore.py
   python3 -m simplebot init "$ADDR" "$PASSWORD"
   if [ -f "$BOTZIPDB" ]; then
      echo "Bot restaurado!"
      rm "$BOTZIPDB"
   else
      echo "No existen restauras, configurando..."
      python3 -m simplebot --account "$ADDR" plugin --add ./telebridge.py
      python3 -m simplebot --account "$ADDR" admin --add "$ADMIN"
   fi
fi
python3 -m simplebot --account "$ADDR" serve

