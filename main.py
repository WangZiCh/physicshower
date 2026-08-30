"""
physicshower程序 - 主程序入口
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMessageBox, QLabel
from PySide6.QtCore import Qt
from canvas import CircuitCanvas
from panel import ComponentPanel


class MainWindow(QMainWindow):
    """主窗口：左侧画布 + 右侧物品栏"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Physicshower")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 左侧：电路画布
        self.canvas = CircuitCanvas()
        layout.addWidget(self.canvas, stretch=3)  # 画布占 3/4 空间
        
        # 右侧：垂直布局（元件面板 + 仿真按钮）
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # 元件面板
        self.panel = ComponentPanel(self.canvas)
        right_layout.addWidget(self.panel, stretch=1)
        
        # 操作提示
        tip_label = QLabel("点击元件以添加至电路，按住右键以连接导线")
        tip_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: #888888;
                font-size: 11px;
                padding: 8px;
                border-radius: 3px;
            }
        """)
        tip_label.setWordWrap(True)
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(tip_label)
        
        # 仿真按钮
        self.simulate_btn = QPushButton("刷新🔄️")
        self.simulate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.simulate_btn.clicked.connect(self.run_simulation)
        right_layout.addWidget(self.simulate_btn)
        
        # 清空按钮
        self.clear_btn = QPushButton("🗑 清空画布")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
        """)
        self.clear_btn.clicked.connect(self.canvas.clear_canvas)
        right_layout.addWidget(self.clear_btn)
        
        layout.addWidget(right_panel, stretch=1)
        
        # 连接信号：从面板拖拽元件到画布
        self.panel.component_selected.connect(self.canvas.add_component)
        
        # 连接信号：电路变化时自动运行仿真
        self.canvas.circuit_changed.connect(self.run_simulation)
    
    def run_simulation(self):
        """运行电路仿真"""
        warnings = self.canvas.simulate()
        
        if warnings:
            warning_text = "\n".join(warnings)
            print("仿真警告:", warning_text)
        else:
            #QMessageBox.information(self, "仿真完成", "电路仿真已完成！\n请查看各元件的示数。")
            print("仿真完成")



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 样式
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
