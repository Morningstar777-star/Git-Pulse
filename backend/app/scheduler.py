import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import REFRESH_INTERVAL_MINUTES
from app.github_client import github_client

class BackgroundScheduler:
    def __init__(self, interval_minutes: int = REFRESH_INTERVAL_MINUTES):
        self.interval_seconds = max(300, interval_minutes * 60) # minimum 5 min safeguard
        self.is_active = False
        self.last_run_at: Optional[str] = None
        self.next_run_at: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background refresh loop."""
        if self.is_active:
            return
        self.is_active = True
        self._task = asyncio.create_task(self._loop())
        print(f"[Scheduler] Background crawler started. Refresh cycle: every {self.interval_seconds // 60} minutes.")

    async def stop(self):
        """Stop background crawler."""
        self.is_active = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def trigger_now(self):
        """Force an immediate out-of-band sync."""
        print("[Scheduler] Manual sync triggered.")
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        res = await github_client.run_full_sync()
        self.next_run_at = (datetime.now(timezone.utc) + timedelta(seconds=self.interval_seconds)).isoformat()
        return res

    async def _loop(self):
        # Initial slight pause on startup so FastAPI boots smoothly
        await asyncio.sleep(5)
        
        while self.is_active:
            try:
                now = datetime.now(timezone.utc)
                self.last_run_at = now.isoformat()
                self.next_run_at = (now + timedelta(seconds=self.interval_seconds)).isoformat()
                
                print(f"[Scheduler] Executing scheduled GitHub trend refresh...")
                result = await github_client.run_full_sync()
                print(f"[Scheduler] Refresh finished: {result}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Scheduler] Background loop error: {e}")

            # Sleep until next interval
            await asyncio.sleep(self.interval_seconds)

scheduler = BackgroundScheduler()
