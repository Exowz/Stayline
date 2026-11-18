import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
root = Path(__file__).resolve().parents[1]
# Remove this path setup once the real justice server is merged.
sys.path.insert(0, str(root))
from stayline.agent.run import always_yes, run_task
from stayline.backend.db import reset_from_seed, snapshot
from stayline.config import load_settings

async def main() -> None:
    with TemporaryDirectory() as directory:
        db = str(Path(directory) / "stayline.sqlite")
        reset_from_seed(str(root / "seeds/base.json"), db)
        record = await run_task("Apply seizure notice N-2026-0417.", operator_id="smoke", run_id="smoke", settings=load_settings(db_path=db), max_steps=30, approver=always_yes, modules=("stayline.servers.justice_reference", "stayline.servers.insurer_contracts"))
        print(record["stop_reason"], [call["tool"] for call in record["tool_calls"]])
        print(sum(item["tokens_in"] + item["tokens_out"] for item in record["usage"]), sum(item["cost_usd"] for item in record["usage"]))
        print(snapshot(db)["contracts"]["C-0001"])
if __name__ == "__main__": asyncio.run(main())
