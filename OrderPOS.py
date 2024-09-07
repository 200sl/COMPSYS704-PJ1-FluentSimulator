import json
import enum
import os
from PySide6.QtCore import QObject, Signal


class OrderStatus(enum.Enum):
    WAITING = "WAITING"
    PRODUCING = "PRODUCING"
    COMPLETED = "COMPLETED"


def orderClassSerializer(order):
    if isinstance(order, Order):
        return order.toDict()
    elif isinstance(order, OrderRecipe):
        return order.toDict()
    else:
        dec = json.JSONEncoder()
        return dec.default(order)


class OrderRecipe:
    def __init__(self, liqType, capacity):
        self.liqType: str = liqType
        self.capacity: float = capacity

    def toDict(self):
        return {
            "liqType": self.liqType,
            "capacity": self.capacity
        }


class Order:
    def __init__(self, orderId, name, desc, bottleSizeInMilliL, count,
                 recipe=None, orderStatus="WAITING", producedAmount=0):
        self.producedAmount = producedAmount
        self.orderStatus = orderStatus
        self.orderId = orderId
        self.name = name
        self.desc = desc
        self.bottleSizeInMilliL = bottleSizeInMilliL
        self.count = count

        self.recipe = [] if recipe is None else recipe

    def addRecipe(self, recipe: OrderRecipe):
        self.recipe.append(recipe)

    def toDict(self):
        myDict = {
            "orderId": self.orderId,
            "name": self.name,
            "desc": self.desc,
            "bottleSizeInMilliL": self.bottleSizeInMilliL,
            "count": self.count,
            "orderStatus": self.orderStatus,
            "producedAmount": self.producedAmount
        }

        if len(self.recipe) > 0:
            myDict["recipe"] = [recipe.toDict() for recipe in self.recipe]

        return myDict

    def toJson(self) -> str:
        return json.dumps(self.toDict(), separators=(',', ':'))


class OrderDao:
    ORDER_DATA_FILE = "./orderData.json"

    class OrderDaoSignalManager(QObject):
        sigOrderListChanged = Signal()

    def __init__(self):
        self.orderList: list[Order] = []
        self.sigMngr = self.OrderDaoSignalManager()
        self.loadOrderList()

    def addOrder(self, oneOrder: Order):
        oneOrder.orderId = len(self.orderList) + 1
        self.orderList.append(oneOrder)
        self.sigMngr.sigOrderListChanged.emit()
        self.saveOrderList()

    def getOrderList(self):
        return self.orderList

    def getOrderIdList(self):
        return [str(order.orderId) for order in self.orderList]

    def getOrderById(self, orderId):
        for oneOrder in self.orderList:
            if oneOrder.orderId == orderId:
                return oneOrder
        return None

    def clearAll(self):
        self.orderList = []
        self.sigMngr.sigOrderListChanged.emit()
        self.saveOrderList()

    def updateOrder(self, oneOrder: Order):
        for i in range(len(self.orderList)):
            if self.orderList[i].orderId == oneOrder.orderId:
                self.orderList[i] = oneOrder
                self.sigMngr.sigOrderListChanged.emit()
                self.saveOrderList()
                return True

        return False

    def saveOrderList(self):
        if os.path.exists(self.ORDER_DATA_FILE):
            os.remove(self.ORDER_DATA_FILE)

        with open(self.ORDER_DATA_FILE, "w") as f:
            s = json.dumps(self.orderList, default=orderClassSerializer, indent=2)
            f.write(s)

    def loadOrderList(self):
        if not os.path.exists(self.ORDER_DATA_FILE):
            self.orderList = []
            return

        with open(self.ORDER_DATA_FILE, "r") as f:
            allText = f.read()
            if len(allText) == 0:
                self.orderList = []
                return

            orderJsonList = json.loads(allText)

            for oneJsonDict in orderJsonList:
                oneOrder = Order(0, "", "", 0, 0)
                oneOrder.orderId = oneJsonDict["orderId"]
                oneOrder.name = oneJsonDict["name"]
                oneOrder.desc = oneJsonDict["desc"]
                oneOrder.producedAmount = oneJsonDict["producedAmount"]
                oneOrder.bottleSizeInMilliL = oneJsonDict["bottleSizeInMilliL"]
                oneOrder.count = oneJsonDict["count"]

                for recipe in oneJsonDict["recipe"]:
                    oneOrder.addRecipe(OrderRecipe(recipe["liqType"], recipe["capacity"]))

                oneOrder.orderStatus = oneJsonDict["orderStatus"]

                self.orderList.append(oneOrder)


class UpdateOrderDto:
    def __init__(self, bottleId, orderId, bottleIndex, orderAmount):
        self.bottleId = bottleId
        self.orderId = orderId
        self.bottleIndex = bottleIndex
        self.orderAmount = orderAmount


if __name__ == '__main__':
    recipe1 = OrderRecipe("cola", 50)
    recipe2 = OrderRecipe("fanta", 150)

    order1 = Order(1, "cola", "cola desc", 500, 10, [recipe1, recipe2])
    order2 = Order(2, "fanta", "fanta desc", 500, 10, [recipe1, recipe2])

    orderDao = OrderDao()
    orderDao.addOrder(order1)
    orderDao.addOrder(order2)

    orderDao.clearAll()

    orderDao.saveOrderList()
