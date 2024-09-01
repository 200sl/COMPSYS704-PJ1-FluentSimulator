import json
import queue
import selectors
import socket
import time

from PySide6.QtCore import QThread, Signal


class SocketBaseInfo:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def __eq__(self, other):
        if isinstance(other, SocketBaseInfo):
            return self.ip == other.ip and self.port == other.port
        return False

    def __hash__(self):
        return hash((self.ip, self.port))


class SignalMessageDto:
    def __init__(self, name: str, cd: str, status: bool, value: None | str = None):
        self.name = name
        self.cd = cd
        self.status = status
        self.value = value

    def __dict__(self):
        rtDict = {
            "name": self.name,
            "cd": self.cd,
            "status": self.status
        }

        if self.value is not None:
            rtDict["value"] = self.value

        return rtDict

    def toJson(self) -> str:
        myDict = self.__dict__()
        return json.dumps(myDict, indent=4)


class SignalBase:
    def __init__(self, name, cd, status=False):
        self.name = name
        self.cd = cd
        self.status = status
        self.signalDto = SignalMessageDto(name, cd, self.status)

    def __eq__(self, other):
        if isinstance(other, SignalBase):
            return self.name == other.name and self.cd == other.cd
        return False

    def __hash__(self):
        return hash((self.name, self.cd))


class OutputSignal(SignalBase):
    def __init__(self, name, cd, port, ip="127.0.0.1"):
        super().__init__(name, cd)

        self.socketInfo = SocketBaseInfo(ip, port)
        self.socket = None

    def changeStatus(self, status: bool):
        self.status = status
        self.signalDto.status = status

    def setSocket(self, so):
        self.socket = so

    def isSocketAvailable(self):
        return self.socket is not None

    def sendSignal(self):
        if self.isSocketAvailable():
            self.socket.send(self.signalDto.toJson().encode())
        else:
            # print(f"{self.name} is not connected to the server")
            pass


class InputSignal(SignalBase):
    def __init__(self, name, cd, port, ip="127.0.0.1"):
        super().__init__(name, cd)
        self.socketInfo = SocketBaseInfo(ip, port)


def createClientSocket(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.01)  # set 10ms to
        sock.connect((ip, port))
    except socket.timeout:
        # print(f"{ip}:{port}, Connection timeout")
        sock.close()
        return None
    except socket.error as e:
        print(f"{ip}:{port}, Connection Error: {e}")
        sock.close()
        return None

    return sock


def createServerSocket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.listen(10)
        sock.setblocking(False)
    except socket.error as e:
        print(f"Error: {e}")
        sock.close()
        return None

    return sock


class OutputSignalManager(QThread):

    def __init__(self):
        super().__init__()
        self.registeredSignal: queue.Queue[OutputSignal] = queue.Queue()

    def addSignal(self, signal: OutputSignal):
        self.registeredSignal.put(signal)

    def run(self) -> None:
        socketInfoMap = {}
        outputSignalSet: set[OutputSignal] = set()

        while True:
            time.sleep(0.25)
            # check if there is any new signal
            if not self.registeredSignal.empty():
                signal = self.registeredSignal.get()
                if signal not in outputSignalSet:
                    outputSignalSet.add(signal)

            for signal in outputSignalSet:
                if signal.socketInfo not in socketInfoMap:
                    newSocket = createClientSocket(signal.socketInfo.ip, signal.socketInfo.port)
                    if newSocket is not None:
                        socketInfoMap[signal.socketInfo] = newSocket
                        signal.setSocket(socketInfoMap[signal.socketInfo])
                        time.sleep(0.5)
                        continue
                else:
                    if not signal.isSocketAvailable():
                        signal.setSocket(socketInfoMap[signal.socketInfo])

                try:
                    signal.sendSignal()
                except socket.error as e:
                    print(f"Error: {e}")
                    signal.socket.close()
                    socketInfoMap.pop(signal.socketInfo)
                    signal.setSocket(None)


class InputSignalManager(QThread):
    recvSignal = Signal(SignalBase)

    def __init__(self):
        super().__init__()
        self.registeredSignal: queue.Queue[InputSignal] = queue.Queue()

        self.servSocks = []
        self.recordSockInfoSet: set[SocketBaseInfo] = set()

        self.sel = selectors.DefaultSelector()

    def addSignal(self, signal: InputSignal):
        self.registeredSignal.put(signal)

    @staticmethod
    def readClientData(inputSigMngr, conn):
        data = conn.recv(1024)
        if not data:
            print(f"Connection closed")
        else:
            print(f"Received: {data}")

            dataStr = data.decode()

            for oneStr in dataStr.split("\r\n"):
                try:
                    jsDict = json.loads(oneStr)
                    sig = SignalBase(jsDict["name"], jsDict["cd"], jsDict["status"])
                    inputSigMngr.recvSignal.emit(sig)

                except json.JSONDecodeError:
                    continue

    @staticmethod
    def acceptedConnection(inputSigMngr, sock):
        conn, addr = sock.accept()
        print(f"Connection from {addr}")
        conn.setblocking(False)
        inputSigMngr.sel.register(conn, selectors.EVENT_READ, inputSigMngr.readClientData)

    def run(self) -> None:
        while True:
            time.sleep(0.25)
            if not self.registeredSignal.empty():
                signal = self.registeredSignal.get()
                sockInfo = signal.socketInfo
                if sockInfo not in self.recordSockInfoSet:
                    newSock = createServerSocket(sockInfo.port)
                    if newSock is not None:
                        print(f"Server socket created: {sockInfo.ip}:{sockInfo.port}")
                        self.servSocks.append(newSock)
                        self.recordSockInfoSet.add(sockInfo)
                        self.sel.register(newSock, selectors.EVENT_READ, self.acceptedConnection)

            if len(self.servSocks) > 0:
                for key, mask in self.sel.select(timeout=1):
                    callback = key.data
                    callback(self, key.fileobj)
