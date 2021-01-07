from operator import attrgetter

import numpy as np

from hardware import *
import log

class Program():

    def __init__(self, instructions):
        self._instructions = self.expand(instructions)

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(instructions=self._instructions)

class Dispatcher():

    def __init__(self):
        self._mmu = HARDWARE.mmu
        self._cpu = HARDWARE.cpu
        HARDWARE.timer.reset()

    def load(self, pcb, pageTable):
        log.logger.info("-- Dispatcher LOAD {pcb}".format(pcb=pcb))
        #self._mmu.limit = pcb.dirLim
        self._cpu.pc = pcb.pc
        HARDWARE.mmu.resetTLB()
        page = 0
        for frame in pageTable:
            HARDWARE.mmu.setPageFrame(page, frame)
            page = page + 1

    def save(self, pcb):
        log.logger.info("-- Dispatcher SAVE {pcb}".format(pcb=pcb))
        pcTest = self._cpu.pc
        log.logger.info(pcTest)
        pcb.setPC(pcTest)
        self._cpu.pc= -1


class PCB():

    def __init__(self, pid, pc, state, path, priority):
        self._pid = pid #la identidad activa
        self._pc = pc #Donde fue cargado*
        self._state = state #Necesito saber que estado esta
        self._dirLim = HARDWARE.memory.size
        self._path = path #nombre del programa
        self._priority = priority

    @property
    def pid(self):
        return self._pid

    @property
    def pc(self):
        return self._pc

    @property
    def state(self):
        return self._state

    @property
    def dirLim(self):
        return self._dirLim

    @property
    def path(self):
        return self._path

    #@state.setter
    def setState(self, state):
        self._state = state

    #@pc.setter
    def setPC(self, pc):
        self._pc = pc

    def getPid(self):
        return self._pid

    @property
    def priority(self):
        return self._priority

    def __repr__(self):
        return "PCB pid {pid} pc: {pc} state: {state}".format(pid=self._pid, pc=self._pc, state=self._state)

class ReadyQueue():
    def __init__(self):
        self._readyPCBs = []

    @property
    def readyQueue(self):
        return self._readyPCBs

    def addPCB(self, pcb):
        self._readyPCBs.append(pcb)

    def getNext(self):
        try:
            return self._readyPCBs.pop(0)
        except:
            raise ValueError ("La cola esta vacia")

    def hasNext(self):
        return len(self._readyPCBs) > 0

class PCBTable(): #Tabla de proceso

    def __init__(self):
        self._pcbRunning = None
        self._table = []
        self._incrementalPid = 0

    @property
    def runningPCB(self):
        return self._pcbRunning

    @property
    def table(self):
        return self._table

    def getNewPID(self):
        return self.numeroMaximo() + 1

    def numeroMaximo(self):
        return max(pcb.pid for pcb in self._table) if self._table else 0

    def addPCB (self, pcb):
        self._table.append(pcb)

    def getPCB(self, pid):
        result = None
        for pcb in self._table:
            if (pcb.getPid() == pid):
                result = pcb
        return result

    def setRunning(self, pcb):
        self._pcbRunning = pcb

    def getRunnigPCB (self):
        return self._pcbRunning

class MemoryManager():
    def __init__(self):
        self._pageTable = dict()
        amount = round(HARDWARE.memory.size / HARDWARE.mmu.frameSize)
        self._freeFrames = list(range(amount))

    def freeFrame (self, frames):
        self._freeFrames = self._freeFrames + frames
        return self._freeFrames

    def allocFrames(self, cantidadDePagina):
        if len(self._freeFrames) < cantidadDePagina:
            raise Exception('No hay espacio sufiente en la Memoria')
        else:
            frame = self._freeFrames[:cantidadDePagina]  #self._freeFrames[:cantidadDePagina - 1]
            self._freeFrames = self._freeFrames[-(len(self._freeFrames) - cantidadDePagina):]
            return frame

    def putPageTable (self, pid, pageTable):
        self._pageTable[pid] = pageTable

    def getPageTable (self, pid):
        return self._pageTable[pid] 

class Loader():
    def __init__(self, memoryManager, fileSystem):
        self._memoryManager = memoryManager
        self._fileSystem = fileSystem
        self._frameSize = HARDWARE.mmu.frameSize

    def load_program(self, pcb):
        # loads the program in main memory
        path = pcb._path
        program = self._fileSystem.read(path)
        mmuFrameSize = HARDWARE.mmu.frameSize
        cantidadDeInstrucciones = len(program.instructions)
        cantidadDePaginas = int(np.ceil(cantidadDeInstrucciones / mmuFrameSize)) #round(cantidadDeInstrucciones / mmuFrameSize) + 1

        frames = self._memoryManager.allocFrames(cantidadDePaginas)
        self._memoryManager.putPageTable(pcb.pid, frames)
        addresses = self.getAddresses(frames)
        for p in program.instructions:
            address = addresses.pop(0)
            HARDWARE.memory.write(address, p)

    def getAddresses(self, listOfFrames):
        addresses = []
        mmuFrameSize = HARDWARE.mmu.frameSize
        for frame in listOfFrames:
            for r in range(0, mmuFrameSize):
                address = (frame * mmuFrameSize) + r
                addresses.append(address)
        return addresses

