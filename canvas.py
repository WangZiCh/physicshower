"""
电路画布 - 用于绘制和交互电路元件
"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QMessageBox
from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QAction
from components import CircuitComponent


# 端口检测的阈值距离（像素）
PORT_SNAP_DISTANCE = 5


class BatteryPropertyDialog(QDialog):
    """电池属性编辑对话框"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("电池属性")
        self.setFixedSize(300, 180)
        
        layout = QVBoxLayout(self)
        
        # 电流显示（只读）
        current_layout = QHBoxLayout()
        current_label = QLabel("电流 (A):")
        self.current_value = QLabel(f"{component.sim_current:.3f}")
        current_layout.addWidget(current_label)
        current_layout.addWidget(self.current_value)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 电压输入
        voltage_layout = QHBoxLayout()
        voltage_label = QLabel("电压 (V):")
        self.voltage_spin = QDoubleSpinBox()
        self.voltage_spin.setRange(0.001, 999.0)
        self.voltage_spin.setDecimals(3)
        self.voltage_spin.setMinimum(0.001)
        self.voltage_spin.setValue(component.params.get('emf', 3.0))
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(self.voltage_spin)
        layout.addLayout(voltage_layout)
        
        # 内阻输入
        resistance_layout = QHBoxLayout()
        resistance_label = QLabel("内阻 (Ω):")
        self.resistance_spin = QDoubleSpinBox()
        self.resistance_spin.setRange(0.001, 999.0)
        self.resistance_spin.setDecimals(3)
        self.resistance_spin.setMinimum(0.001)
        self.resistance_spin.setValue(component.params.get('internal_r', 0.5))
        resistance_layout.addWidget(resistance_label)
        resistance_layout.addWidget(self.resistance_spin)
        layout.addLayout(resistance_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_values(self):
        """返回编辑后的电压和内阻"""
        return self.voltage_spin.value(), self.resistance_spin.value()


class BulbPropertyDialog(QDialog):
    """灯泡属性编辑对话框"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("灯泡属性")
        self.setFixedSize(300, 210)
        
        layout = QVBoxLayout(self)
        
        # 电流显示（只读）
        current_layout = QHBoxLayout()
        current_label = QLabel("电流 (A):")
        current_value = QLabel(f"{component.sim_current:.3f}")
        current_layout.addWidget(current_label)
        current_layout.addWidget(current_value)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 电压显示（只读）
        voltage_layout = QHBoxLayout()
        voltage_label = QLabel("电压 (V):")
        voltage_value = QLabel(f"{component.sim_voltage:.3f}")
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(voltage_value)
        voltage_layout.addStretch()
        layout.addLayout(voltage_layout)
        
        # 功率显示（只读）
        power_layout = QHBoxLayout()
        power_label = QLabel("功率 (W):")
        power = component.sim_current ** 2 * component.params.get('resistance', 10.0)
        power_value = QLabel(f"{power:.3f}")
        power_layout.addWidget(power_label)
        power_layout.addWidget(power_value)
        power_layout.addStretch()
        layout.addLayout(power_layout)
        
        # 电阻输入
        resistance_layout = QHBoxLayout()
        resistance_label = QLabel("电阻 (Ω):")
        self.resistance_spin = QDoubleSpinBox()
        self.resistance_spin.setRange(0.001, 999.0)
        self.resistance_spin.setDecimals(3)
        self.resistance_spin.setMinimum(0.001)
        self.resistance_spin.setValue(component.params.get('resistance', 10.0))
        resistance_layout.addWidget(resistance_label)
        resistance_layout.addWidget(self.resistance_spin)
        layout.addLayout(resistance_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_resistance(self):
        """返回编辑后的电阻"""
        return self.resistance_spin.value()


class SwitchPropertyDialog(QDialog):
    """开关只读属性对话框"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("开关属性")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # 状态显示（只读）
        state_layout = QHBoxLayout()
        state_label = QLabel("状态:")
        state_value = QLabel("闭合" if component.switch_closed else "断开")
        state_layout.addWidget(state_label)
        state_layout.addWidget(state_value)
        state_layout.addStretch()
        layout.addLayout(state_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)


class MeterPropertyDialog(QDialog):
    """电表只读属性对话框（电流表/电压表）"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("电表属性")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # 电流显示（只读）
        current_layout = QHBoxLayout()
        current_label = QLabel("电流 (A):")
        current_value = QLabel(f"{component.sim_current:.6f}")
        current_layout.addWidget(current_label)
        current_layout.addWidget(current_value)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 电压显示（只读）
        voltage_layout = QHBoxLayout()
        voltage_label = QLabel("电压 (V):")
        voltage_value = QLabel(f"{component.sim_voltage:.6f}")
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(voltage_value)
        voltage_layout.addStretch()
        layout.addLayout(voltage_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)


class ResistorPropertyDialog(QDialog):
    """电阻属性编辑对话框"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("电阻属性")
        self.setFixedSize(300, 210)
        
        layout = QVBoxLayout(self)
        
        # 电流显示（只读）
        current_layout = QHBoxLayout()
        current_label = QLabel("电流 (A):")
        current_value = QLabel(f"{component.sim_current:.3f}")
        current_layout.addWidget(current_label)
        current_layout.addWidget(current_value)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 电压显示（只读）
        voltage_layout = QHBoxLayout()
        voltage_label = QLabel("电压 (V):")
        voltage_value = QLabel(f"{component.sim_voltage:.3f}")
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(voltage_value)
        voltage_layout.addStretch()
        layout.addLayout(voltage_layout)
        
        # 功率显示（只读）
        power_layout = QHBoxLayout()
        power_label = QLabel("功率 (W):")
        power = component.sim_current ** 2 * component.params.get('resistance', 10.0)
        power_value = QLabel(f"{power:.3f}")
        power_layout.addWidget(power_label)
        power_layout.addWidget(power_value)
        power_layout.addStretch()
        layout.addLayout(power_layout)
        
        # 电阻输入
        resistance_layout = QHBoxLayout()
        resistance_label = QLabel("电阻 (Ω):")
        self.resistance_spin = QDoubleSpinBox()
        self.resistance_spin.setRange(0.001, 999.0)
        self.resistance_spin.setDecimals(3)
        self.resistance_spin.setMinimum(0.001)
        self.resistance_spin.setValue(component.params.get('resistance', 10.0))
        resistance_layout.addWidget(resistance_label)
        resistance_layout.addWidget(self.resistance_spin)
        layout.addLayout(resistance_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_resistance(self):
        """返回编辑后的电阻"""
        return self.resistance_spin.value()


class RheostatPropertyDialog(QDialog):
    """滑动变阻器属性编辑对话框"""
    
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.component = component
        self.setWindowTitle("滑动变阻器属性")
        self.setFixedSize(300, 210)
        
        layout = QVBoxLayout(self)
        
        # 电流显示（只读）
        current_layout = QHBoxLayout()
        current_label = QLabel("电流 (A):")
        current_value = QLabel(f"{component.sim_current:.3f}")
        current_layout.addWidget(current_label)
        current_layout.addWidget(current_value)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # 电压显示（只读）
        voltage_layout = QHBoxLayout()
        voltage_label = QLabel("电压 (V):")
        voltage_value = QLabel(f"{component.sim_voltage:.3f}")
        voltage_layout.addWidget(voltage_label)
        voltage_layout.addWidget(voltage_value)
        voltage_layout.addStretch()
        layout.addLayout(voltage_layout)
        
        # 功率显示（只读）
        power_layout = QHBoxLayout()
        power_label = QLabel("功率 (W):")
        power = component.sim_current ** 2 * component.params.get('resistance', 10.0)
        power_value = QLabel(f"{power:.3f}")
        power_layout.addWidget(power_label)
        power_layout.addWidget(power_value)
        power_layout.addStretch()
        layout.addLayout(power_layout)
        
        # 总电阻输入
        resistance_layout = QHBoxLayout()
        resistance_label = QLabel("总电阻 (Ω):")
        self.resistance_spin = QDoubleSpinBox()
        self.resistance_spin.setRange(0.001, 999.0)
        self.resistance_spin.setDecimals(3)
        self.resistance_spin.setMinimum(0.001)
        self.resistance_spin.setValue(component.params.get('resistance', 10.0))
        resistance_layout.addWidget(resistance_label)
        resistance_layout.addWidget(self.resistance_spin)
        layout.addLayout(resistance_layout)
        
        # 滑动变阻器位置输入（百分比）
        position_layout = QHBoxLayout()
        position_label = QLabel("位置 (%):")
        self.position_spin = QDoubleSpinBox()
        self.position_spin.setRange(0.0, 100.0)
        self.position_spin.setDecimals(1)
        self.position_spin.setValue(component.params.get('position', 50.0))
        position_layout.addWidget(position_label)
        position_layout.addWidget(self.position_spin)
        layout.addLayout(position_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_values(self):
        """返回编辑后的总电阻和位置"""
        return self.resistance_spin.value(), self.position_spin.value()


class WireItem(QGraphicsPathItem):
    """导线，横平竖直的折线，跟随元件移动"""
    
    def __init__(self, start_comp, start_port, end_comp, end_port):
        super().__init__()
        self.start_comp = start_comp
        self.start_port = start_port  # 'left' 或 'right'
        self.end_comp = end_comp
        self.end_port = end_port      # 'left' 或 'right'
        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)  # 导线在元件下方，避免遮挡点击
        self.update_position()
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除导线")
        
        action = menu.exec(event.screenPos())
        if action == delete_action:
            # 从画布中删除此导线
            scene = self.scene()
            if scene and hasattr(scene, 'views') and scene.views():
                canvas = scene.views()[0]
                if hasattr(canvas, 'delete_wire'):
                    canvas.delete_wire(self)
    
    def _port_pos(self, comp, port_type):
        if port_type == 'left':
            return comp.get_left_port_scene_pos()
        return comp.get_right_port_scene_pos()
    
    def update_position(self):
        """根据当前元件位置更新导线（横平竖直）"""
        start = self._port_pos(self.start_comp, self.start_port)
        end = self._port_pos(self.end_comp, self.end_port)
        
        # 创建横平竖直的路径
        path = QPainterPath()
        path.moveTo(start)
        
        # 根据端口类型决定初始方向
        # 右端口：先向右走一段，再垂直，最后水平到终点
        # 左端口：先向左走一段，再垂直，最后水平到终点
        
        offset = 10  # 离开元件的初始距离
        
        if self.start_port == 'right':
            # 从右端口出发，先向右
            p1 = QPointF(start.x() + offset, start.y())
            path.lineTo(p1)
            
            if self.end_port == 'left':
                # 到左端口，先垂直到终点高度，再水平进入
                if end.x()-offset < start.x()+offset:
                    if abs(end.y() - start.y()) >40 or end.x() > start.x():
                        p2 = QPointF(p1.x(), (end.y()+start.y())/2)
                        path.lineTo(p2)
                        p3 = QPointF(end.x() - offset, p2.y())
                        path.lineTo(p3)
                        p4 = QPointF(p3.x(), end.y())
                        path.lineTo(p4)
                    else:
                        p2 = QPointF(p1.x(), max(end.y(), p1.y())+20)
                        path.lineTo(p2)
                        p3 = QPointF(end.x() - offset, p2.y())
                        path.lineTo(p3)
                        p4 = QPointF(p3.x(), end.y())
                        path.lineTo(p4)
                else:
                    p2 = QPointF((start.x() + end.x())/2, p1.y())
                    path.lineTo(p2)
                    p3 = QPointF(p2.x(), end.y())
                    path.lineTo(p3)
                    p4 = QPointF(end.x() - offset, end.y())
                    path.lineTo(p4)
            else:
                # 到右端口，先垂直到终点高度，再水平进入
                p2 = QPointF(max(p1.x(), end.x() + offset), p1.y())
                path.lineTo(p2)
                p3 = QPointF(p2.x(), end.y())
                path.lineTo(p3)
                p4 = QPointF(end.x() + offset, end.y())
                path.lineTo(p4)
        else:  # start_port == 'left'
            # 从左端口出发，先向左
            p1 = QPointF(start.x() - offset, start.y())
            path.lineTo(p1)
            
            if self.end_port == 'right':
                if end.x()+offset > start.x()-offset:
                    if abs(end.y() - start.y()) >40 or end.x() < start.x():
                        p2 = QPointF(p1.x(), (end.y()+start.y())/2)
                        path.lineTo(p2)
                        p3 = QPointF(end.x() + offset, p2.y())
                        path.lineTo(p3)
                        p4 = QPointF(p3.x(), end.y())
                        path.lineTo(p4)
                    else:
                        p2 = QPointF(p1.x(), max(end.y(), p1.y())+20)
                        path.lineTo(p2)
                        p3 = QPointF(end.x() + offset, p2.y())
                        path.lineTo(p3)
                        p4 = QPointF(p3.x(), end.y())
                        path.lineTo(p4)
                else:
                    p2 = QPointF((start.x() + end.x())/2, p1.y())
                    path.lineTo(p2)
                    p3 = QPointF(p2.x(), end.y())
                    path.lineTo(p3)
                    p4 = QPointF(end.x() + offset, end.y())
                    path.lineTo(p4)
            else:
                # 到左端口
                p2 = QPointF(min(p1.x(), end.x() - offset), p1.y())
                path.lineTo(p2)
                p3 = QPointF(p2.x(), end.y())
                path.lineTo(p3)
                p4 = QPointF(end.x() - offset, end.y())
                path.lineTo(p4)
        
        path.lineTo(end)
        self.setPath(path)


class CircuitCanvas(QGraphicsView):
    """电路画布视图"""
    
    circuit_changed = Signal()  # 电路变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建场景
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 2000, 1500)
        self.setScene(self.scene)
        
        # 设置渲染提示 - 启用抗锯齿
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # 启用拖拽支持
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setAcceptDrops(True)
        
        # 设置背景
        self.setBackgroundBrush(QBrush(QColor(250, 250, 250)))
        
        # 存储画布上的元件和导线
        self.components = []
        self.wires = []
        
        # 右键连线状态
        self.wire_start_info = None   # (元件, 端口类型, 端口坐标)
        self.preview_line = None      # 预览导线
        
        # 自动仿真定时器
        self.sim_timer = QTimer(self)
        self.sim_timer.setSingleShot(True)
        self.sim_timer.timeout.connect(self.auto_simulate)
        
    def add_component(self, component_type: str):
        """添加元件到画布"""
        from components import create_component
        
        center = self.mapToScene(self.viewport().rect().center())
        component = create_component(component_type, center)
        
        if component:
            # 设置元件移动时通知画布更新导线
            component.canvas = self
            self.scene.addItem(component)
            self.components.append(component)
            self.schedule_simulate()  # 自动仿真
    
    def update_wires_for_component(self, comp):
        """更新与某元件相连的所有导线"""
        for wire in self.wires:
            if wire.start_comp == comp or wire.end_comp == comp:
                wire.update_position()
        #self.schedule_simulate()  # 元件移动后自动仿真
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        component_type = event.mimeData().text()
        pos = self.mapToScene(event.pos())
        
        from components import create_component
        component = create_component(component_type, pos)
        
        if component:
            component.canvas = self
            self.scene.addItem(component)
            self.components.append(component)
            self.schedule_simulate()  # 自动仿真
            event.acceptProposedAction()
    
    def find_nearest_port(self, scene_pos: QPointF):
        """查找最近的端口，返回 (元件, 端口类型, 端口坐标) 或 None"""
        best = None
        best_dist = PORT_SNAP_DISTANCE
        
        for comp in self.components:
            left_pos = comp.get_left_port_scene_pos()
            dist = (scene_pos - left_pos).manhattanLength()
            if dist < best_dist:
                best_dist = dist
                best = (comp, 'left', left_pos)
            
            right_pos = comp.get_right_port_scene_pos()
            dist = (scene_pos - right_pos).manhattanLength()
            if dist < best_dist:
                best_dist = dist
                best = (comp, 'right', right_pos)
        
        return best
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            port_info = self.find_nearest_port(scene_pos)
            
            if port_info is not None:
                comp, port_type, port_pos = port_info
                self.wire_start_info = (comp, port_type, port_pos)
                # 创建预览线
                self.preview_line = QGraphicsLineItem(
                    port_pos.x(), port_pos.y(), port_pos.x(), port_pos.y()
                )
                self.preview_line.setPen(QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine))
                self.scene.addItem(self.preview_line)
                event.accept()
                return
            super().mousePressEvent(event)
        elif event.button() == Qt.MouseButton.RightButton:
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.wire_start_info is not None and self.preview_line is not None:
            scene_pos = self.mapToScene(event.pos())
            start_pos = self.wire_start_info[2]
            self.preview_line.setLine(
                start_pos.x(), start_pos.y(),
                scene_pos.x(), scene_pos.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            # 检查端口连线
            if self.wire_start_info is not None:
                port_info = self.find_nearest_port(scene_pos)
                
                if port_info is not None:
                    start_comp, start_port_type, _ = self.wire_start_info
                    end_comp, end_port_type, _ = port_info
                    
                    if not (start_comp == end_comp and start_port_type == end_port_type):
                        wire = WireItem(start_comp, start_port_type, end_comp, end_port_type)
                        self.scene.addItem(wire)
                        self.wires.append(wire)
                        self.schedule_simulate()  # 自动仿真
                
                self.cancel_wire()
                event.accept()
                return
            super().mouseReleaseEvent(event)
        elif event.button() == Qt.MouseButton.RightButton:
            scene_pos = self.mapToScene(event.pos())
            
            # 检查是否点击在元件上
            item = self.itemAt(event.pos())
            if isinstance(item, CircuitComponent):
                # 显示元件右键菜单
                self.show_component_context_menu(item, event.pos())
                event.accept()
                return
            
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)
    
    def show_component_context_menu(self, component, pos):
        """显示元件右键菜单"""
        menu = QMenu(self)
        
        # 电池和电池组添加属性选项
        if component.comp_type in ['battery', 'battery_pack']:
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_battery_properties(component))
            menu.addAction(property_action)
        
        # 灯泡添加属性选项
        elif component.comp_type == 'bulb':
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_bulb_properties(component))
            menu.addAction(property_action)
        
        # 电阻添加属性选项
        elif component.comp_type == 'resistor':
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_resistor_properties(component))
            menu.addAction(property_action)
        
        # 滑动变阻器添加属性选项
        elif component.comp_type == 'rheostat':
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_rheostat_properties(component))
            menu.addAction(property_action)
        
        # 电流表和电压表添加属性选项（只读）
        elif component.comp_type in ['ammeter', 'voltmeter']:
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_meter_properties(component))
            menu.addAction(property_action)
        
        # 开关添加属性选项（只读）
        elif component.comp_type == 'switch':
            property_action = QAction("属性", self)
            property_action.triggered.connect(lambda: self.show_switch_properties(component))
            menu.addAction(property_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_component(component))
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def show_battery_properties(self, component):
        """显示电池属性编辑对话框"""
        dialog = BatteryPropertyDialog(component, self)
        if dialog.exec():
            emf, internal_r = dialog.get_values()
            component.params['emf'] = emf
            component.params['internal_r'] = internal_r
            self.schedule_simulate()  # 重新仿真
    
    def show_bulb_properties(self, component):
        """显示灯泡属性编辑对话框"""
        dialog = BulbPropertyDialog(component, self)
        if dialog.exec():
            resistance = dialog.get_resistance()
            component.params['resistance'] = resistance
            self.schedule_simulate()  # 重新仿真
    
    def show_resistor_properties(self, component):
        """显示电阻属性编辑对话框"""
        dialog = ResistorPropertyDialog(component, self)
        if dialog.exec():
            resistance = dialog.get_resistance()
            component.params['resistance'] = resistance
            self.schedule_simulate()  # 重新仿真
    
    def show_rheostat_properties(self, component):
        """显示滑动变阻器属性编辑对话框"""
        dialog = RheostatPropertyDialog(component, self)
        if dialog.exec():
            resistance, position = dialog.get_values()
            component.params['resistance'] = resistance
            component.params['position'] = position
            self.schedule_simulate()  # 重新仿真
    
    def show_meter_properties(self, component):
        """显示电表属性对话框（只读）"""
        dialog = MeterPropertyDialog(component, self)
        dialog.exec()
    
    def show_switch_properties(self, component):
        """显示开关属性对话框（只读）"""
        dialog = SwitchPropertyDialog(component, self)
        dialog.exec()
    
    def delete_component(self, component):
        """删除元件及其相连的导线"""
        # 删除与该元件相连的所有导线
        wires_to_remove = []
        for wire in self.wires:
            if wire.start_comp == component or wire.end_comp == component:
                self.scene.removeItem(wire)
                wires_to_remove.append(wire)
        
        for wire in wires_to_remove:
            self.wires.remove(wire)
        
        # 删除元件
        self.scene.removeItem(component)
        self.components.remove(component)
        self.schedule_simulate()  # 自动仿真
    
    def delete_wire(self, wire):
        """删除导线"""
        if wire in self.wires:
            self.scene.removeItem(wire)
            self.wires.remove(wire)
            self.schedule_simulate()  # 自动仿真
    
    def clear_canvas(self):
        """清空画布上的所有元件和导线"""
        # 删除所有导线
        for wire in self.wires[:]:
            self.scene.removeItem(wire)
        self.wires.clear()
        
        # 删除所有元件
        for component in self.components[:]:
            self.scene.removeItem(component)
        self.components.clear()
        
        # 触发仿真更新
        self.schedule_simulate()
    
    def cancel_wire(self):
        """取消当前连线操作"""
        if self.preview_line is not None:
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        self.wire_start_info = None

    def schedule_simulate(self):
        """发出电路变化信号"""
        self.circuit_changed.emit()

    def auto_simulate(self):
        """定时器触发的自动仿真（保留兼容）"""
        self.circuit_changed.emit()

    def simulate(self) -> list:
        """运行电路仿真，返回警告列表"""
        from solver import CircuitSolver

        # 重置所有元件的仿真数据
        for comp in self.components:
            comp.sim_current = 0.0
            comp.sim_voltage = 0.0
            comp.sim_warning = False

        if not self.components:
            return ["电路为空"]

        # 构建 solver 需要的导线信息
        # WireItem 的 start_port/end_port 是 'left'/'right' 字符串
        # solver 需要通过 id(port) 来识别节点
        class WireInfo:
            def __init__(self, start_port_obj, end_port_obj):
                self.start_port = start_port_obj
                self.end_port = end_port_obj

        solver_wires = []
        for wire in self.wires:
            start_port_obj = (wire.start_comp.left_port
                              if wire.start_port == 'left'
                              else wire.start_comp.right_port)
            end_port_obj = (wire.end_comp.left_port
                            if wire.end_port == 'left'
                            else wire.end_comp.right_port)
            solver_wires.append(WireInfo(start_port_obj, end_port_obj))

        solver = CircuitSolver()
        result = solver.solve(self.components, solver_wires)

        # 将结果写回元件
        for comp in self.components:
            comp_id = id(comp)
            if comp_id in result.component_currents:
                comp.sim_current = result.component_currents[comp_id]
            if comp_id in result.component_voltages:
                comp.sim_voltage = result.component_voltages[comp_id]
            # 电池短路警告
            if comp.comp_type == 'battery' and abs(comp.sim_current) > 10:
                comp.sim_warning = True
            comp.update()

        return result.warnings
