import json
import sys
import threading
import time

from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot, Signal, QThread
from PySide6.QtWidgets import QApplication, QLabel
from qfluentwidgets import FluentWindow, NavigationItemPosition, ProgressBar

from qfluentwidgets import FluentIcon as FIF

from MyWidget import *
from SysjSignal import OutputSignal, InputSignalManager, OutputSignalManager, SignalBase


class BottlePosCheckThread(QThread):
    bottlePosChanged = Signal(int)

    def __init__(self, bottlePosList: list[OutputSignal]):
        super().__init__()
        self.bottlePosList = bottlePosList

    def run(self):
        while True:
            for i, bottlePos in enumerate(self.bottlePosList):
                if bottlePos.status:
                    self.bottlePosChanged.emit(i)
                    break
            else:
                self.bottlePosChanged.emit(-1)
            time.sleep(0.5)


def createFillerSignal(fillerIdx: str, iPort, oPort) -> tuple[list[OutputSignal], list[InputSignal], list]:
    iSig = []
    oSig = []

    iSig.append(InputSignal(f"valveInjector{fillerIdx}OnOff", "FillerModel", iPort))
    iSig.append(InputSignal(f"valveInlet{fillerIdx}OnOff", "FillerModel", iPort))
    iSig.append(InputSignal(f"dosUnit{fillerIdx}ValveRetract", "FillerModel", iPort))
    iSig.append(InputSignal(f"dosUnit{fillerIdx}ValveExtend", "FillerModel", iPort))
    iSig.append(InputSignal(f"filler{fillerIdx}Idle", "Coordinator", iPort))

    oSig.append(OutputSignal(f"bottleAtPos2{fillerIdx}", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"dosUnit{fillerIdx}Evac", f"Filler{fillerIdx}ControllerCD", oPort, initStatus=True))
    oSig.append(OutputSignal(f"dosUnit{fillerIdx}AtTarget", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"bottleAtPos2{fillerIdx}Full", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"filler{fillerIdx}DoProcess", f"Filler{fillerIdx}ControllerCD", oPort,
                             oneShot=True, ignoreSocket=True))

    def fillerSimu(signals):
        def simuThread():
            signals[0].changeStatus(True)
            time.sleep(1)
            signals[1].changeStatus(False)
            time.sleep(2)
            signals[2].changeStatus(True)
            time.sleep(1)
            signals[2].changeStatus(False)
            time.sleep(2)
            signals[1].changeStatus(True)
            time.sleep(1)
            signals[0].changeStatus(False)

        threading.Thread(target=simuThread).start()

    simuEvent = [
        None,
        None,
        None,
        None,
        (fillerSimu, oSig)
    ]

    return oSig, iSig, simuEvent


