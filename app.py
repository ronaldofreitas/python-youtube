from flask import Flask, request, jsonify
import youtube_dl
from urllib import parse
import json
import urllib.request
import re
from google.cloud import storage
import os
storage_client = storage.Client()
bucket_destino = storage_client.get_bucket("catalobyte-input")

app = Flask(__name__)

# um link de 2:30:00 dá mais ou menos 150Mb de arquivo final .m4a

def YTDurationToSeconds(duration):
    match = re.match('PT(\d+H)?(\d+M)?(\d+S)?', duration).groups()
    hours = _js_parseInt(match[0]) if match[0] else 0
    minutes = _js_parseInt(match[1]) if match[1] else 0
    seconds = _js_parseInt(match[2]) if match[2] else 0
    return hours * 3600 + minutes * 60 + seconds

def _js_parseInt(string):
    return int(''.join([x for x in string if x.isdigit()]))

class MyLogger(object):
    def debug(self, msg):
        #print(msg)
        pass

    def warning(self, msg):
        #print(msg)
        pass

    def error(self, msg):
        print(msg)

@app.route("/", methods=["POST"])
def receive():
    data = request.get_json()
    firebase_uid = data['foldername'] #  recebe como parametro da function/task - é a pasta inicial do bucket 'catalobyte-youtube'
    iduid = data['iduid']
    uuid_file = data['uuid_file']
    url_yt = data['urlyoutube']
    datetime = data['datetime']
    idioma = data['idioma']
    traduzir = data['traduzir']
    repidom = idioma.replace("-","_")# pt-BR para pt_BR
    nomearquivo = iduid+'-'+str(datetime)+'-'+uuid_file+'-'+str(repidom)+".m4a"
    dst_local = "./output/"+nomearquivo
    dst_bucket = firebase_uid +'/'+nomearquivo

    url_parsed = parse.urlparse(url_yt)
    qsl = parse.parse_qs(url_parsed.query)
    yt_video_id = qsl['v'][0]

    credent_api_key = 'AIzaSyCIss0SDAyB60qBnH1Q0gkG3J6ZGScqfqw'
    url_api = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&key={credent_api_key}&id={yt_video_id}&part=contentDetails'

    webURL = urllib.request.urlopen(url_api)
    data = webURL.read()
    encoding = webURL.info().get_content_charset('utf-8')
    dt = data.decode(encoding)
    d2 = json.loads(dt)
    timetube = d2['items'][0]['contentDetails']['duration']
    yt_time = YTDurationToSeconds(timetube)

    if(yt_time <= 10800):# 10800 segundos = 3 horas
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': dst_local,
            'logger': MyLogger(),
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_yt])
            
        blob = bucket_destino.blob(dst_bucket)
        blob.upload_from_filename(dst_local)
        blob.metadata = {'x-goog-meta-item-idiom': idioma, 'x-goog-meta-item-trad': traduzir}
        blob.patch()
        return "ok"
    else:
        # salva em um bucket 'catalobyte-erros'
        return "not-ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)