"""
电路元件定义 - 基于集总参数模型
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QFont
import math


class Port:
    """端口对象，用于 solver 中通过 id() 识别节点"""
    def __init__(self, local_pos: QPointF, owner=None):
        self.local_pos = local_pos
        self.owner = owner  # 所属元件


# 默认电气参数
DEFAULT_PARAMS = {
    "battery":   {"emf": 3.0, "internal_r": 0.5},
    "battery_pack": {"emf": 6.0, "internal_r": 1.0},  # 两个电池串联
    "switch":    {},
    "bulb":      {"resistance": 10.0},
    "resistor":  {"resistance": 10.0},
    "rheostat":  {"resistance": 10.0, "position": 50.0},
    "ammeter":   {"resistance": 1e-6},
    "voltmeter": {"resistance": 1e9}
}


class CircuitComponent(QGraphicsItem):
    """电路元件基类"""

    def __init__(self, comp_type: str, pos: QPointF, width=60, height=40):
        super().__init__()
        self.comp_type = comp_type
        self.setPos(pos)
        self.width = width
        self.height = height

        # 开关状态
        self.switch_closed = False
        self._press_pos = None

        # 电气参数（可修改）
        self.params = dict(DEFAULT_PARAMS.get(comp_type, {}))

        # 仿真结果（由 solver 写入）
        self.sim_current = 0.0   # 流过元件的电流（A）
        self.sim_voltage = 0.0   # 元件两端电压（V）
        self.sim_warning = False # 是否处于短路警告状态

        # 端口对象（solver 通过 id() 识别节点）
        self.left_port = Port(self.get_left_port(), self)
        self.right_port = Port(self.get_right_port(), self)

        # 画布引用（用于通知导线更新）
        self.canvas = None

        # 启用交互
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def boundingRect(self):
        return QRectF(-self.width/2, -self.height/2, self.width, self.height)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 更新端口本地坐标
            self.left_port.local_pos = self.get_left_port()
            self.right_port.local_pos = self.get_right_port()
            if self.canvas is not None:
                self.canvas.update_wires_for_component(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = self.mapToScene(event.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            release_pos = self.mapToScene(event.pos())
            moved = (release_pos - self._press_pos).manhattanLength()
            if moved < 5 and self.comp_type == "switch":
                self.switch_closed = not self.switch_closed
                self.update()
                self.canvas.schedule_simulate()
        self._press_pos = None
        super().mouseReleaseEvent(event)

    # ── 端口坐标（局部坐标系）──────────────────────────────
    def get_left_port(self) -> QPointF:
        if self.comp_type == "rheostat":
            # 滑动变阻器左端点：下方长方形左侧
            return QPointF(-self.width/2, self.height/4)
        return QPointF(-self.width/2, 0)

    def get_right_port(self) -> QPointF:
        if self.comp_type == "rheostat":
            # 滑动变阻器右端点：上方箭头右侧
            return QPointF(self.width/2, -self.height/4)
        return QPointF(self.width/2, 0)

    def get_left_port_scene_pos(self) -> QPointF:
        return self.mapToScene(self.get_left_port())

    def get_right_port_scene_pos(self) -> QPointF:
        return self.mapToScene(self.get_right_port())

    # ── 主绘制 ──────────────────────────────────────────────
    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        rect = self.boundingRect()

        if self.comp_type == "battery":
            self.draw_battery(painter, rect)
        elif self.comp_type == "battery_pack":
            self.draw_battery_pack(painter, rect)
        elif self.comp_type == "switch":
            self.draw_switch(painter, rect)
        elif self.comp_type == "bulb":
            self.draw_bulb(painter, rect)
        elif self.comp_type == "resistor":
            self.draw_resistor(painter, rect)
        elif self.comp_type == "rheostat":
            self.draw_rheostat(painter, rect)
        elif self.comp_type == "ammeter":
            self.draw_meter(painter, rect, "A")
        elif self.comp_type == "voltmeter":
            self.draw_meter(painter, rect, "V")

    # ── 各元件绘制 ──────────────────────────────────────────
    def draw_battery(self, painter: QPainter, rect: QRectF):
        center = rect.center()
        # 短路警告：橙色填充
        if self.sim_warning:
            painter.setPen(QPen(QColor(255, 140, 0), 2))  # 橙色边框
            painter.setBrush(QBrush(QColor(255, 165, 0)))  # 橙色填充
            painter.drawRect(rect)
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        # 正极（长线）
        painter.drawLine(center.x() - 5, center.y() - 15,
                         center.x() - 5, center.y() + 15)
        # 负极（短线）
        painter.drawLine(center.x() + 5, center.y() - 8,
                         center.x() + 5, center.y() + 8)
        # 标注
        """text_font = QFont()
        text_font.setPointSize(4)
        painter.setFont(text_font)
        painter.setPen(QPen(QColor(180, 0, 0), 1))
        painter.drawText(rect.adjusted(0, 0, 0, 0),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                         f"+ {self.params.get('emf', 3.0):.1f}V")
        painter.setPen(QPen(QColor(0, 0, 0), 2))"""

    def draw_battery_pack(self, painter: QPainter, rect: QRectF):
        """绘制电池组（两个电池串联）"""
        center = rect.center()
        # 短路警告：橙色填充
        if self.sim_warning:
            painter.setPen(QPen(QColor(255, 140, 0), 2))
            painter.setBrush(QBrush(QColor(255, 165, 0)))
            painter.drawRect(rect)
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        # 第一个电池（左侧）
        painter.drawLine(center.x() - 15, center.y() - 15,
                         center.x() - 15, center.y() + 15)  # 正极（长线）
        painter.drawLine(center.x() - 5, center.y() - 8,
                         center.x() - 5, center.y() + 8)    # 负极（短线）
        # 第二个电池（右侧）
        painter.drawLine(center.x() + 5, center.y() - 15,
                         center.x() + 5, center.y() + 15)   # 正极（长线）
        painter.drawLine(center.x() + 15, center.y() - 8,
                         center.x() + 15, center.y() + 8)   # 负极（短线）

    def draw_switch(self, painter: QPainter, rect: QRectF):
        center = rect.center()
        painter.drawEllipse(QPointF(center.x() - 15, center.y()), 3, 3)
        painter.drawEllipse(QPointF(center.x() + 15, center.y()), 3, 3)
        if self.switch_closed:
            painter.drawLine(center.x() - 15, center.y(),
                             center.x() + 15, center.y())
        else:
            painter.drawLine(center.x() - 15, center.y(),
                             center.x() + 13, center.y() - 10)

    def draw_bulb(self, painter: QPainter, rect: QRectF):
        center = rect.center()
        # 根据功率计算亮度（P = I²R，归一化到 0~1）
        R = self.params.get('resistance', 10.0)
        P = self.sim_current ** 2 * R if R > 0 else 0.0
        brightness = min(P / 2.0, 1.0)  # 2W 为满亮度

        # 发光圆（亮度越高越黄）
        if brightness > 0.01:
            glow_color = QColor(255, 255, 0, int(brightness * 220))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(center, 14, 14)
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # 灯泡圆形
        painter.drawEllipse(center, 12, 12)
        # 叉丝
        painter.drawLine(center.x() - 8, center.y() - 8,
                         center.x() + 8, center.y() + 8)
        painter.drawLine(center.x() - 8, center.y() + 8,
                         center.x() + 8, center.y() - 8)
        # 功率标注
        """if brightness > 0.01:
            text_font = QFont()
            text_font.setPointSize(6)
            painter.setFont(text_font)
            painter.setPen(QPen(QColor(180, 100, 0), 1))
            painter.drawText(rect.adjusted(0, 14, 0, 10),
                             Qt.AlignmentFlag.AlignHCenter,
                             f"{P:.2f}W")
            painter.setPen(QPen(QColor(0, 0, 0), 2))"""

    def draw_resistor(self, painter: QPainter, rect: QRectF):
        center = rect.center()
        painter.drawRect(QRectF(center.x() - 20, center.y() - 8, 40, 16))
        # 阻值标注
        R = self.params.get('resistance', 10.0)
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawText(rect.adjusted(0, 0, 0, 0),
                         Qt.AlignmentFlag.AlignCenter,
                         f"{R:.0f}Ω")
        painter.setPen(QPen(QColor(0, 0, 0), 2))

    def draw_rheostat(self, painter: QPainter, rect: QRectF):
        """绘制滑动变阻器：下方长方形 + 上方箭头"""
        center = rect.center()
        position = self.params.get('position', 50.0)
        
        # 下方长方形（电阻体）
        rect_y = center.y() + self.height/4
        painter.drawRect(QRectF(center.x() - 20, rect_y - 6, 40, 16))
        
        # 箭头水平位置随 position 变化（0%最左，100%最右）
        arrow_x = center.x() - 17 + (position / 100.0) * 34
        arrow_y = center.y() - self.height/4
        
        # 连接线（从箭头位置到电阻体）
        painter.drawLine(arrow_x, arrow_y, arrow_x, rect_y - 6)
        # 箭头头部
        painter.drawLine(arrow_x, rect_y - 6, arrow_x + 3, rect_y - 12)
        painter.drawLine(arrow_x, rect_y - 6, arrow_x - 3, rect_y - 12)
        painter.drawLine(arrow_x, arrow_y, 20, arrow_y)
        # 阻值标注
        R = self.params.get('resistance', 10.0)
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawText(rect.adjusted(0, -25, 0, 0),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                         f"{R:.0f}Ω")
        painter.setPen(QPen(QColor(0, 0, 0), 2))

    def draw_meter(self, painter: QPainter, rect: QRectF, label: str):
        center = rect.center()
        # 表盘背景
        if label == "A":
            bg_color = QColor(230, 245, 255)  # 电流表浅蓝
        else:
            bg_color = QColor(255, 245, 230)  # 电压表浅橙
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(bg_color))
        painter.drawEllipse(center, 18, 18)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 标签（小字，在顶部）
        small_font = QFont()
        small_font.setPointSize(7)
        painter.setFont(small_font)
        painter.drawText(QRectF(center.x()-6, center.y()-17, 12, 10),
                         Qt.AlignmentFlag.AlignCenter, label)

        # 示数（大字，在中心）
        normal_font = QFont()
        normal_font.setPointSize(7)
        normal_font.setBold(True)
        painter.setFont(normal_font)
        if label == "A":
            val = self.sim_current
            unit = "A"
        else:
            val = self.sim_voltage
            unit = "V"
        if abs(val) > 1e-6:
            text = f"{val:.2f}{unit}"
        else:
            text = "0"
        painter.setPen(QPen(QColor(180, 0, 0)))
        painter.drawText(QRectF(center.x()-16, center.y()-4, 32, 14),
                         Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        normal_font.setBold(False)
        painter.setFont(normal_font)


def create_component(comp_type: str, pos: QPointF) -> CircuitComponent:
    """工厂函数：创建元件"""
    widths = {
        "battery":   10,
        "battery_pack": 30,
        "switch":    36,
        "bulb":      24,
        "resistor":  40,
        "rheostat":  40,
        "ammeter":   36,
        "voltmeter": 36
    }
    width = widths.get(comp_type, 60)
    return CircuitComponent(comp_type, pos, width=width)
