#!/bin/bash

timestamp() {
    date +%s
}


TS=$(timestamp)
USER=ironcaesar
HOST=10.0.2.16
DIR=~
ZIPFILE=backup_$TS.zip
BACKUP_PASS=$(~/backups/pass_gen.sh $TS)

zip -r --password $BACKUP_PASS $ZIPFILE ~/Desktop/backups
rsync -avz -e "ssh -i ~/.ssh/id_rsa" ./$ZIPFILE $USER@$HOST:$DIR
rm $ZIPFILE

