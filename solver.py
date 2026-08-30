"""
电路仿真求解器 - 基于改进节点分析法(MNA)
使用集总参数模型，符合中学物理理想电路假设
"""
import numpy as np
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class SimulationResult:
    """仿真结果"""
    node_voltages: Dict[int, float]
    component_currents: Dict[int, float]
    component_voltages: Dict[int, float]
    warnings: List[str]


class CircuitSolver:
    """电路求解器 - 使用改进节点分析法"""

    GMIN = 1e-12  # 最小电导，防止浮空节点

    def solve(self, components: list, wires: list) -> SimulationResult:
        warnings = []

        # 1. 构建端口到节点的映射
        port_to_node = self._build_node_mapping(components, wires)

        all_nodes = set(port_to_node.values())
        if not all_nodes:
            return SimulationResult({}, {}, {}, ["电路为空"])

        # 2. 选择参考节点
        ground_node = self._select_ground_node(components, port_to_node, all_nodes)

        # 3. 识别电压源（电池和电池组）
        voltage_sources = [c for c in components if c.comp_type in ['battery', 'battery_pack']]
        n_vs = len(voltage_sources)

        # 4. 为每个电池创建内部节点（用于串联内阻模型）
        #    电池模型：理想电压源(node_p -> internal_node) + 内阻(internal_node -> node_n)
        internal_nodes = {}
        max_node_id = max(all_nodes) if all_nodes else 0
        for i, vs in enumerate(voltage_sources):
            internal_id = max_node_id + 1 + i
            internal_nodes[id(vs)] = internal_id
            all_nodes.add(internal_id)

        # 5. 构建 node_id_map: ground->0, 其他->1,2,3...
        node_list = sorted([n for n in all_nodes if n != ground_node])
        node_id_map = {ground_node: 0}
        for i, n in enumerate(node_list):
            node_id_map[n] = i + 1

        n_total = len(all_nodes)

        # 6. MNA 矩阵大小: (n_total - 1) 个节点电压 + n_vs 个电压源电流
        matrix_size = (n_total - 1) + n_vs
        if matrix_size == 0:
            return SimulationResult({}, {}, {}, ["电路没有可求解的节点"])

        G = np.zeros((matrix_size, matrix_size))
        I_vec = np.zeros(matrix_size)

        # 7. gmin 稳定化 - 防止浮空节点导致奇异矩阵
        for i in range(n_total - 1):
            G[i, i] += self.GMIN

        # 8. 填充元件导纳
        for comp in components:
            if not self._is_active_component(comp):
                continue

            node_p = port_to_node.get(id(comp.left_port))
            node_n = port_to_node.get(id(comp.right_port))
            if node_p is None or node_n is None:
                continue

            idx_p = node_id_map.get(node_p, 0)
            idx_n = node_id_map.get(node_n, 0)

            if comp.comp_type in ['resistor', 'bulb']:
                R = comp.params.get('resistance', 10.0)
                if R < 1e-9:
                    warnings.append("电阻阻值过小，可能导致短路")
                    R = 1e-9
                self._stamp_resistor(G, idx_p, idx_n, 1.0 / R)

            elif comp.comp_type == 'switch':
                # 闭合开关：极大导纳模拟零电阻
                self._stamp_resistor(G, idx_p, idx_n, 1e9)

            elif comp.comp_type == 'ammeter':
                R = comp.params.get('resistance', 1e-6)
                self._stamp_resistor(G, idx_p, idx_n, 1.0 / R)

            elif comp.comp_type == 'voltmeter':
                R = comp.params.get('resistance', 1e9)
                self._stamp_resistor(G, idx_p, idx_n, 1.0 / R)

            elif comp.comp_type in ['battery', 'battery_pack']:
                # 电池/电池组内阻：串联在 internal_node 和 node_n 之间
                internal_node_id = internal_nodes[id(comp)]
                idx_internal = node_id_map[internal_node_id]
                internal_r = comp.params.get('internal_r', 0.5)
                if internal_r > 0:
                    self._stamp_resistor(G, idx_internal, idx_n, 1.0 / internal_r)

        # 9. 填充电压源 stamp
        for i, vs in enumerate(voltage_sources):
            node_p = port_to_node.get(id(vs.left_port))
            node_n = port_to_node.get(id(vs.right_port))
            if node_p is None or node_n is None:
                continue

            idx_p = node_id_map.get(node_p, 0)
            idx_internal = node_id_map[internal_nodes[id(vs)]]

            # 短路检测
            if idx_p == idx_internal:
                warnings.append("⚠️ 电池短路！正负极直接相连")
                continue

            vs_idx = (n_total - 1) + i  # 电压源电流在矩阵中的索引

            # 电压源方程: V_p - V_internal = emf
            # MNA stamp:
            #   G[idx_p, vs_idx] = +1,  G[idx_internal, vs_idx] = -1
            #   G[vs_idx, idx_p] = +1,  G[vs_idx, idx_internal] = -1
            if idx_p > 0:
                G[idx_p - 1, vs_idx] += 1.0
                G[vs_idx, idx_p - 1] += 1.0
            if idx_internal > 0:
                G[idx_internal - 1, vs_idx] -= 1.0
                G[vs_idx, idx_internal - 1] -= 1.0

            emf = vs.params.get('emf', 3.0)
            I_vec[vs_idx] = emf

        # 10. 求解线性方程组
        try:
            solution = np.linalg.solve(G, I_vec)
        except np.linalg.LinAlgError:
            try:
                solution, _, _, _ = np.linalg.lstsq(G, I_vec, rcond=None)
                warnings.append("电路方程奇异，使用最小二乘法近似求解")
            except Exception as e:
                warnings.append(f"电路方程求解失败: {str(e)}")
                return SimulationResult({}, {}, {}, warnings)

        # 11. 提取节点电压
        node_voltages = {ground_node: 0.0}
        for node, idx in node_id_map.items():
            if idx > 0 and idx - 1 < len(solution):
                node_voltages[node] = solution[idx - 1]

        # 12. 计算各元件的电压和电流
        component_currents = {}
        component_voltages = {}

        for comp in components:
            comp_id = id(comp)

            if not self._is_active_component(comp):
                continue

            node_p = port_to_node.get(id(comp.left_port))
            node_n = port_to_node.get(id(comp.right_port))
            if node_p is None or node_n is None:
                continue

            V_p = node_voltages.get(node_p, 0.0)
            V_n = node_voltages.get(node_n, 0.0)
            V_comp = V_p - V_n
            component_voltages[comp_id] = V_comp

            if comp.comp_type in ['resistor', 'bulb', 'ammeter', 'voltmeter', 'switch']:
                R = comp.params.get('resistance', 1e-6 if comp.comp_type == 'ammeter' else 10.0)
                if R > 0:
                    I_comp = V_comp / R
                    component_currents[comp_id] = I_comp

                    if abs(I_comp) > 100:
                        warnings.append(f"电流过大 ({abs(I_comp):.2f}A)，可能存在短路")

        # 13. 提取电压源（电池）电流
        for i, vs in enumerate(voltage_sources):
            vs_idx = (n_total - 1) + i
            if vs_idx < len(solution):
                I_vs = solution[vs_idx]
                component_currents[id(vs)] = I_vs

                # 短路检测：设置元件的短路标记
                if abs(I_vs) >= vs.params.get('emf', 3.0) / vs.params.get('internal_r', 0.5)-1e-4:
                    vs.sim_warning = True  # 电池变橙色

        return SimulationResult(node_voltages, component_currents, component_voltages, warnings)

    def _stamp_resistor(self, G: np.ndarray, idx_p: int, idx_n: int, G_val: float):
        """将电阻导纳 stamp 到矩阵（idx=0 表示地节点，跳过）"""
        if idx_p > 0:
            G[idx_p - 1, idx_p - 1] += G_val
        if idx_n > 0:
            G[idx_n - 1, idx_n - 1] += G_val
        if idx_p > 0 and idx_n > 0:
            G[idx_p - 1, idx_n - 1] -= G_val
            G[idx_n - 1, idx_p - 1] -= G_val

    def _build_node_mapping(self, components: list, wires: list) -> Dict[int, int]:
        """使用并查集构建端口到节点的映射"""
        parent = {}

        def find(x):
            if parent.get(x, x) != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 初始化
        for comp in components:
            if hasattr(comp, 'left_port') and comp.left_port:
                parent[id(comp.left_port)] = id(comp.left_port)
            if hasattr(comp, 'right_port') and comp.right_port:
                parent[id(comp.right_port)] = id(comp.right_port)

        
        # 导线连接的端口合并
        for wire in wires:
            if hasattr(wire, 'start_port') and hasattr(wire, 'end_port'):
                union(id(wire.start_port), id(wire.end_port))

        # 构建最终映射
        port_to_node = {}
        node_counter = 1

        for comp in components:
            if hasattr(comp, 'left_port') and comp.left_port:
                port_id = id(comp.left_port)
                root = find(port_id)
                if root not in port_to_node:
                    port_to_node[root] = node_counter
                    node_counter += 1
                port_to_node[port_id] = port_to_node[root]

            if hasattr(comp, 'right_port') and comp.right_port:
                port_id = id(comp.right_port)
                root = find(port_id)
                if root not in port_to_node:
                    port_to_node[root] = node_counter
                    node_counter += 1
                port_to_node[port_id] = port_to_node[root]

        return port_to_node

    def _select_ground_node(self, components: list, port_to_node: Dict[int, int],
                           all_nodes: set) -> int:
        """选择参考节点，优先选择电池/电池组负极"""
        for comp in components:
            if comp.comp_type in ['battery', 'battery_pack']:
                if hasattr(comp, 'right_port') and comp.right_port:
                    node = port_to_node.get(id(comp.right_port))
                    if node is not None:
                        return node
        return min(all_nodes) if all_nodes else 0

    def _is_active_component(self, comp) -> bool:
        """判断元件是否参与电路求解"""
        if comp.comp_type == 'switch' and not comp.switch_closed:
            return False
        return True