class FileSystem ():

    def __init__ (self):
        self.programs = dict()

    def write (self, path, program):
        self.programs[path] = program

    def read (self, path):
        #path = {'path': path}
        return self.programs.get(path)

class Scheduler ():

    def __init__(self):
        self._readyQueue = ReadyQueue()

    @property
    def readyQueue (self):
        return self._readyQueue

    def addReadyQueue (self,pcb):
        pass

    def getNext (self):
        pass

    def hasNext (self):
        pass

    def mustExpropiate(self,pcbRunnig, pcb):
        pass

class FCFS (Scheduler):

    def addReadyQueue(self,pcb):
        self.readyQueue.addPCB(pcb)

    def getNext(self):
        return self.readyQueue.getNext()

    def hasNext(self):
        return self.readyQueue.hasNext()

    def mustExpropiate(self,pcbRunnig, pcb):
        return False

class PrioNonPreemptive (Scheduler):

    def addReadyQueue(self, pcb):
        self.readyQueue.addPCB(pcb)
        sorted(self.readyQueue.readyQueue, key=attrgetter ('priority'))

    def getNext(self):
        return self.readyQueue.getNext()

    def hasNext(self):
        return self.readyQueue.hasNext()

    def mustExpropiate(self,pcbRunnig, pcb):
        return False

class RoundRobin (Scheduler):

    def __init__(self, quantum):
        super().__init__()
        HARDWARE.timer.quantum = quantum

    def addReadyQueue(self, pcb):
        self.readyQueue.addPCB(pcb)

    def getNext(self):
        return self.readyQueue.getNext()

    def hasNext (self):
        return self.readyQueue.hasNext()

    def mustExpropiate(self,pcbRunnig, pcb):
        return False

class PrioPreemptive(Scheduler):

    def addReadyQueue(self, pcb):
        self.readyQueue.addPCB(pcb)

    def getNext(self):
        return self.readyQueue.getNext()

    def hasNext (self):
        return self.readyQueue.hasNext()

    def mustExpropiate(self,pcbRunnig, pcb):
        return  pcbRunnig.priority >= pcb.priority

    # la diferencia entre PrioNonPreemptive y PrioPreemptive va a ser en el metodo
    #donde tiene que ser expropiativo o no

## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)

    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))

    def expropiate(self, pcb):
        pcbRunning = self.kernel.pcbTable.getRunnigPCB()
        pcbRunning.setState("READY")
        self.kernel.scheduler.addReadyQueue(pcbRunning)
        self.kernel.dispatcher.save(pcbRunning)

        pcb.setState("RUNNING")
        pageTable = self.kernel.mmg.getPageTable(pcb.pid)
        self.kernel.dispatcher.load(pcb, pageTable)
        self.kernel.pcbTable.setRunning(pcb)


class TimeOutInterruptionHandler (AbstractInterruptionHandler):

    def execute(self, irq):
        if (self.kernel.scheduler.hasNext()):
            pcbRunnig = self.kernel.pcbTable.getRunnigPCB()
            self.kernel.dispatcher.save(pcbRunnig)
            pcbRunnig.setState("READY")
            self.kernel.scheduler.addReadyQueue(pcbRunnig)
            pcbNext = self.kernel.scheduler.getNext()
            pcbNext.setState("RUNNING")
            pageTable = self.kernel.mmg.getPageTable(pcbNext.pid)
            self.kernel.dispatcher.load(pcbNext, pageTable)
            HARDWARE.timer.reset()
        else:
            HARDWARE.timer.reset()
        ##Preguntar por si se resetea en io

class NewInterruptionHandler(AbstractInterruptionHandler):
    #Quiero que se ejecute en la cpu
    def execute(self, irq):
        #log.logger.info("-ENTRANDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))
        #llega un programa,
        path = irq.parameters['path']
        prioridad = irq.parameters['prioridad']
        pid = self.kernel.pcbTable.getNewPID()#genero un nuevo pid
        pcb = PCB(pid, 0, "NEW", path, prioridad)#para agregarle a esta pcb
        self.kernel.loader.load_program(pcb)
        self.kernel.pcbTable.addPCB(pcb)
        #log.logger.info(pcb.pid)

        if self.kernel.pcbTable.getRunnigPCB() == None :
            pcb.setState ("RUNNING")
            log.logger.info(pid)
            self.kernel.pcbTable.setRunning(pcb)
            pageTable = self.kernel.mmg.getPageTable (pcb.pid)
            self.kernel.dispatcher.load(pcb, pageTable)
            #log.logger.info( self.kernel.pcbTable._pcbRunning)
        elif self.kernel.scheduler.mustExpropiate(self.kernel.pcbTable.getRunnigPCB(), pcb):
            self.expropiate(pcb)
        else:
            pcb.setState("READY")
            self.kernel.scheduler.addReadyQueue(pcb)
        #log.logger.info("-SALIENDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))

