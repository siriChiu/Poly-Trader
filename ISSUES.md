# Poly-Trader Issues 追踪

本文档记录开发过程中发现的问题、待优化项与未来改进方向。

---

## 🔴 高优先级（阻塞功能）

| ID | 问题描述 | 影响模块 | 状态 | 解决方案 |
|----|----------|----------|------|----------|
| #001 | Eye 模块当前返回 `feat_eye_dist` 为 None（order book 数据缺失） | `eye_binance.py` | 🟡 待调查 | 检查 Binance API 限流或字段结构变化 |
| #002 | Ear 模块 Polymarket API 返回列表而非字典，导致解析失败 | `ear_polymarket.py` | 🟡 部分修复 | 已添加列表兼容，需验证实际数据 |
| #003 | Body 模块 DefiLlama API 响应字段名不匹配（totalCirculatingUSD 可能不存在） | `body_defillama.py` | 🟡 部分修复 | 已支持多字段名，需真实数据验证 |
| #004 | collector 未写入 volume 数据（Eye 模块需补充） | `collector.py` | 🟢 待增强 | 从 order book 的总量计算 volume |
| #005 | 真实模型训练尚未执行（标签数据不足） | `model/train.py` | 🔴 阻塞 | 积累 >50 条标签后训练 XGBoost |

---

## 🟡 中优先级（体验优化）

| ID | 问题描述 | 建议改进 |
|----|----------|----------|
| #006 | `preprocessor.py` 中五感特徵合并逻辑依赖 raw data 中的 eye_dist/ear_prob，但 collector 写入的字段名可能不一致 | 统一字段命名规范，添加数据验证 |
| #007 | 回测引擎的止損邏輯只支持固定百分比，未考虑移动止損 | 增加 ATR-based trailing stop |
| #008 | 仪表板「五感有效性」页面需要足够多的历史样本才有效 | 添加数据量提示与等待机制 |
| #009 | 缺少 SHAP 可解释性图表（用户需求） | 集成 `shap` 库，绘制特征重要性 |
| #010 | 日志中文编码在 Windows cp950 下报错 | 切换为英文日志或配置编码 |

---

## 🟢 低优先级（后续迭代）

- [ ] 多策略框架：允许多个模型版本并存
- [ ] 实时数据流：WebSocket 订阅 Binance 实时 Kline/Depth
- [ ] 风险控制升级：凯利公式、波动率调整仓位
- [ ] 性能监控：Prometheus 指标导出
- [ ] 单元测试覆盖率达到 80%+
- [ ] CI/CD 自动化（GitHub Actions）
- [ ] Docker 容器化部署

---

## ✅ 已解决问题

- ✅ `__pycache__/` 被误提交 → 已添加 `.gitignore` 并清理
- ✅ 相对导入错误 → 全部改为绝对导入
- ✅ body_defillama 数据结构解析 → 支持 `all` 键或直接数组，多字段名回退
- ✅ ear_polymarket 响应兼容 → 支持列表或字典
- ✅ comprehensive_test.py 7/7 通过
- ✅ Git 仓库初始化完成

---

## 📊 问题统计

- 总问题数：14
- 已解决：7
- 待处理：7 (高优先级 3 + 中优先级 4)

---

**维护负责人**：AI Agent (main)  
**最后更新**：2026-03-30 18:14 UTC
