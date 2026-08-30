# Physicshower

一个面向初中物理教学的电路绘制与仿真工具。用户可以在画布上放置电路元件、用导线连接成电路，程序会自动求解并显示各元件的电流、电压示数。A physics circuit drawing and simulation tool for middle school physics education.

## 功能特点 Features

- **丰富的电路元件 Circuit Components**：电池（3V / 内阻 0.5Ω）、电池组（6V / 内阻 1.0Ω）、开关、灯泡、定值电阻、电流表、电压表 Cell(3V/0.5Ω), Battery(6V/1.0Ω), Switch, Light, Resistor, Current Meter, Voltage Meter
- **自由绘制电路 Circuit Drawing**：点击面板元件添加至画布，按住右键拖拽连接导线（导线严格水平/垂直）Click a component on the panel to add it to the canvas, then hold the right mouse button and drag to connect wires (wires are strictly horizontal/vertical)
- **自动仿真 Automatic Simulation**：元件移动、开关切换、导线增删后自动重新求解电路 The circuit is re-solved automatically after components are moved, switches are toggled, or wires are added/removed
- **实时示数 Real-time Readings**：电流表、电压表显示仿真读数，灯泡亮度随实际功率变化 Ammeters and voltmeters display simulation readings; bulb brightness changes with actual power
- **短路提醒 Short Circuit Warning**：电池短路（或负载过大）时元件变为橙色警示，不会弹窗打断操作 When the battery is short-circuited (or the load is too large), the component turns orange as a warning, without any pop-up interrupting the operation
- **开关交互 Switch Interaction and Dragging**：单击切换开/闭状态，拖拽仅移动位置 Single-click toggles the open/closed state; dragging only moves the position
- **属性窗口 Property Window**：点击元件显示其参数，如电阻值、电压等，支持直接修改 Click a component to view its parameters such as resistance and voltage, with direct editing supported

## 电路求解原理 Circuit Solving

采用改进节点分析法（Modified Nodal Analysis, MNA），基于 numpy 求解线性方程组，支持含内阻电源、串并联混联电路。
Uses Modified Nodal Analysis (MNA) to solve the linear equation system with numpy, supporting power sources with internal resistance and series/parallel mixed circuits.

## 环境要求 Requirements

- Python 3.11+
- PySide6
- numpy

## 安装与运行 Installation & Running

```bash
pip install PySide6 numpy
python main.py
```

## 打包为可执行文件 Packaging

```bash
pip install pyinstaller
pyinstaller physicshower.spec
```

打包产物位于 `dist/physicshower.exe`。
The packaged executable is located at `dist/physicshower.exe`.

## 项目结构 Project Structure

```
physicshower/
├── main.py        # 主程序入口，主窗口布局与仿真调度 / entry point, main window layout & simulation scheduling
├── canvas.py      # 电路画布：元件管理、导线连接、节点识别 / circuit canvas: component management, wire connection, node detection
├── components.py  # 电路元件定义（基类及各元件的绘制与交互） / component definitions (base class, drawing & interaction)
├── panel.py       # 右侧元件选择面板 / right-side component panel
└── solver.py      # 电路求解器（MNA + numpy） / circuit solver (MNA + numpy)
```

## 使用说明 Usage

1. 点击右侧面板中的元件按钮，将其添加到画布 Click a component button on the right panel to add it to the canvas
2. 在画布空白处按住鼠标右键拖拽，从元件端口拉出导线 Hold the right mouse button on an empty area and drag to pull a wire out from a component port
3. 拖动元件调整位置，导线会自动跟随 Drag a component to reposition it; the wires follow automatically
4. 单击开关可切换通断状态 Single-click a switch to toggle its on/off state
5. 电路变化后自动刷新仿真，观察各元件示数 The simulation refreshes automatically after circuit changes; observe each component's reading
