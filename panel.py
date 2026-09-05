"""
元件面板 - 右侧物品栏，显示可用的电路元件
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                                QLabel, QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag


class ComponentPanel(QWidget):
    """元件面板：显示所有可用的电路元件"""
    
    component_selected = Signal(str)  # 发射选中的元件类型
    
    def __init__(self, canvas=None, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("电路元件")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 元件容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(8)
        
        # 添加各类元件按钮
        components = [
            ("battery", "电池 🔋"),
            ("battery_pack", "电池组 🔋🔋"),
            ("switch", "开关 🔘"),
            ("bulb", "灯泡 💡"),
            ("resistor", "电阻 ⚡"),
            ("rheostat", "滑动变阻器 🎚"),
            ("ammeter", "电流表 Ⓐ"),
            ("voltmeter", "电压表 Ⓥ")
        ]
        
        for comp_type, comp_name in components:
            btn = self.create_component_button(comp_type, comp_name)
            container_layout.addWidget(btn)
        
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
    def create_component_button(self, comp_type: str, comp_name: str) -> QPushButton:
        """创建元件按钮"""
        btn = DraggableButton(comp_type, comp_name)
        btn.setMinimumHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # 点击信号 - 点击时在画布中心添加元件
        btn.clicked.connect(lambda: self.component_selected.emit(comp_type))
        
        return btn


class DraggableButton(QPushButton):
    """可拖拽的按钮"""
    
    def __init__(self, component_type, text, parent=None):
        super().__init__(text, parent)
        self.component_type = component_type
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 开始拖拽"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
            
        if (event.pos() - self.drag_start_pos).manhattanLength() < 10:
            return
            
        # 创建拖拽数据
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.component_type)
        drag.setMimeData(mime_data)
        
        # 执行拖拽
        drag.exec(Qt.DropAction.CopyAction)