class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        #log.logger.info("-ENTRANDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))
        pcbFinalizado = self.kernel.pcbTable.getRunnigPCB() #la pcb que quiero finalizar es el proceso que se encuentra en la pcbtable con estado runnig
        self.kernel.dispatcher.save(pcbFinalizado) #dispacher saca el pcb de la pc
        pcbFinalizado.setState("TERMINATED")
        self.kernel.pcbTable.setRunning(None)
        pagetable = self.kernel.mmg.getPageTable(pcbFinalizado.pid)
        self._kernel.mmg.freeFrame(pagetable)
        #if self.kernel._readyQueue._readyPCBs:

        if self.kernel.scheduler.hasNext():
            nextPCB = self.kernel.scheduler.getNext()
            pageTable = self.kernel.mmg.getPageTable (nextPCB.pid)
            self.kernel.dispatcher.load(nextPCB, pageTable)
            nextPCB.setState("RUNNING")
            self.kernel.pcbTable.setRunning(nextPCB)

           #log.logger.info("-SALIENDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))

class IoInInterruptionHandler(AbstractInterruptionHandler):
    #Se genera cuando quiero ingresar a un dipositivo, tiene que sacarle el proceso de la CPU
    #y mandarlo a la waiting new de otro dispositivo

    def execute(self, irq):
        log.logger.info("-ENTRANDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.scheduler.readyQueue._readyPCBs))
        operation = irq.parameters #Es el print que le quiero mandar al dispositivo
        #program = irq.parameters['program']
        #prioridad = irq.parameters['prioridad']
        pcb =  self.kernel.pcbTable._pcbRunning #Busco el pcb running que quierosacar de pcb
        self.kernel.dispatcher.save(pcb) #saco la pcb de la cpu
        pcb.setState("WAITING") # y le cambio el estado a waiting
        #log.logger.info(self.kernel.ioDeviceController)
        self.kernel.pcbTable.setRunning(None)
        #la pcb ya esta en WAITING ahora vamos a ver que pasa con la CPU

        if self.kernel.scheduler.hasNext():
            nextPCB = self.kernel.scheduler.getNext()
            pageTable = self.kernel.mmg.getPageTable (nextPCB.pid)
            self.kernel.dispatcher.load(nextPCB, pageTable)
            nextPCB.setState("RUNNING")
            self.kernel.pcbTable.setRunning(nextPCB)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        #log.logger.info("-SALIENDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
       # log.logger.info("-ENTRANDO- Scheduler {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.Scheduler._readyPCBs))
        pcb = self.kernel.ioDeviceController.getFinishedPCB() #Tenemos un solo dispositivo, estaba en estado waiting
       # log.logger.info(self.kernel.ioDeviceController)

        if self.kernel.pcbTable.getRunnigPCB() == None:
            pcb.setState("RUNNING")
            self.kernel.pcbTable.setRunning(pcb)
            pageTable = self.kernel.mmg.getPageTable (pcb.pid)
            self.kernel.dispatcher.load(pcb, pageTable)
        elif self.kernel.scheduler.mustExpropiate(self.kernel.pcbTable.getRunnigPCB(), pcb):
            self.expropiate(pcb)
        else:
            pcb.setState("READY")
            self.kernel.scheduler.addReadyQueue(pcb)
#        log.logger.info("-SALIENDO- ReadyQueue {rq} - runningPCB: {runningPCB}".format(runningPCB=self.kernel.pcbTable._pcbRunning,rq=self.kernel.readyQueue._readyPCBs))

# emulates the core of an Operative System
class Kernel():

    def __init__(self, scheduler):
        HARDWARE.mmu.frameSize = 4
        self._dispatcher = Dispatcher()
        self._pcbTable = PCBTable()
        self._interruptVector = HARDWARE.interruptVector
        self._scheduler = scheduler
        self._memoryManager = MemoryManager()
        self._fileSystem = FileSystem()
        self._loader = Loader(self._memoryManager, self._fileSystem)


        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)


        timeOutHandler = TimeOutInterruptionHandler (self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeOutHandler)
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

    @property
    def loader(self):
        return self._loader

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def pcbTable(self):
        return self._pcbTable

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def mmg (self):
        return self._memoryManager

    ## emulates a "system call" for programs execution
    
    @property
    def fileSystem (self):
        return self._fileSystem

    def run(self, path, prioridad):
        pair = {'path': path, 'prioridad': prioridad}
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, pair)
        HARDWARE.interruptVector.handle(newIRQ)
        log.logger.info(HARDWARE)



    def __repr__(self):
        return "Kernel"

