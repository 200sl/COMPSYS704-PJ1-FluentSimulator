import sys

from PySide6.QtGui import QIcon

from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, NavigationItemPosition

from qfluentwidgets import FluentIcon as FIF

from MyWidget import *
from SysjSignal import OutputSignal, InputSignalManager, OutputSignalManager


def createFillerSignal(fillerIdx: str, iPort, oPort) -> tuple[list[OutputSignal], list[InputSignal]]:
    iSig = []
    oSig = []

    iSig.append(InputSignal(f"valveInjector{fillerIdx}OnOff", "FillerModel", iPort))
    iSig.append(InputSignal(f"valveInlet{fillerIdx}OnOff", "FillerModel", iPort))
    iSig.append(InputSignal(f"dosUnit{fillerIdx}ValveRetract", "FillerModel", iPort))
    iSig.append(InputSignal(f"dosUnit{fillerIdx}ValveExtend", "FillerModel", iPort))
    iSig.append(InputSignal(f"filler{fillerIdx}Idle", "Coordinator", iPort))

    oSig.append(OutputSignal(f"bottleAtPos2{fillerIdx}", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"dosUnit{fillerIdx}Evac", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"dosUnit{fillerIdx}AtTarget", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"bottleAtPos2{fillerIdx}Full", f"Filler{fillerIdx}ControllerCD", oPort))
    oSig.append(OutputSignal(f"filler{fillerIdx}DoProcess", f"Filler{fillerIdx}ControllerCD", oPort, oneShot=True))

    return oSig, iSig


class Window(FluentWindow):

    def __init__(self):
        super().__init__()

        # create sub interface
        self.posInterface = Widget('POS', self)
        self.overallInterface = Widget('Overall', self)
        self.baxterInterface = Widget('Baxter', self)
        self.fillersInterface = Widget('Fillers', self)
        self.fillerAInterface = Widget('Filler-A', self)
        self.fillerBInterface = Widget('Filler-B', self)
        self.fillerCInterface = Widget('Filler-C', self)
        self.fillerDInterface = Widget('Filler-D', self)
        self.lipLoaderInterface = Widget('Lip Loader', self)
        self.capperInterface = Widget('Capper', self)
        self.rotaryAndConveyorInterface = Widget('Rotary and Conveyor', self)

        self.outputSignalMngr = OutputSignalManager()
        self.inputSignalMngr = InputSignalManager()
        self.inputSignalMngr.recvSignal.connect(self.updateStatusLight)
        self.globalStatusLights = []

        self.initNavigation()
        self.initWindow()
        self.initInterfaces()

        self.outputSignalMngr.start()
        self.inputSignalMngr.start()

    def initNavigation(self):
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.overallInterface, FIF.VIEW, 'Overall')
        self.addSubInterface(self.posInterface, FIF.PIN, "POS")
        self.navigationInterface.addSeparator()

        self.addSubInterface(self.rotaryAndConveyorInterface, FIF.ROTATE, 'Rotary and Conveyor')
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
            OutputSignal("tableAlignedWithSensor", "RotaryTableControllerCD", 40001),
            OutputSignal("bottleAtPos5", "RotaryTableControllerCD", 40001),
            OutputSignal("capOnBottleAtPos1", "RotaryTableControllerCD", 40001),
            OutputSignal("move2NextPos", "RotaryTableControllerCD", 40001, oneShot=True),
        ]

        iSigRotary: list[InputSignal] = [
            InputSignal("rotaryTableTrigger", "RotaryTableModel", 41001),
            InputSignal("rotaryIdle", "Coordinator", 41001),
        ]

        def move2NextSimulator(signal: OutputSignal):
            signal.changeStatus(False)

        simulatorEvent: list = [
            None,
            None,
            None,
            (move2NextSimulator, oSigRotary[0])
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

        conveyorCdCard = self.createCdCardByIOSignal(iSigConveyor, oSigConveyor)
        self.rotaryAndConveyorInterface.addCdCard(conveyorCdCard)

    def initFillerABCDInterfaces(self):
        oSigFillerA, iSigFillerA = createFillerSignal('A', 41002, 40002)
        oSigFillerB, iSigFillerB = createFillerSignal('B', 41003, 40003)
        oSigFillerC, iSigFillerC = createFillerSignal('C', 41004, 40004)
        oSigFillerD, iSigFillerD = createFillerSignal('D', 41005, 40005)

        fillerACdCard = self.createCdCardByIOSignal(iSigFillerA, oSigFillerA)
        self.fillerAInterface.addCdCard(fillerACdCard)

        fillerBCdCard = self.createCdCardByIOSignal(iSigFillerB, oSigFillerB)
        self.fillerBInterface.addCdCard(fillerBCdCard)

        fillerCCdCard = self.createCdCardByIOSignal(iSigFillerC, oSigFillerC)
        self.fillerCInterface.addCdCard(fillerCCdCard)

        fillerDCdCard = self.createCdCardByIOSignal(iSigFillerD, oSigFillerD)
        self.fillerDInterface.addCdCard(fillerDCdCard)

    def initCappeerInterface(self):
        oSigCapper: list[OutputSignal] = [
            OutputSignal("bottleAtPos4", "CapperControllerCD", 40006),
            OutputSignal("gripperZAxisLowered", "CapperControllerCD", 40006),
            OutputSignal("gripperZAxisLifted", "CapperControllerCD", 40006),
            OutputSignal("gripperTurnHomePos", "CapperControllerCD", 40006),
            OutputSignal("gripperTurnFinalPos", "CapperControllerCD", 40006),
            OutputSignal("capperDoProcess", "CapperControllerCD", 40006, oneShot=True),
        ]

        iSigCapper: list[InputSignal] = [
            InputSignal("cylPos5ZaxisExtend", "CapperModel", 41006),
            InputSignal("gripperTurnRetract", "CapperModel", 41006),
            InputSignal("gripperTurnExtend", "CapperModel", 41006),
            InputSignal("capGripperPos5Extend", "CapperModel", 41006),
            InputSignal("cylClampBottleExtend", "CapperModel", 41006),
            InputSignal("capperIdle", "Coordinator", 41006),
        ]

        capperCdCard = self.createCdCardByIOSignal(iSigCapper, oSigCapper)
        self.capperInterface.addCdCard(capperCdCard)

    def initInterfaces(self):
        self.initRotaryAndConveyorInterface()
        self.initFillerABCDInterfaces()
        self.initCappeerInterface()

    @Slot(SignalBase)
    def updateStatusLight(self, sb: SignalBase):
        for light in self.globalStatusLights:
            if light.label.text() == sb.name:
                light.setStatus(sb.status)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()
