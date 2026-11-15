import threading
import time
from django.utils import timezone
from .services import sync_pending_receipts

def sync_receipts():
    """Your function"""
    print(f"Task running at [{timezone.now()}] syncing receipts")
    sync_pending_receipts()

def start_scheduler():
    def run():
        while True:
            time.sleep(3600) #time is in seconds
            sync_receipts()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

