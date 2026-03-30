# Poly-Trader 🐰

> **五感量化交易系统** - 基于免费API与开源工具的自动化策略平台

![GitHub last commit](https://img.shields.io/github/lastcommit/your-org/poly-trader)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 特色功能

| 模块 | 描述 |
|------|------|
| **👀 Eye** | Binance Order Book 流动性分析，计算价格阻力/支撑距离 |
| **👂 Ear** | Polymarket 预测市场概率 + Binance 多空比 Z-score |
| **👃 Nose** | Binance Futures 资金费率 Sigmoid 压缩 + 未平仓量增长率 |
| **👅 Tongue** | Alternative.me 恐惧贪婪指数 + 社群多空情绪 |
| **💪 Body** | DefiLlama 全网稳定币市值 7日 ROC（链上资金水位） |
| **🧠 Brain** | XGBoost 分类器（信心分數 0~1） |
| **📊 Dashboard** | Streamlit 实时仪表板：特征分析、回测、参数优化、五感有效性 |
| **🔁 LCM** | 集成 `lossless-claw-enhanced` 实现 CJK 友好的长期上下文管理 |

---

## 🗂️ 项目结构

```
poly-trader/
├── data_ingestion/       # 五感数据采集
│   ├── body_defillama.py
│   ├── tongue_sentiment.py
│   ├── nose_futures.py
│   ├── eye_binance.py
│   ├── ear_polymarket.py
│   └── collector.py      # 整合五感写入 raw_market_data
├── feature_engine/
│   └── preprocessor.py   # 特征标准化 (ROC, Z-score, Sigmoid)
├── model/
│   ├── predictor.py      # Dummy/真实模型预测
│   └── train.py          # XGBoost 训练脚本
├── execution/
│   ├── risk_control.py   # 部位控制、止損
│   └── order_manager.py  # CCXT 下單 (Dry Run 模式)
├── backtesting/
│   ├── engine.py         # 回测引擎
│   ├── metrics.py        # 绩效指标 (Sharpe, Max DD, Win Rate)
│   └── optimizer.py      # 网格搜索最佳参数
├── analysis/
│   └── sense_effectiveness.py  # 五感有效性分析 (IC, Quantile Win Rate)
├── dashboard/
│   └── app.py            # Streamlit 仪表板
├── database/
│   └── models.py         # SQLAlchemy ORM (RawMarketData, FeaturesNormalized, TradeHistory, Labels)
├── utils/
│   └── logger.py         # 日志配置
├── main.py               # APScheduler 排程闭环
├── test_pipeline.py      # 端到端测试
├── dev_heartbeat.py      # 开发进度心跳
├── comprehensive_test.py # 全面规格验证
├── config.yaml           # 配置文件
└── requirements.txt      # Python 依赖
```

---

## 🚀 快速开始

### 环境需求

- Python 3.10+
- Git
- (可选) Streamlit 用于仪表板

### 安装步骤

```bash
# 1. 克隆仓库
git clone <your-repo-url>
cd poly-trader

# 2. 创建虚拟环境
python -m venv .venv
# Windows:
# .venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python init_db.py

# 5. 配置 API Keys（编辑 config.yaml）
#   - Binance: api_key, api_secret
#   - Tavily (可选, 用于搜索)

# 6. 启动仪表板
streamlit run dashboard/app.py
```

---

## 📈 使用流程

1. **数据收集**（自动/手动）
   ```bash
   # 手动执行一次五感收集
   python -c "from data_ingestion.collector import run_collection_and_save; from database.models import init_db; from config import load_config; cfg=load_config(); session=init_db(cfg['database']['url']); run_collection_and_save(session); session.close()"
   ```

2. **特征工程**
   ```python
   from feature_engine.preprocessor import run_preprocessor
   run_preprocessor(session, "BTCUSDT")
   ```

3. **标签生成**（首次）
   ```python
   from data_ingestion.labeling import generate_future_return_labels
   labels_df = generate_future_return_labels(session, "BTCUSDT", horizon_hours=24)
   ```

4. **模型训练**（有足够标签后）
   ```bash
   python -c "from model.train import run_training; from database.models import init_db; from config import load_config; cfg=load_config(); session=init_db(cfg['database']['url']); run_training(session); session.close()"
   ```

5. **策略回测**（仪表板页面）
   - 选择日期范围、初始资金
   - 点击「执行回测」查看资金曲线与绩效指标

6. **参数优化**（仪表板页面）
   - 调整 confidence、position ratio、stop loss 的搜索范围
   - 运行网格搜索，查看 Sharpe 热图

7. **五感有效性分析**（仪表板页面）
   - 查看每个感官的 **Information Coefficient (IC)**
   - 分位数胜率热图 → 判断哪些感官设计有效/需调整

---

## ⚙️ 配置说明

`config.yaml` 主要字段：

```yaml
database:
  url: sqlite:///poly_trader.db

binance:
  api_key: ""        # 填入你的 Binance API Key
  api_secret: ""      # 填入你的 Binance API Secret

trading:
  symbol: "BTC/USDT"
  confidence_threshold: 0.7   # 预测信心阈值
  max_position_ratio: 0.05    # 最大仓位比例（5%）
  dry_run: true              # True=模拟, False=实盘
```

---

## 📊 仪表板功能详解

| 页签 | 功能 |
|------|------|
| **🔍 特徵分析** | 五感时间序列图 + 特徵相关性热图 |
| **🤖 模型預測** | 输入特徵 → 输出信心分數與交易信號 |
| **📜 交易歷史** | 历史交易列表 + 累计 P&L 曲线 |
| **📈 策略回測** | 选择时间范围 → 回测 → 展示资金曲线、Sharpe、Max DD等 |
| **🔧 參數優化** | 网格搜索 → Sharpe 热图 → 最佳参数组合 |
| **🔬 五感有效性** | 信息系数 (IC) 条形图 + 分位数胜率热图（用于调整感官设计） |

---

## 🔧 开发与自动化

### Cron 作业（OpenClaw）

| 作业名称 | 频率 | 操作 |
|----------|------|------|
| `Poly-Trader Dev Heartbeat` | 每 5 分钟 | 检查文件结构与语法 |
| `Poly-Trader Comprehensive Test` | 每日 02:00 UTC | 运行 `comprehensive_test.py`，确保无回归 |

### 验证套件

```bash
# 快速检查
python dev_heartbeat.py

# 全面规格验证（7项测试）
python comprehensive_test.py
```

---

## 📝 贡献与开发流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [OpenClaw](https://github.com/openclaw/openclaw) - AI Agent 平台
- [lossless-claw-enhanced](https://github.com/win4r/lossless-claw-enhanced) - CJK token estimation 修复
- [CCXT](https://github.com/ccxt/ccxt) - 交易所 API 封装
- [XGBoost](https://xgboost.ai/) - 机器学习模型
- [Streamlit](https://streamlit.io/) - 仪表板框架
- [DefiLlama](https://defillama.com/) - 链上数据
- [Polymarket](https://polymarket.com/) - 预测市场 Gamma API

---

**Happy Trading! 🚀**
