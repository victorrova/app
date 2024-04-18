import json
import logging
import asyncio
from logging.handlers import RotatingFileHandler
import sys
from Construct import Construct
from mqtt_beta import MQTT
import queue
import psutil
import os
import sys


print('''	(  ____ \(  ____ )(  ___  )( (    /|| \    /\|\     /|
	| (    \/| (    )|| (   ) ||  \  ( ||  \  / /( \   / )
	| (__    | (____)|| (___) ||   \ | ||  (_/ /  \ (_) / 
	|  __)   |     __)|  ___  || (\ \) ||   _ (    \   /  
	| (      | (\ (   | (   ) || | \   ||  ( \ \    ) (   
	| )      | ) \ \__| )   ( || )  \  ||  /  \ \   | |   
	|/       |/   \__/|/     \||/    )_)|_/    \/   \_/


		         .-""-"-""-.
		        /           
 			| .--.-.--. |
		        |` >       `|
		        | <         |
		        (__..---..__)
		       (`|\o_/ \_o/|`)
		        \(    >    )/
		      [>=|   ---   |=<]
		         \__\   /__/
		             '-'
###############################################################
###############################################################''')

class Core:
    def __init__(self,configjson):
        self.loop = asyncio.get_event_loop()
        self.log = self.configure_log()
        self.config = self.Config(configjson)
        self.mqtt_queue = asyncio.Queue()
        self.subs_topic =[]
        self.topics = []
        self.imports = []
        self.queue = queue.SimpleQueue()
        self.mqtt = MQTT(self.config,self.queue)
        self.mqtt.run()
        self.construct = Construct()
        self.ka_timer = 60
        sys.path.append("./componentes")
        self.Internal_config = {"module":"core", "task":["keepalive", "mqtt_loop"],"topic": None, "subs_topic": None}
        self.lock = asyncio.Lock()
    
    async def Config(self):
        return self.Internal_config
            
        


    async def keepalive(self):
        try:
            while True:
                if not self.mqtt_queue.full():
                    self.mqtt_queue.put_nowait((self.config["config"]['topic'] + '/keepalive', json.dumps({'topic': self.config["config"]['topic'], 
						'cpu_load': psutil.cpu_percent(interval=1,percpu=True),
						'freq':psutil.cpu_percent(interval=1,percpu=True),
						'ram':round(psutil.virtual_memory().available /1024**2, 2),
						'temp': "hello"}))) #,psutil.sensors_temperatures()['cpu_thermal'][0].current})))
                    await asyncio.sleep(self.ka_timer)
                else:
                    await asyncio.sleep(1)
        except Exception as error:
            self.log.exception(str(error))



    async def mqtt_loop(self):
        self.log.info("task mqtt run")
        try:
            while True:
                
                if not self.mqtt_queue.empty():
                    _msg = await self.mqtt_queue.get()
                    self.mqtt_queue.task_done()
                    self.log.debug("mensaje para gestionar "+ str(_msg[0]))
                    async with self.lock:
                        if _msg[0] in self.subs_topic:
                            self.mqtt_queue.put_nowait(_msg)
                            self.log.debug("mensaje devuelto a la cola " + str(_msg[0]))
                        elif _msg[0] in self.topics:
                            self.mqtt.pub(_msg[0],_msg[1])
                            self.log.debug("mensaje publicado")
                        elif _msg[0] in self.topics and _msg[0] in self.subs_topic:
                            self.mqtt.pub(_msg[0],_msg[1])
                            self.mqtt_queue.put_nowait(_msg)
                            self.log.debug("mensaje publicado y devuelto a la cola")
                        else:
                            self.log.debug("mensaje no esperado")
                        
                    await asyncio.sleep(0.5)
                   
                elif not self.queue.empty():
                    _arrival =self.queue.get()
                    self.log.debug("llegada de mensaje: "+ str(_arrival[0]))
                    self.mqtt_queue.put_nowait(_arrival)
                    self.log.debug("mensaje entrante en cola de gestion")
                    await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(1)           
        except Exception as error:
            self.log.exception(str(error))



    def configure_mqtt(self):
        self.mqtt = MQTT(self.config,self.queue)
        self.mqtt.run()
    
    async def subscribe(self,topic):
        self.mqtt.sub(topic)
        self.subs_topic.append(topic)
        self.log.debug("Subscrito a : "+ topic)
    
    async def  unsubscribe(self, topic):
        self.mqtt.unsub(topic)
        self.log.debug("Subscripción %s eliminada",topic)
        




    def configure_log(self):
        FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s %(funcName)-20s:%(lineno)-8s %(message)s')
        log_console_format = "[%(levelname)s]: %(message)s"
        log = logging.basicConfig(
        handlers=[RotatingFileHandler('Deb.log', maxBytes=10**5, backupCount=1)],
        level=logging.DEBUG,
        format=FORMAT,
        datefmt='%Y-%m-%dT%H:%M:%S')
        log = logging.getLogger()
        Stream_log = logging.StreamHandler(sys.stdout)
        Stream_log.setLevel(logging.INFO)
        Stream_log.setFormatter(logging.Formatter(log_console_format))
        log.addHandler(Stream_log)
        return log

    def Config(self,archivo):
        ''' Función de lectura de archivo de configuración CONFIG.json'''
        self.log.info("cargarando configuración")
        try:
            with open(archivo) as file:
                conf = json.load(file)
                self.log.info('config cargada con exito')
                return conf
        except Exception as error:
            self.log.error('error en archivo json ' +  str(error))
            raise
    




    async def control_topics(self):
        async with self.lock:
            for n  in self.topics:
                if n in self.subs_topic:
                    self.subs_topic.remove(n)
                    await self.unsubscribe(n)
                    self.log.info("%s se ha eliminado de la lista de subscripciones",n)

    async def _imports2(self,m):
        try:
            self.log.warning("importando : "+ str(m))
            module = __import__(m)
            _class = module.main(self.construct,self.config, self.mqtt_queue)
            _class_conf = await _class.Config()
            async with self.lock:
                for n in _class_conf["task"]:
                    await _class.run(task=n)
                    if type((_class_conf["topic"]))== list:
                        for n in _class_conf["topic"]:
                            if not n in self.topics:
                                self.topics.append(n)
                    else:
                        if not n in self.topics:
                            self.topics.append(_class_conf["topic"])

                    if _class_conf["subs_topic"]:
                        if type((_class_conf["subs_topic"]))== list:
                            for n in _class_conf["subs_topic"]:
                                if not n in self.topics:
                                    self.subs_topic.append(n)
                                    await self.subscribe(n)
                                    self.log.debug( n + "se ha añadido a la lista de subscriciones")

                        else:        
                            if not _class_conf["subs_topic"] in self.topics:
                                self.subs_topic.append(_class_conf["subs_topic"])
                                await self.subscribe(_class_conf["subs_topic"])
                                self.log.debug(_class_conf["subs_topic"] + "se ha añadido a la lista de subscriciones")
                    

                    

        except Exception as error:
            self.log.exception(error)
    
    async def scan_dir(self):
        self.log.info(" Inicio de Scandir")
        while 1:
            with os.scandir("./componentes/") as ficheros:
                for file in ficheros:
                    if not file.is_file():
                        continue
                    elif file.name == "__init__.py":
                        continue
                    elif file.name == "CONFIG.json":
                        continue
                    mod = file.name.split(".")
                    if not mod[0] in self.imports:
                        self.log.info("modulo [%s] encontrado", mod[0])
                    if mod[1] =="py" or mod[1] =="pyc" or mod[1] =="pyd":
                        if not mod[0] in self.imports:
                            await self. _imports2(mod[0])
                            self.imports.append(mod[0])
                            self.log.debug("Archivo  %s añadido ", mod[0])
                    else:
                        self.log.debug("Archivo %s icompatible o ya añadido", mod[0])
            await self.control_topics()  
            await asyncio.sleep(10)




            

    async def run(self):
        #self.construct.task_launcher(self.keepalive(),"core",3)
        await self.construct.task_launcher(self.mqtt_loop(),"mqtt_loop",self.Internal_config)
        #await self._imports()
        await self.construct.task_launcher(self.scan_dir(),"scan_dir",self.Internal_config)

    



if __name__ == "__main__":
    core = Core("./componentes/CONFIG.json")
    loop = asyncio.get_event_loop()
    loop.create_task(core.run())
    loop.run_forever()


        




