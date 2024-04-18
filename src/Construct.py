import json
import logging
import asyncio
import random




class Construct(object):
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.id_active = []
        self.log1 = logging.getLogger("Construct")
        self.log_level1= logging.DEBUG
        self.log1.setLevel(self.log_level1)
        self.meta_task = {}
        self.lock = asyncio.Lock()
        

    async def pid(self):
        self.log1.debug("call pid")
        while 1:
            n = random.randint(1,999)
            if n in self.pid_active:
                pass
            else:
                break
        return str(n)

    async def task_launcher(self,task,name,property):
        
        self.loop.create_task(task,name=name)
        self.log1.debug("create task: "+ name)
        self.id_active.append(name)
        await self.save_memory({name:property })


    async def load_memory(self,key):
        async with self.lock:
            try:
                with open(".memory.json") as file:
                    self.meta_task = json.load(file)
                    self.log1.debug('memory json load')
                file.close()
                del file
                return self.meta_task.get(key)
            except Exception as error:
                self.log1.error('memory json file error: ' +  str(error))
            
   
 
    

        

    async def save_memory(self,item):
        async with self.lock:
            self.meta_task.update(item)
            try:
                with open("./app/src/memory.json",'w') as file:
                    json.dump(self.meta_task,file)
                    self.log1.debug('memory json save')
                file.close()
            except Exception as error:
                self.log1.error('json file error ' +  str(error))
   

    async def metadata(self):
        return self.meta_task


class Circular_queue:
    def __init__(self):
        self.log = logging.getLogger("Circular_queue")
        self.log_level1= logging.DEBUG
        self.log.setLevel(self.log_level1)
        self.queue = asyncio.Queue()
        self.msg_id = set()
        self.pid_active = set()


    async def pid(self):
        self
        while 1:
            n = random.randint(1,100)
            if n in self.pid_active:
                pass
            else:
                break
        return str(n)
    

    async def put(self,msg):
        self.queue.put_nowait(msg)













    
    

    

