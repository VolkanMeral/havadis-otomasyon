#!/bin/bash
# Kullanım: ./uret.sh <kelime-klasörü>   (ör. ./uret.sh kahve)
# Ses parçaları bolumler/<k>/ses/ altında hazır olmalı.
set -e
K="$1"; D="bolumler/$K"; C="cikti/$K"; mkdir -p "$C"
python3 moduller/zamanla.py "$D/senaryo.json" "$D/anlatim.json" "$D/ses" "$D/senaryo_sesli.json" "$C/anlatim_ham.wav"
ffmpeg -loglevel error -y -i "$C/anlatim_ham.wav" -af "highpass=f=70,equalizer=f=150:t=q:w=1.0:g=3,equalizer=f=3000:t=q:w=1.4:g=1.2,deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=8:release=160:makeup=3,aecho=0.85:0.5:28|46:0.10|0.06,loudnorm=I=-16:TP=-1.5:LRA=7" -ar 44100 "$C/anlatim.wav"
python3 moduller/muzik_v2.py "$D/senaryo_sesli.json" "$C/muzik.wav"
python3 moduller/render_seri.py "$D/senaryo.json" x "$C/kapak_$K.jpg" kapak
python3 moduller/render_seri.py "$D/senaryo_sesli.json" "$C/muzik.wav" "$C/_video.mp4" > "$C/render.log" 2>&1
ffmpeg -loglevel error -y -i "$C/_video.mp4" -i "$C/anlatim.wav" -filter_complex "[1:a]aformat=channel_layouts=stereo,asplit=2[v1][v2];[0:a][v1]sidechaincompress=threshold=0.04:ratio=6:attack=40:release=400[m];[m]volume=0.5[mq];[mq][v2]amix=inputs=2:weights=1 1.2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart "$C/${K}_tam.mp4"
ffmpeg -loglevel error -y -i "$C/${K}_tam.mp4" -vf scale=720:1280 -c:v libx264 -preset veryfast -crf 25 -maxrate 3M -bufsize 6M -c:a aac -b:a 160k -movflags +faststart "$C/${K}_onizleme.mp4"
echo "BİTTİ $K $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$C/${K}_tam.mp4")"
