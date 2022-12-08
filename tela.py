import io
import json
import time
from datetime import datetime
import requests
import cv2 as cv
import numpy as np
from sys import argv
from os import listdir, remove
from os.path import join
from PySimpleGUI import PySimpleGUI as sg
from PIL import Image


class TelaPython:
    def __init__(self):
        self.time_ = 0
        self.start_time_ = 0
        self.json_path = '/home/pi/data'
        # self.json_path = 'data'
        self.json_name = 'data.json'
        self.get_url = 'http://192.168.100.21:8001/api/v1/retrieve_image'
        # Layout
        W,H = sg.Window.get_screen_size()
        self.w, self.h = int(W/15)*14,int(H/15)*14
        self.Log('START', False, 'w')
        self.img = self.Make_img("AGUARDANDO CARREGAMENTO")
        self.img = self.Image_Define(self.img)
        layout = [
            [sg.Push()],
            [sg.Push(), sg.Image(data= self.img, key='-IMAGEM-'), sg.Push()],
        ]

        # Janela
        self.janela = sg.Window('Expedição', layout=layout, no_titlebar=True, location=(0,0), size=(W,H), keep_on_top=True)
        
    def Log(self, text, previous = True, mod = 'a' ):
        """Salva dados em arquivo de log (log.txt)"""
        moment = float(datetime.now().strftime('%S.%f'))
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if previous:
            previous_time = self.time_
        else:
            previous_time = moment
            self.start_time_ = moment
        if text == 'Tela atualizada':
            total = f', tempo total: {moment-self.start_time_:.3f}s\n'
        else:
            total = '\n'
        if text == 'Json detectado':
            s = 50*'-'+'\n'
        else:
            s = ''
        with open('/home/pi/log.txt', mod) as FILE:
        # with open('log.txt', mod) as FILE:
            FILE.write(f'{s}{date} {text:23} {moment-previous_time:.3f}s{total}')
        self.time_ = moment
    
    # def Draw_Bounds(self, bounds, img):
    #     """Desenha as bounds"""
    #     color = (50, 200, 50)
    #     fator_x = self.original_shape[0]/img.shape[0]
    #     fator_y = self.original_shape[1]/img.shape[1]
    #     l = int(20/fator_x)
    #     for bound, content in bounds:
    #         X = [i[0] for i in bound]
    #         Y = [i[1] for i in bound]
    #         max_x, min_x = int(max(X)/fator_x),int(min(X)/fator_x)
    #         max_y, min_y = int(max(Y)/fator_y),int(min(Y)/fator_y)
    #         img = cv.rectangle(img, (max_x, max_y) , (min_x, min_y), color, l)
    #         text = content.split('/')[-1]
    #         img = cv.putText(img,f'{text[-4:]}', (min_x-(3*l), min_y-l), cv.FONT_HERSHEY_COMPLEX,  3/fator_x, color, int(l/2))
    #     self.Log(f'{len(bounds):02d} Bounds desenhados')
    #     return img

    def Image_Define(self, jpg_data):
        """Converte imagem de array decimal (.jpg) para um array bytes hexadecimais (.png)"""
        imgbytes = cv.imencode('.png', jpg_data)[1].tobytes()
        self.Log('Imagem convertida')
        return imgbytes
    
    def Get_Information(self):
        """Lê os dados de interesse do arquivo json"""
        path = join(self.json_path, self.json_name)
        with open(path, 'r') as FILE:
            data = json.load(FILE)
        remove(path)
        self.original_shape = data['shape']
        if 'ip' in data and 'port' in data:
            self.get_url = f"http://{data['ip']}:{data['port']}/api/v1/retrieve_image"
        else:
            self.Log('ip ou porta não identificado')
        self.Log(f'Json lido ({self.get_url.split("/")[2]})')
        return [(lecture['bounds'],lecture['content']) for lecture in data['lectures']]

    def Image_Update(self):
        """Captura a imagem do servidor"""
        bounds = self.Get_Information()
        self.Log('Iniciando get da imagem')
        try:    
            r = requests.get(self.get_url)
            self.Log('Get da imagem concluido')
            if r.status_code == 200:
                img = np.array(Image.open(io.BytesIO(r.content)))
                img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
                self.img = cv.resize(img, (self.w,self.h), interpolation = cv.INTER_AREA)
                # if bounds:
                #     self.img = self.Draw_Bounds(bounds, self.img)
                # else:
                if not bounds:
                    self.img = self.Make_img(f"NENHUMA LEITURA ({datetime.now().strftime('%H:%M')})", False)
            else:
                self.img = self.Make_img(f"FALHA NA CAPTURA ({datetime.now().strftime('%H:%M')})")
        except:
            self.img = self.Make_img(f"AGUARDANDO IMAGEM ({datetime.now().strftime('%H:%M')})")



    def Update_Screen(self):
        """Atualiza a imagem da tela"""
        cv.imwrite('/home/pi/img.jpg', self.img)
        # cv.imwrite('img.jpg', self.img)
        self.Log('Atualizando tela')
        self.img = self.Image_Define(self.img)
        self.janela['-IMAGEM-'].update(self.img)
        self.Log('Tela atualizada')
        # self.img.save("/home/pi/img.png")
        # self.Log('png salvo')
    
    def Make_img(self, text, black_background = True):
        """Cria uma imagem com a string enviada"""
        if black_background:
            img = np.zeros([self.h, self.w, 3]).astype(int)
            color = (255,255,255)
        else:
            img = self.img
            color = (50, 200, 50)
        img = cv.putText(np.float32(img), text, (int(self.w/20), self.h-int(self.h/20)), cv.FONT_HERSHEY_DUPLEX, 2, color, 10)
        self.Log(text)
        return img
    
    def Iniciar(self):
        while True:
            """Extrai os dados da Janela"""
            self.event, self.values = self.janela.read(timeout=100)
            if self.event == sg.WINDOW_CLOSED:
                break 
            if self.json_name in listdir(self.json_path):
                self.Log('Json detectado', False)
                time.sleep(0.2)
                self.Image_Update()
                self.Update_Screen()
        self.janela.close()

tela = TelaPython()
tela.Iniciar()
