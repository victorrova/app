
import requests
import json
import logging
from datetime import datetime
import asyncio
import time

class Bateria:
    def __init__(self,construct,config, queue):
        self.id = config["bateria"]["id"]
        self.pub_topic = config["bateria"]["topic"]
        self.subs_topic = config["bateria"]["subs_topic"]
        self.msg_queue = queue
        self.log = logging.getLogger("bateria")
        self.log_level = logging.DEBUG
        self.log.setLevel(self.log_level)
        self.token = ""
        self.pvpc =[]
        self.price = 0.11
        self.Kwh =0
        self.Wh = 0
        self.req = 0
        self.construct = construct
        self.log.info("clase iniciada con exito")
        self.Internal_config = {"module":"bateria", "task":["_loop"],"topic": self.pub_topic, "subs_topic": self.subs_topic}
        self.ant_time = 0
    
    async def Config(self):
        return self.Internal_config
            
    
    async def req_pryce(self):
        url2 = "https://api.esios.ree.es/archives/70/download_json"
        headers = {'Accept':'application/json; application/vnd.esios-api-v2+json','Content-Type':'application/json','Host':'api.esios.ree.es','Authorization':'Token token=' + self.token}     
        response = requests.get(url2, headers=headers)
        if response.status_code == 200:
            self.log.debug("Api esios OK response")
            json_data = json.loads(response.text)
            dia = int(json_data["PVPC"][0]["Dia"].split("/")[0])
            self.pvpc = []
            if dia == datetime.now().day:
                for n in json_data["PVPC"]:
                    self.pvpc.append(int(n['PCB'].split(",")[0])/1000)
                await self.construct.save_memory({"pvpc":self.pvpc})
                self.log.debug("pvp:"+ str( self.pvpc))
           
            else:
                for n in range(0,24):
                    self.pvpc.append(0)
            
        del json_data
    

    async def charge(self,injected, grid_power):
        multi = self.pvpc[datetime.now().hour] / self.price
        lapse_time = time.time() - self.ant_time
        W = round((injected - (grid_power * multi)) * (lapse_time/ 3600),2)
        self.Wh = round(injected - (grid_power * multi),2)
        self.ant_time = time.time()
        self.Kwh += round(W/1000 ,2)
        await self.construct.save_memory({"bateria":{"Kwh":self.Kwh}})
        return { "Kwh": self.Kwh, "Wh":self.Wh }


    async def reset(self):
            self.Kwh = 0

    async def _loop(self):
        
        await self.req_pryce()
        try:
            Kwh = await self.construct.load_memory("bateria")
            self.Kwh = Kwh["Kwh"]
        except TypeError as e:
            self.log.debug("Kwh no guardados en memoria, inicio en 0")
            self.Kwh = 0
        self.log.info("Hilo principal de bateria iniciado")
        self.ant_time = time.time()
        while True:
            try:
                if datetime.now().hour == 1 and self.req == 0:
                    await self.req_pryce()
                    self.req = 1
                elif datetime.now().hour == 0:
                    self.req = 0
                if datetime.now().day == 1:
                    await self.reset()
                    
                if not self.msg_queue.empty():
                    msg = await self.msg_queue.get()
                    
                    self.log.debug("mensaje entrante de:" + msg[0])
                    self.msg_queue.put_nowait(msg)
                    self.msg_queue.task_done()
                    self.log.debug("mensaje retornado")
                    if msg[0] == self.subs_topic:
                        json_data =json.loads(msg[1])
                        env = await self.charge(json_data["injected_power"],json_data["grid_power"])
                        self.msg_queue.put_nowait((self.pub_topic, json.dumps(env)))
                        self.log.debug("mensaje enviado para publicación")
                await asyncio.sleep(1)
            except Exception as error:
                self.log.error("_loop error" + str(error))
                
                

    async def run(self,task = None):
        if task == "_loop":
            await self.construct.task_launcher(self._loop(),"_loop",self.Internal_config)
        else:
            self.log.debug("No se encuentra la Tarea para inicio")


     
        
def main(const,config,queue):
    
    b = Bateria(const,config,queue)
    return b