class Window(FluentWindow):

    def __init__(self):
        super().__init__()

        self.outputSignalMngr = OutputSignalManager()
        self.inputSignalMngr = InputSignalManager()
        self.inputSignalMngr.recvSignal.connect(self.updateStatusLight)
        self.globalStatusLights = []

        self.inputSigCallbackMap: dict[str, tuple] = {}
        self.allOutputSignal: dict[str, list[OutputSignal]] = {}

        # create sub interface
        self.posInterface = PosWidget(self)
        posSignal = OutputSignal("POS", "POS", 50000, oneShot=True)
        self.posInputSignal = InputSignal("POS", "POS", 51000)
        self.outputSignalMngr.addSignal(posSignal)
        self.inputSignalMngr.addSignal(self.posInputSignal)
        self.posInterface.setOutputSignal(posSignal)

        self.baxterInterface = Widget('Baxter', self)
        self.fillersInterface = Widget('Fillers', self)
        self.fillerAInterface = Widget('Filler-A', self)
        self.fillerBInterface = Widget('Filler-B', self)
        self.fillerCInterface = Widget('Filler-C', self)
        self.fillerDInterface = Widget('Filler-D', self)
        self.lipLoaderInterface = Widget('Lip Loader', self)
        self.capperInterface = Widget('Capper', self)
        self.rotaryAndConveyorInterface = Widget('Rotary and Conveyor', self)

        self.rotaryAndConveyorOverallLayout = QVBoxLayout()
        self.overallSimulatorButton = PushButton()
        self.overallSimulatorButton.setText('Simulate All')
        self.overallSimulatorButton.clicked.connect(lambda: threading.Thread(target=self.simulatorAll).start())
        self.rotaryAndConveyorOverallLayout.addWidget(self.overallSimulatorButton)

        self.bottlePosHBoxLayout = QHBoxLayout()
        self.bottlePosBar = ProgressBar()
        self.bottlePosBar.setRange(0, 7)
        self.bottlePosBar.setValue(0)
        self.bottlePosHBoxLayout.addWidget(self.bottlePosBar)
        self.bottlePosLabel = QLabel()
        self.bottlePosLabel.setText('Bottle Position: N/A')
        self.bottlePosHBoxLayout.addWidget(self.bottlePosLabel)
        self.bottlePosList = []

        self.rotaryAndConveyorOverallLayout.addLayout(self.bottlePosHBoxLayout)

        self.rotaryAndConveyorInterface.vBoxLayout.addLayout(self.rotaryAndConveyorOverallLayout)
        self.rotaryAndConveyorInterface.vBoxLayout.addSpacing(30)

        self.initNavigation()
        self.initWindow()
        self.initInterfaces()

        self.outputSignalMngr.start()
        self.inputSignalMngr.start()

        self.bottlePosList.append(self.allOutputSignal['conveyor'][0])
        self.bottlePosList.append(self.allOutputSignal['fillerA'][0])
        self.bottlePosList.append(self.allOutputSignal['fillerB'][0])
        self.bottlePosList.append(self.allOutputSignal['fillerC'][0])
        self.bottlePosList.append(self.allOutputSignal['fillerD'][0])
        self.bottlePosList.append(self.allOutputSignal['capper'][0])
        self.bottlePosList.append(self.allOutputSignal['conveyor'][1])

        self.bottlePosCheckThread = BottlePosCheckThread(self.bottlePosList)
        self.bottlePosCheckThread.bottlePosChanged.connect(self.updateBottlePos)
        self.bottlePosCheckThread.start()

    def updateBottlePos(self, bottlePos: int):
        POS_STR = ['POS1', 'POS2A', 'POS2B', 'POS2C', 'POS2D', 'POS4', 'POS Left 5']

        if bottlePos == -1:
            if self.bottlePosBar.getVal() == 7:
                self.bottlePosLabel.setText('Bottle Position: N/A')
                self.bottlePosBar.setValue(0)
        else:
            self.bottlePosLabel.setText(f'Bottle Position: {POS_STR[bottlePos]}')
            self.bottlePosBar.setValue(bottlePos + 1)

    def initNavigation(self):
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.rotaryAndConveyorInterface, FIF.ROTATE, 'Rotary and Conveyor')
        self.addSubInterface(self.posInterface, FIF.PIN, "POS")
        self.navigationInterface.addSeparator()

        self.addSubInterface(self.baxterInterface, FIF.ROBOT, 'Baxter', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.fillersInterface, FIF.BACKGROUND_FILL, 'Fillers', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.fillerAInterface, FIF.BACKGROUND_FILL, 'Filler A', parent=self.fillersInterface)
        self.addSubInterface(self.fillerBInterface, FIF.BACKGROUND_FILL, 'Filler B', parent=self.fillersInterface)
        self.addSubInterface(self.fillerCInterface, FIF.BACKGROUND_FILL, 'Filler C', parent=self.fillersInterface)
        self.addSubInterface(self.fillerDInterface, FIF.BACKGROUND_FILL, 'Filler D', parent=self.fillersInterface)
        self.addSubInterface(self.lipLoaderInterface, MIF.LL, 'Lip Loader',
                             NavigationItemPosition.SCROLL)
        self.addSubInterface(self.capperInterface, MIF.CAPPER, 'Capper',
                             NavigationItemPosition.SCROLL)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        self.setWindowTitle('Advanced Loader')

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        # set the minimum window width that allows the navigation panel to be expanded
        # self.navigationInterface.setMinimumExpandWidth(900)
        # self.navigationInterface.expand(useAni=False)

    def createCdCardByIOSignal(self, iSig: list[InputSignal], oSig: list[OutputSignal], simulatorEvent=None):
        cdCard = CdCard()
        cdCard.addOutputSignals(oSig, simulatorEvent=simulatorEvent)
        lights = cdCard.addStatusLights(iSig)

        for signal in oSig:
            self.outputSignalMngr.addSignal(signal)
        for signal in iSig:
            self.inputSignalMngr.addSignal(signal)
        for light in lights:
            self.globalStatusLights.append(light)

        return cdCard

    def initRotaryAndConveyorInterface(self):
        oSigRotary: list[OutputSignal] = [
            OutputSignal("tableAlignedWithSensor", "RotaryTableControllerCD", 40001, initStatus=True),
            OutputSignal("bottleAtPos5", "RotaryTableControllerCD", 40001),
            OutputSignal("capOnBottleAtPos1", "RotaryTableControllerCD", 40001),
            OutputSignal("move2NextPos", "RotaryTableControllerCD", 40001, oneShot=True, ignoreSocket=True),
        ]

        iSigRotary: list[InputSignal] = [
            InputSignal("rotaryTableTrigger", "RotaryTableModel", 41001),
            InputSignal("rotaryIdle", "Coordinator", 41001),
        ]

        def rotaryTriggerCallback(signals: list[OutputSignal]):
            def simuThread():
                signals[0].changeStatus(False)
                time.sleep(1)
                signals[0].changeStatus(True)

            threading.Thread(target=simuThread).start()

        self.inputSigCallbackMap['rotaryTableTrigger'] = (rotaryTriggerCallback, oSigRotary)
        self.allOutputSignal['rotaryTable'] = oSigRotary

        def rotarySimu(signals: list[OutputSignal]):
            def simuThread():
                signals[0].changeStatus(False)
                time.sleep(1)
                signals[0].changeStatus(True)

            threading.Thread(target=simuThread).start()

        simulatorEvent: list = [
            None,
            None,
            None,
            (rotarySimu, oSigRotary)
        ]

        rotaryCdCard = self.createCdCardByIOSignal(iSigRotary, oSigRotary, simulatorEvent=simulatorEvent)
        self.rotaryAndConveyorInterface.addCdCard(rotaryCdCard)

        oSigConveyor: list[OutputSignal] = [
            OutputSignal("bottleAtPos1", "ConveyorControllerCD", 40000),
            OutputSignal("bottleLeftPos5", "ConveyorControllerCD", 40000),
        ]
        iSigConveyor: list[InputSignal] = [
            InputSignal("motConveyorOnOff", "ConveyorModel", 41000),
        ]

        self.allOutputSignal['conveyor'] = oSigConveyor

        conveyorCdCard = self.createCdCardByIOSignal(iSigConveyor, oSigConveyor)
        self.rotaryAndConveyorInterface.addCdCard(conveyorCdCard)

    def initFillerABCDInterfaces(self):
        oSigFillerA, iSigFillerA, eventA = createFillerSignal('A', 41002, 40002)
        oSigFillerB, iSigFillerB, eventB = createFillerSignal('B', 41003, 40003)
        oSigFillerC, iSigFillerC, eventC = createFillerSignal('C', 41004, 40004)
        oSigFillerD, iSigFillerD, eventD = createFillerSignal('D', 41005, 40005)

        self.allOutputSignal['fillerA'] = oSigFillerA
        self.allOutputSignal['fillerB'] = oSigFillerB
        self.allOutputSignal['fillerC'] = oSigFillerC
        self.allOutputSignal['fillerD'] = oSigFillerD

        fillerACdCard = self.createCdCardByIOSignal(iSigFillerA, oSigFillerA, simulatorEvent=eventA)
        self.fillerAInterface.addCdCard(fillerACdCard)

        fillerBCdCard = self.createCdCardByIOSignal(iSigFillerB, oSigFillerB, simulatorEvent=eventB)
        self.fillerBInterface.addCdCard(fillerBCdCard)

        fillerCCdCard = self.createCdCardByIOSignal(iSigFillerC, oSigFillerC, simulatorEvent=eventC)
        self.fillerCInterface.addCdCard(fillerCCdCard)

        fillerDCdCard = self.createCdCardByIOSignal(iSigFillerD, oSigFillerD, simulatorEvent=eventD)
        self.fillerDInterface.addCdCard(fillerDCdCard)

    def initCappeerInterface(self):
        oSigCapper: list[OutputSignal] = [
            OutputSignal("bottleAtPos4", "CapperControllerCD", 40006),
            OutputSignal("gripperZAxisLowered", "CapperControllerCD", 40006),
            OutputSignal("gripperZAxisLifted", "CapperControllerCD", 40006, initStatus=True),
            OutputSignal("gripperTurnHomePos", "CapperControllerCD", 40006, initStatus=True),
            OutputSignal("gripperTurnFinalPos", "CapperControllerCD", 40006),
            OutputSignal("capperDoProcess", "CapperControllerCD", 40006, oneShot=True, ignoreSocket=True),
        ]

        iSigCapper: list[InputSignal] = [
            InputSignal("cylPos5ZaxisExtend", "CapperModel", 41006),
            InputSignal("gripperTurnRetract", "CapperModel", 41006),
            InputSignal("gripperTurnExtend", "CapperModel", 41006),
            InputSignal("capGripperPos5Extend", "CapperModel", 41006),
            InputSignal("cylClampBottleExtend", "CapperModel", 41006),
            InputSignal("capperIdle", "Coordinator", 41006),
        ]

        self.allOutputSignal['capper'] = oSigCapper

        def capperSimu(signals: list[OutputSignal]):
            def simuThread():
                signals[0].changeStatus(True)
                time.sleep(1)
                signals[2].changeStatus(False)
                time.sleep(1)
                signals[1].changeStatus(True)
                time.sleep(0.5)
                signals[3].changeStatus(False)
                time.sleep(1)
                signals[4].changeStatus(True)
                time.sleep(0.5)
                signals[4].changeStatus(False)
                time.sleep(0.5)
                signals[3].changeStatus(True)
                signals[1].changeStatus(False)
                time.sleep(1)
                signals[2].changeStatus(True)
                signals[0].changeStatus(False)

            threading.Thread(target=simuThread).start()

        simulatorEvent: list = [
            None,
            None,
            None,
            None,
            None,
            (capperSimu, oSigCapper)
        ]

        capperCdCard = self.createCdCardByIOSignal(iSigCapper, oSigCapper, simulatorEvent=simulatorEvent)
        self.capperInterface.addCdCard(capperCdCard)

    def initInterfaces(self):
        self.initRotaryAndConveyorInterface()
        self.initFillerABCDInterfaces()
        self.initCappeerInterface()

    @Slot(SignalBase)
    def updateStatusLight(self, sb: SignalBase):
        if sb.name in self.inputSigCallbackMap:
            if sb.status:
                callback, signals = self.inputSigCallbackMap[sb.name]
                callback(signals)

        if sb.cd == 'POS':
            updateOrderDtoDict = json.loads(sb.value)
            updateOrderDto = UpdateOrderDto(updateOrderDtoDict['bottleId'], updateOrderDtoDict['orderId'],
                                            updateOrderDtoDict['bottleIndex'], updateOrderDtoDict['orderAmount'])
            self.posInterface.updateOneOrder(updateOrderDto)
            return

        for light in self.globalStatusLights:
            if light.label.text() == sb.name:
                light.setStatus(sb.status)
                return

    def simulatorAll(self):
        def fillerSimu(sigList: list[OutputSignal]):
            sigList[0].changeStatus(True)
            time.sleep(1)
            sigList[1].changeStatus(False)
            time.sleep(2)
            sigList[2].changeStatus(True)
            time.sleep(1)
            sigList[2].changeStatus(False)
            time.sleep(2)
            sigList[1].changeStatus(True)
            time.sleep(1)
            sigList[0].changeStatus(False)

        def capperSimu(sigList: list[OutputSignal]):
            sigList[0].changeStatus(True)
            time.sleep(1)
            sigList[2].changeStatus(False)
            time.sleep(1)
            sigList[1].changeStatus(True)
            time.sleep(0.5)
            sigList[3].changeStatus(False)
            time.sleep(1)
            sigList[4].changeStatus(True)
            time.sleep(0.5)
            sigList[4].changeStatus(False)
            time.sleep(0.5)
            sigList[3].changeStatus(True)
            sigList[1].changeStatus(False)
            time.sleep(1)
            sigList[2].changeStatus(True)
            sigList[0].changeStatus(False)

        def rotarySimu(sigList: list[OutputSignal]):
            sigList[0].changeStatus(False)
            time.sleep(1)
            sigList[0].changeStatus(True)

        # bottle At Pos1
        self.allOutputSignal['conveyor'][0].changeStatus(False)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        time.sleep(0.5)
        fillerSimu(self.allOutputSignal['fillerA'])
        time.sleep(0.5)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        time.sleep(0.5)
        fillerSimu(self.allOutputSignal['fillerB'])
        time.sleep(0.5)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        time.sleep(0.5)
        fillerSimu(self.allOutputSignal['fillerC'])
        time.sleep(0.5)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        time.sleep(0.5)
        fillerSimu(self.allOutputSignal['fillerD'])
        time.sleep(0.5)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        time.sleep(0.5)
        capperSimu(self.allOutputSignal['capper'])
        time.sleep(0.5)
        rotarySimu(self.allOutputSignal['rotaryTable'])
        self.allOutputSignal['conveyor'][1].changeStatus(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()
