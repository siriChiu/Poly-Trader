"""
Optimizer smoke test: very small grid on a 30d window.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from datetime import datetime, timedelta
from config import load_config
from database.models import init_db
from backtesting.optimizer import grid_search

cfg = load_config()
s = init_db(cfg["database"]["url"])
end = datetime.utcnow()
start = end - timedelta(days=30)
print("Starting optimizer smoke test...")
rdf = grid_search(
    session=s,
    confidence_thresholds=[0.55],
    max_position_ratios=[0.03],
    stop_loss_pcts=[0.02],
    start_date=start,
    end_date=end,
    initial_capital=10000.0,
    symbol=cfg["trading"]["symbol"],
)
print("rows", len(rdf))
if not rdf.empty:
    print(rdf.to_string(index=False))
else:
    print("EMPTY")
s.close()
