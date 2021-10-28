#!/bin/bash
python3 -m simplebot init "$ADDR" "$PASSWORD"
python3 -m simplebot --account "$ADDR" plugin --add ./telebridge.py
python3 -m simplebot --account "$ADDR" admin --add "$ADMIN"
python3 -m simplebot --account "$ADDR" serve
